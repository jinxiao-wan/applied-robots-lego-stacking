import sys
import time
from pathlib import Path

import cv2
import numpy as np

IMAGE_PATH = Path(__file__).parent / "image2.png"
STEPS_FOLDER = Path(__file__).parent / "vision_steps"
COLOR_TOPIC = "/camera/camera/color/image_raw"
INFO_TOPIC = "/camera/camera/color/camera_info"
CAMERA_WAIT_SECONDS = 15.0

# Colors are classified by nearest centroid in CIE Lab's a*/b* (chroma) plane rather than
# fixed HSV cuboids. Lab separates color from brightness, so shadows/highlights/exposure
# changes barely move a pixel's (a, b) position. Centroids/radii below were sampled directly
# from the RealSense camera (vision_steps/camera_capture.png, taken with `--camera`), not a
# phone photo: a marker-referenced white-balance step was tried first but the marker's own
# printed surface turned out non-neutral under this camera (and partially overexposed), which
# distorted every pixel's color more than it fixed. If the camera or bricks change enough that
# detection degrades, recalibrate centroids from a fresh --camera capture instead of guessing.
BRICK_COLORS = {
    "red":    {"ab": (178, 157), "radius": 35},
    #"yellow": {"ab": (0, 0), "radius": 0},
    "green":  {"ab": (103, 124), "radius": 16},
    "blue":   {"ab": (144, 75), "radius": 25},
}
CHROMA_MIN = 18  # reject near-neutral pixels (table wood, walls, shadows) regardless of hue
# Detection is restricted to a table-plane square centered on the marker's own position (not a
# fixed world-frame rectangle, and not anything tied to where the camera happens to be - the
# camera pose is re-solved from the marker every frame) so background clutter outside the table
# - the gripper, walls, anything the camera happens to also see - can never register as a brick
# no matter what color it is. The marker sits near the middle of the working area, so this
# padding just needs to comfortably cover the table out to where bricks actually get placed.
WORKSPACE_PADDING_M = 0.40
MARKER_EXCLUDE_MARGIN_PX = 20  # also cut out the marker itself, which sits inside that square
MIN_BRICK_AREA = 1500
MAX_BRICK_AREA = 25000

TABLE_Z = -0.020
MARKER_CORNERS_XY = {0: (0.1, 0.6), 1: (0.1, 0.5), 2: (0.0, 0.5), 3: (0.0, 0.6)}
FOCAL_PX = 1380.0
BRICK_TOP_Z = TABLE_Z + 0.0192
STUD_Z = TABLE_Z + 0.0214
STUD_PITCH = 0.016
BRICK_WIDTH = 0.0318
BRICK_HEIGHT = 0.0236
STUD_RADIUS = 0.0047
DUPLO_STUD_LENGTHS = (2, 4, 6)  # known Duplo brick lengths in studs (x2 studs wide = 4, 8, 12 pins)

CIRCLE_MIN_RADIUS = 6
CIRCLE_MAX_RADIUS = 12
CIRCLE_MIN_DISTANCE = 24
CIRCLE_SENSITIVITY = 10
CIRCLE_CONTRAST = 10.0
TOP_FACE_GROW = 6
MATCH_DISTANCE_PX = 10
MIN_MATCHES = 3
CIRCLE_OVERRIDE_MARGIN = 3.0  # min score lead an alternate stud count needs over the outline's
# own (geometric, frame-to-frame stable) count before it's trusted to override it - Hough circle
# detection is noisy enough on a live feed that without this margin, a one-circle miss would
# occasionally beat the correct count by a hair and make the reported brick size flip every run
CIRCLE_WEIGHT = 0.5
AGREE_SHIFT_M = 0.0015
MAX_SHIFT_M = 0.008
MAX_TURN_DEG = 10

MASK_PANEL_SCALE = 0.5
OUTLINE_COLORS = {"red": (0, 0, 255), "yellow": (0, 255, 255), "green": (0, 255, 0), "blue": (255, 128, 0)}
EXPECTED_COLOR = (255, 255, 0)
DETECTED_COLOR = (255, 0, 255)
MARKER_ALPHA = 0.45
BOX_EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]


def nearest_duplo_length(studs):
    return min(DUPLO_STUD_LENGTHS, key=lambda n: abs(n - studs))


def detect_marker(gray):
    for name in ("DICT_4X4_50", "DICT_4X4_100", "DICT_4X4_250", "DICT_4X4_1000"):
        dictionary_id = getattr(cv2.aruco, name)
        if hasattr(cv2.aruco, "ArucoDetector"):
            detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(dictionary_id),
                                               cv2.aruco.DetectorParameters())
            corners, ids, _ = detector.detectMarkers(gray)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(gray, cv2.aruco.Dictionary_get(dictionary_id),
                                                      parameters=cv2.aruco.DetectorParameters_create())
        if ids is not None and 0 in ids.flatten():
            return corners[list(ids.flatten()).index(0)][0].astype(np.float64)
    return None


def grab_color_image(timeout=CAMERA_WAIT_SECONDS):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import CameraInfo, Image

    started_ros = not rclpy.ok()
    if started_ros:
        rclpy.init()
    node = rclpy.create_node("new_vision_camera")
    received = {}

    def on_image(msg):
        data = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, -1)
        received["image"] = data[:, :, ::-1].copy() if msg.encoding == "rgb8" else data.copy()

    def on_info(msg):
        received["K"] = np.array(msg.k, np.float64).reshape(3, 3)

    node.create_subscription(Image, COLOR_TOPIC, on_image, qos_profile_sensor_data)
    node.create_subscription(CameraInfo, INFO_TOPIC, on_info, qos_profile_sensor_data)
    end = time.time() + timeout
    while ("image" not in received or "K" not in received) and time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()
    if started_ros:
        rclpy.shutdown()
    if "image" not in received:
        raise SystemExit("No picture from the camera. Is it plugged in and is the RealSense driver running? "
                         "Start it with: ros2 launch realsense2_camera rs_launch.py")
    return received["image"], received.get("K")


class BrickDetector:

    def __init__(self, image, K=None):
        self.image = image
        corners = detect_marker(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        if corners is None:
            raise SystemExit("The ArUco marker was not found in the image")
        self.hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        self.lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
        self._labels = None
        self.calibrate(corners, K)
        self.valid_mask = self.build_valid_mask(corners)

    def calibrate(self, corners, K=None):
        height, width = self.image.shape[:2]
        self.K = K if K is not None else np.array([[FOCAL_PX, 0, width / 2], [0, FOCAL_PX, height / 2], [0, 0, 1.0]])
        world = np.array([[*MARKER_CORNERS_XY[i], TABLE_Z] for i in range(4)])
        _, rvec, tvec = cv2.solvePnP(world, corners, self.K, None)
        self.R, _ = cv2.Rodrigues(rvec)
        self.t = tvec.ravel()

    def build_valid_mask(self, marker_corners):
        """Pixels outside a table-plane square centered on the marker, or on the marker itself,
        are never considered for brick detection - this keeps the gripper, walls, and other
        off-table clutter from ever being misread as a brick, regardless of their color. The
        square is defined relative to the marker's own table position (MARKER_CORNERS_XY), not
        a fixed world-frame rectangle, so it follows the table if the marker/table ever moves,
        and it does not assume anything about where the camera is: the camera pose is re-solved
        from the detected marker every frame.

        Built by mapping every pixel to its table-plane (x, y) and testing those bounds, not by
        projecting the square's corners forward into pixel space: that forward direction is
        numerically unstable for a corner far from the marker (the homography can send it to a
        wild, effectively unbounded pixel coordinate depending on camera pose, which made
        fillConvexPoly balloon the "valid" region across the wall on some frames). Pixel -> table
        is always evaluated at real, bounded pixel coordinates, so it doesn't have that failure
        mode, regardless of where the camera happens to be."""
        height, width = self.image.shape[:2]
        ys, xs = np.mgrid[0:height, 0:width]
        pixels = np.column_stack([xs.ravel(), ys.ravel()])
        table_xy = self.pixels_to_table(pixels, TABLE_Z)
        marker_cx, marker_cy = np.mean(list(MARKER_CORNERS_XY.values()), axis=0)
        x0, x1 = marker_cx - WORKSPACE_PADDING_M, marker_cx + WORKSPACE_PADDING_M
        y0, y1 = marker_cy - WORKSPACE_PADDING_M, marker_cy + WORKSPACE_PADDING_M
        inside = (table_xy[:, 0] >= x0) & (table_xy[:, 0] <= x1) & (table_xy[:, 1] >= y0) & (table_xy[:, 1] <= y1)
        mask = inside.reshape(height, width).astype(np.uint8) * 255
        center = marker_corners.mean(axis=0)
        radius = int(np.linalg.norm(marker_corners - center, axis=1).max() + MARKER_EXCLUDE_MARGIN_PX)
        cv2.circle(mask, tuple(center.astype(int)), radius, 0, -1)
        return mask

    def plane_homography(self, z):
        return self.K @ np.column_stack([self.R[:, 0], self.R[:, 1], self.R[:, 2] * z + self.t])

    def pixels_to_table(self, pixels, z):
        inverse = np.linalg.inv(self.plane_homography(z))
        points = np.asarray(pixels, np.float64).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(points, inverse).reshape(-1, 2)

    def table_to_pixels(self, points, z):
        points = np.asarray(points, np.float64).reshape(-1, 1, 2)
        return cv2.perspectiveTransform(points, self.plane_homography(z)).reshape(-1, 2)

    def classify_colors(self):
        if self._labels is None:
            names = list(BRICK_COLORS)
            ab = self.lab[:, :, 1:3].reshape(-1, 2)
            chroma = np.linalg.norm(ab - 128.0, axis=1)
            distances = np.stack([np.linalg.norm(ab - np.array(BRICK_COLORS[c]["ab"]), axis=1) for c in names], axis=1)
            nearest = distances.argmin(axis=1)
            nearest_distance = distances.min(axis=1)
            labels = np.full(ab.shape[0], -1, np.int8)
            for i, name in enumerate(names):
                within = (nearest == i) & (nearest_distance <= BRICK_COLORS[name]["radius"]) & (chroma >= CHROMA_MIN)
                labels[within] = i
            self._labels = labels.reshape(self.lab.shape[:2])
            self._names = names
        return self._labels, self._names

    def color_mask(self, color):
        labels, names = self.classify_colors()
        mask = (labels == names.index(color)).astype(np.uint8) * 255
        return cv2.bitwise_and(mask, self.valid_mask)

    def find_bricks(self):
        bricks = []
        kernel = np.ones((5, 5), np.uint8)
        for color in BRICK_COLORS:
            mask = self.color_mask(color)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if MIN_BRICK_AREA <= area <= MAX_BRICK_AREA:
                    brick = {"color": color, "contour": cv2.convexHull(contour), "area": area}
                    self.measure_from_outline(brick)
                    self.match_circles(brick)
                    bricks.append(brick)
        return bricks

    def top_face(self, brick):
        inside = np.zeros(self.hsv.shape[:2], np.uint8)
        cv2.drawContours(inside, [brick["contour"]], -1, 255, -1)
        values = self.hsv[:, :, 2][inside > 0].reshape(-1, 1)
        threshold, _ = cv2.threshold(values, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        top = ((self.hsv[:, :, 2] > threshold) & (inside > 0)).astype(np.uint8) * 255
        top = cv2.morphologyEx(top, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        top = cv2.morphologyEx(top, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        count, labels, stats, _ = cv2.connectedComponentsWithStats(top)
        if count <= 1:
            return inside
        biggest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        return (labels == biggest).astype(np.uint8) * 255

    def measure_from_outline(self, brick):
        top = self.top_face(brick)
        contours, _ = cv2.findContours(top, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        outline = cv2.convexHull(max(contours, key=cv2.contourArea))
        points = self.pixels_to_table(outline, BRICK_TOP_Z).astype(np.float32)
        (cx, cy), (w, h), angle = cv2.minAreaRect(points)
        long_side, short_side = max(w, h), min(w, h)
        yaw = angle if w >= h else angle + 90
        brick["top_face"] = top
        brick["x"], brick["y"] = float(cx), float(cy)
        brick["yaw"] = float(yaw % 180)
        brick["length"], brick["width"] = float(long_side), float(short_side)
        brick["n_studs"] = nearest_duplo_length(long_side / STUD_PITCH)
        brick["outline_pose"] = (brick["x"], brick["y"], brick["yaw"], brick["n_studs"])
        brick["circles"] = self.find_circles(brick)

    def find_circles(self, brick):
        x, y, w, h = cv2.boundingRect(brick["contour"])
        pad = 6
        x0, y0 = max(0, x - pad), max(0, y - pad)
        crop = self.hsv[y0:y + h + pad, x0:x + w + pad, 2]
        crop = cv2.createCLAHE(clipLimit=CIRCLE_CONTRAST, tileGridSize=(3, 3)).apply(crop)
        crop = cv2.GaussianBlur(crop, (5, 5), 1.2)
        found = cv2.HoughCircles(crop, cv2.HOUGH_GRADIENT, dp=1, minDist=CIRCLE_MIN_DISTANCE, param1=100,
                                 param2=CIRCLE_SENSITIVITY, minRadius=CIRCLE_MIN_RADIUS, maxRadius=CIRCLE_MAX_RADIUS)
        if found is None:
            return []
        grow = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * TOP_FACE_GROW + 1, 2 * TOP_FACE_GROW + 1))
        top = cv2.dilate(brick["top_face"], grow)
        circles = []
        for cx, cy, r in found[0]:
            if top[int(cy + y0), int(cx + x0)] > 0:
                circles.append((float(cx + x0), float(cy + y0), float(r)))
        return circles

    def expected_studs(self, x, y, yaw_deg, n_studs):
        yaw = np.radians(yaw_deg)
        along = np.array([np.cos(yaw), np.sin(yaw)])
        across = np.array([-np.sin(yaw), np.cos(yaw)])
        points = []
        for i in range(n_studs):
            for side in (-0.5, 0.5):
                u = (i - (n_studs - 1) / 2) * STUD_PITCH
                points.append(np.array([x, y]) + u * along + side * STUD_PITCH * across)
        return np.array(points)

    def pair_circles(self, brick, x, y, yaw, n_studs):
        expected = self.expected_studs(x, y, yaw, n_studs)
        expected_px = self.table_to_pixels(expected, STUD_Z)
        pairs = []
        for k, point in enumerate(expected_px):
            best = None
            for cx, cy, r in brick["circles"]:
                distance = np.hypot(cx - point[0], cy - point[1])
                if distance < MATCH_DISTANCE_PX and (best is None or distance < best[0]):
                    best = (distance, cx, cy)
            if best is not None:
                pairs.append((k, best[1], best[2]))
        return expected, pairs

    def match_circles(self, brick):
        brick["circle_shift"] = 0.0
        brick["pose_source"] = "outline"

        outline_n = brick["n_studs"]
        scores = {}
        for n in DUPLO_STUD_LENGTHS:
            _, pairs = self.pair_circles(brick, brick["x"], brick["y"], brick["yaw"], n)
            scores[n] = len(pairs) - 0.5 * (2 * n - len(pairs))
        best_n = max(scores, key=scores.get)
        if scores[best_n] >= scores[outline_n] + CIRCLE_OVERRIDE_MARGIN:
            brick["n_studs"] = best_n

        expected, pairs = self.pair_circles(brick, brick["x"], brick["y"], brick["yaw"], brick["n_studs"])
        if len(pairs) < MIN_MATCHES:
            self.pose_from_circles(brick)
            expected, pairs = self.pair_circles(brick, brick["x"], brick["y"], brick["yaw"], brick["n_studs"])
        brick["matched"] = len(pairs)
        if len(pairs) < MIN_MATCHES or brick["pose_source"] != "outline":
            return

        found = self.pixels_to_table([[cx, cy] for _, cx, cy in pairs], STUD_Z)
        wanted = expected[[k for k, _, _ in pairs]]
        shift = found.mean(axis=0) - wanted.mean(axis=0)
        a, b = wanted - wanted.mean(axis=0), found - found.mean(axis=0)
        turn = np.degrees(np.arctan2((a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]).sum(), (a * b).sum()))
        brick["circle_shift"] = float(np.hypot(*shift))
        if brick["circle_shift"] < AGREE_SHIFT_M or brick["circle_shift"] > MAX_SHIFT_M or abs(turn) > MAX_TURN_DEG:
            return
        brick["x"] += float(CIRCLE_WEIGHT * shift[0])
        brick["y"] += float(CIRCLE_WEIGHT * shift[1])
        brick["yaw"] = float((brick["yaw"] + CIRCLE_WEIGHT * turn) % 180)
        brick["pose_source"] = "outline + circles"

    def pose_from_circles(self, brick):
        count = len(brick["circles"])
        if count % 2 or not min(DUPLO_STUD_LENGTHS) * 2 <= count <= max(DUPLO_STUD_LENGTHS) * 2:
            return
        points = self.pixels_to_table([[cx, cy] for cx, cy, _ in brick["circles"]], STUD_Z)
        brick["x"], brick["y"] = float(points[:, 0].mean()), float(points[:, 1].mean())
        brick["n_studs"] = nearest_duplo_length(count // 2)
        if brick["n_studs"] == min(DUPLO_STUD_LENGTHS):
            brick["yaw"] = float(brick["yaw"] % 90)
        else:
            centered = points - points.mean(axis=0)
            eigenvalues, eigenvectors = np.linalg.eigh(centered.T @ centered)
            axis = eigenvectors[:, np.argmax(eigenvalues)]
            brick["yaw"] = float(np.degrees(np.arctan2(axis[1], axis[0])) % 180)
        brick["pose_source"] = "circles (outline disagreed)"

    def brick_box(self, brick):
        yaw = np.radians(brick["yaw"])
        along = np.array([np.cos(yaw), np.sin(yaw)])
        across = np.array([-np.sin(yaw), np.cos(yaw)])
        half_length = brick["n_studs"] * STUD_PITCH / 2
        half_width = BRICK_WIDTH / 2
        center = np.array([brick["x"], brick["y"]])
        corners = []
        for z in (TABLE_Z, TABLE_Z + BRICK_HEIGHT):
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                xy = center + a * half_length * along + b * half_width * across
                corners.append([xy[0], xy[1], z])
        return np.array(corners)

    def project(self, points):
        camera_points = (self.R @ np.asarray(points).T).T + self.t
        pixels = (self.K @ camera_points.T).T
        return pixels[:, :2] / pixels[:, 2:3]

    def location_3d(self, brick):
        size = (brick["n_studs"] * STUD_PITCH, BRICK_WIDTH, BRICK_HEIGHT)
        center = (brick["x"], brick["y"], TABLE_Z + BRICK_HEIGHT / 2)
        return center, size

    def title(self, image, text):
        cv2.putText(image, text, (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 6)
        cv2.putText(image, text, (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2)
        return image

    def number(self, image, brick, i):
        x, y, w, h = cv2.boundingRect(brick["contour"])
        cv2.putText(image, str(i), (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 5)
        cv2.putText(image, str(i), (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    def blend(self, base, markers):
        return cv2.addWeighted(markers, MARKER_ALPHA, base, 1 - MARKER_ALPHA, 0)

    def stud_circles(self, x, y, yaw, n_studs):
        points = self.expected_studs(x, y, yaw, n_studs)
        centers = self.table_to_pixels(points, STUD_Z)
        edges = self.table_to_pixels(points + [STUD_RADIUS, 0], STUD_Z)
        return [(c, max(3, int(np.hypot(*(e - c))))) for c, e in zip(centers, edges)]

    def step1_color_masks(self):
        panels = []
        for color in BRICK_COLORS:
            panel = cv2.bitwise_and(self.image, self.image, mask=self.color_mask(color))
            panel = cv2.resize(panel, None, fx=MASK_PANEL_SCALE, fy=MASK_PANEL_SCALE)
            cv2.putText(panel, color, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3)
            panels.append(panel)
        columns = 2
        blank = np.zeros_like(panels[0])
        rows = [panels[i:i + columns] for i in range(0, len(panels), columns)]
        rows[-1] += [blank] * (columns - len(rows[-1]))
        return np.vstack([np.hstack(row) for row in rows])

    def step2_outlines(self, bricks):
        result = self.image.copy()
        for i, brick in enumerate(bricks, start=1):
            cv2.drawContours(result, [brick["contour"]], -1, OUTLINE_COLORS[brick["color"]], 3)
            self.number(result, brick, i)
        return self.title(result, "Step 2: outline of every colored brick")

    def step3_circles(self, bricks):
        result = self.image.copy()
        markers = result.copy()
        for i, brick in enumerate(bricks, start=1):
            for cx, cy, r in brick["circles"]:
                cv2.circle(markers, (int(cx), int(cy)), int(r), DETECTED_COLOR, -1)
                cv2.circle(result, (int(cx), int(cy)), int(r), DETECTED_COLOR, 1)
            self.number(result, brick, i)
        return self.title(self.blend(result, markers), "Step 3: circles found directly in the picture")

    def step4_pose(self, bricks):
        result = self.image.copy()
        markers = result.copy()
        for i, brick in enumerate(bricks, start=1):
            for center, radius in self.stud_circles(*brick["outline_pose"]):
                cv2.circle(result, (int(center[0]), int(center[1])), radius, (255, 255, 255), 1)
            for center, radius in self.stud_circles(brick["x"], brick["y"], brick["yaw"], brick["n_studs"]):
                cv2.circle(markers, (int(center[0]), int(center[1])), radius, EXPECTED_COLOR, -1)
            for cx, cy, r in brick["circles"]:
                cv2.circle(result, (int(cx), int(cy)), int(r), DETECTED_COLOR, 1)
            corners = self.project(self.brick_box(brick)[4:]).astype(int)
            cv2.polylines(result, [corners], True, OUTLINE_COLORS[brick["color"]], 2)
            self.number(result, brick, i)
        return self.title(self.blend(result, markers), "Step 4: pose from the outline, checked and corrected with the circles")

    def boxes_image(self, bricks):
        result = self.image.copy()
        for i, brick in enumerate(bricks, start=1):
            corners = self.project(self.brick_box(brick)).astype(int)
            for a, b in BOX_EDGES:
                cv2.line(result, tuple(corners[a]), tuple(corners[b]), (0, 0, 0), 5)
            for a, b in BOX_EDGES:
                cv2.line(result, tuple(corners[a]), tuple(corners[b]), OUTLINE_COLORS[brick["color"]], 2)
            self.number(result, brick, i)
        return result

    def step5_boxes(self, bricks):
        return self.title(self.boxes_image(bricks), "Step 5: 3D reconstruction of every brick")

    def save_steps(self, bricks, folder=STEPS_FOLDER):
        folder.mkdir(exist_ok=True)
        steps = {
            "step1_color_masks.png": self.step1_color_masks(),
            "step2_outlines.png": self.step2_outlines(bricks),
            "step3_circles.png": self.step3_circles(bricks),
            "step4_pose.png": self.step4_pose(bricks),
            "step5_boxes.png": self.step5_boxes(bricks),
        }
        for name, picture in steps.items():
            cv2.imwrite(str(folder / name), picture)
        return list(steps)


def main():
    K = None
    if "--camera" in sys.argv:
        image, K = grab_color_image()
        STEPS_FOLDER.mkdir(exist_ok=True)
        cv2.imwrite(str(STEPS_FOLDER / "camera_capture.png"), image)
        print(f"Picture from the camera saved to {STEPS_FOLDER / 'camera_capture.png'}")
    else:
        image = cv2.imread(str(IMAGE_PATH))
        if image is None:
            raise SystemExit(f"Could not read {IMAGE_PATH}")
    print(f"Image: {image.shape[1]}x{image.shape[0]}")

    detector = BrickDetector(image, K)
    bricks = detector.find_bricks()
    print(f"{len(bricks)} bricks found")
    print(" #  color    center x, y, z (mm)         yaw   size L x W x H (mm)   studs  matched  pose from")
    for i, brick in enumerate(bricks, start=1):
        center, size = detector.location_3d(brick)
        print(f"{i:2d}  {brick['color']:6s}  {center[0] * 1000:7.1f} {center[1] * 1000:7.1f} {center[2] * 1000:6.1f}  "
              f"{brick['yaw']:6.1f}   {size[0] * 1000:5.1f} x {size[1] * 1000:4.1f} x {size[2] * 1000:4.1f}    "
              f"{brick['n_studs'] * 2:3d}    {brick['matched']:3d}     {brick['pose_source']}")

    for name in detector.save_steps(bricks):
        print(f"Saved {STEPS_FOLDER / name}")


if __name__ == "__main__":
    main()
