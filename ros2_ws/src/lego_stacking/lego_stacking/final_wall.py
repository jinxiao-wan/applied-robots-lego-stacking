import time

import cv2
from numpy import pi
from tf_transformations import quaternion_from_euler

from lego_stacking.prepare_pymoveit2 import prepare_pymoveit2
prepare_pymoveit2()
from pymoveit2 import connect

from lego_stacking import new_vision
from lego_stacking.gripper_connection import Gripper

GRIPPER_YAW_OFFSET = 3.0

GRIPPER_ALIGN = 80000
GRIPPER_OPEN_POSITION = 53000
GRIPPER_CLOSE_POSITION = 67000
GRIPPER_HOLDING_BRICK_MAX = 70000
GRIPPER_HOLDING_BRICK_MIN = 62000
GRIPPER_OPEN_TOLERANCE = 2000
GRIPPER_MOVE_VELOCITY = 10_000

TOOL_LENGTH = 0.154
TOOL_WIDTH = 0.016
HOVER_HEIGHT = 0.07
PLACE_CLEARANCE = 0.001
PAUSE = 0.3

ROWS = 3
STUD_MM = 16
GAP_MM = 3
BRICK_HEIGHT = 0.020
TABLE_Z = -0.020
WALL_CENTER_XY = (0.0, 0.75)
ALIGN_PLACE = (-0.30, 0.75)
ALIGN_YAW = 90
PREVIEW_SCALE = 0.75


# Predefined push maneuver for each known Duplo brick size (studs), hand-tuned.
# approach_mm: how far (mm) past the brick's edge the gripper starts the push, on the +x side.
# push_to_mm: how far (mm) the gripper pushes to; this is exactly half the brick's length, so
#             the brick ends up centered on ALIGN_PLACE once the push is done.
ALIGN_PUSH_MM = {
    2: {"approach_mm": 60, "push_to_mm": 16},
    4: {"approach_mm": 76, "push_to_mm": 32},
    6: {"approach_mm": 92, "push_to_mm": 48},
}
ALIGN_PUSH_SPEED_SCALE = 0.3  # slow the sideways push so the brick doesn't slip instead of sliding


hand = Gripper()


def gripper(yaw):
    yaw = yaw + GRIPPER_YAW_OFFSET
    yaw = (yaw + 90) % 180 - 90
    return quaternion_from_euler(pi, 0, yaw * pi / 180, "sxyz")


def move_to(robot, x, y, z, yaw):
    print(x, y, z, yaw)
    trajectory = robot.arm.plan(None, [x, y, z], gripper(yaw))
    if trajectory is None:
        raise RuntimeError("no plan found")
    robot.arm.execute(trajectory)
    robot.arm.wait_until_executed()


def open_gripper():
    return _gripper_move(GRIPPER_OPEN_POSITION, "open")


def close_gripper():
    return _gripper_move(GRIPPER_CLOSE_POSITION, "close")


def align_gripper():
    return _gripper_move(GRIPPER_ALIGN, "align")


def _gripper_move(target, kind):
    """Used AI to fix gripper code given it was impossible otherwise."""
    for attempt in range(1, 4):
        position, ok = None, False
        try:
            hand.move_to_position(target, GRIPPER_MOVE_VELOCITY)
            end, last = time.time() + 18, []
            while time.time() < end:
                time.sleep(0.6)
                position = hand.driver.get_actual_position()
                last = (last + [position])[-3:]
                if not hand.driver.connected:
                    break
                if kind == "open" and abs(position - target) < GRIPPER_OPEN_TOLERANCE:
                    ok = True
                    break
                if kind == "close" and len(last) == 3 and max(last) - min(last) < 80 and position > GRIPPER_HOLDING_BRICK_MIN:
                    ok = True
                    break
                if kind == "align" and len(last) == 3 and max(last) - min(last) < 80:
                    ok = True
                    break
        except Exception as ex:
            print(f"  gripper {kind}: {ex}")

        if ok:
            if kind == "close" and position > GRIPPER_HOLDING_BRICK_MAX:
                raise RuntimeError(f"the gripper closed fully (position {position}): there is no brick between the fingers")
            print(f"  gripper {kind}: position {position}")
            return position
        #print(f"  gripper {kind} not verified (position {position}), try {attempt}/3")
        time.sleep(2)
    raise RuntimeError(f"could not verify that the gripper {kind}ed")


def pickup(robot, x, y, z, yaw):
    above = z + TOOL_LENGTH + HOVER_HEIGHT
    down = z + TOOL_LENGTH

    move_to(robot, x, y, above, yaw)
    open_gripper()
    time.sleep(PAUSE)
    move_to(robot, x, y, down, yaw)
    time.sleep(PAUSE)
    close_gripper()
    move_to(robot, x, y, above, yaw)


def drop(robot, x, y, z, yaw):
    above = z + TOOL_LENGTH + HOVER_HEIGHT
    down = z + TOOL_LENGTH + PLACE_CLEARANCE

    move_to(robot, x, y, above, yaw)
    move_to(robot, x, y, down, yaw)
    time.sleep(PAUSE)
    open_gripper()
    time.sleep(PAUSE)
    move_to(robot, x, y, above, yaw)


def align(robot, n_studs, z):
    """Drop the brick at ALIGN_PLACE, push it to a known x by hand-tuned motion, re-grab it centered."""
    x, y = ALIGN_PLACE
    drop(robot, x, y, z, ALIGN_YAW)

    maneuver = ALIGN_PUSH_MM[n_studs]
    push_from_x = x + maneuver["approach_mm"] / 1000
    push_to_x = x + maneuver["push_to_mm"] / 1000
    push_height = z + TOOL_LENGTH

    move_to(robot, push_from_x, y, push_height + HOVER_HEIGHT, ALIGN_YAW)
    move_to(robot, push_from_x, y, push_height, ALIGN_YAW)
    align_gripper()

    normal_velocity, normal_acceleration = robot.arm.max_velocity, robot.arm.max_acceleration
    robot.arm.max_velocity = normal_velocity * ALIGN_PUSH_SPEED_SCALE
    robot.arm.max_acceleration = normal_acceleration * ALIGN_PUSH_SPEED_SCALE
    move_to(robot, push_to_x, y, push_height, ALIGN_YAW)
    robot.arm.max_velocity, robot.arm.max_acceleration = normal_velocity, normal_acceleration

    move_to(robot, push_to_x, y, push_height + HOVER_HEIGHT, ALIGN_YAW)
    open_gripper()

    center_x = push_to_x - (n_studs * STUD_MM / 1000) / 2 - TOOL_WIDTH / 2
    pickup(robot, center_x, y, z, ALIGN_YAW)


def bricks_by_length(studs):
    bricks = []
    for i, n in enumerate(studs):
        length = n * STUD_MM + GAP_MM
        bricks.append((length, i))
    bricks.sort(reverse=True)
    return bricks


def plan_wall(studs, rows=ROWS):
    slots = bricks_by_length(studs)
    total = 0
    for slot, _ in slots:
        total += slot
    limit = total // rows
    wall = []
    for _ in range(rows):
        row, used = [], 0
        for slot, i in list(slots):
            if used + slot <= limit:
                row.append(i)
                used += slot
                slots.remove((slot, i))
        if not row:
            break
        wall.append(row)
        limit = min(limit, used)
    if not wall:
        raise RuntimeError("not enough bricks for a wall")
    return wall


def row_width(studs, row):
    width = 0
    for i in row:
        width += studs[i] * STUD_MM + GAP_MM
    return width - GAP_MM


def wall_slots(studs, wall):
    left = WALL_CENTER_XY[0] - row_width(studs, wall[0]) / 2000
    y = WALL_CENTER_XY[1]
    slots = []
    for course, row in enumerate(wall):
        z = TABLE_Z + course * BRICK_HEIGHT + BRICK_HEIGHT / 2
        x = left
        for i in row:
            length = studs[i] * STUD_MM / 1000
            centre = x + length / 2
            slots.append((i, (centre, y, z, 90)))
            x += length + GAP_MM / 1000
    return slots


def draw_preview(picture):
    cv2.imshow("bricks", cv2.resize(picture, None, fx=PREVIEW_SCALE, fy=PREVIEW_SCALE))
    cv2.waitKey(1)

def save_preview(image, path="/tmp/wall_preview.png"):
    """Save the picture with every detected brick outlined and numbered."""
    out = image.copy()
    #for i, b in enumerate(bricks, start=1):
    #    colour = (0, 0, 255) if b["suspect"] else (0, 255, 0)
    #    cv2.drawContours(out, [b["contour"]], -1, colour, 1)
    #    if b.get("hull") is not None:
    #        cv2.polylines(out, [b["hull"]], True, (255, 0, 255), 1)
    #    x, y, w, h = cv2.boundingRect(b["contour"])
    #    cv2.putText(out, str(i), (x, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.imwrite(path, out)
    return path



def find_bricks():
    image, K = new_vision.grab_color_image()
    detector = new_vision.BrickDetector(image, K)
    found = detector.find_bricks()
    draw_preview(detector.boxes_image(found))
    save_preview(detector.boxes_image(found))
    print(f"{len(found)} bricks found")
    bricks = []
    for brick in found:
        yaw = (brick["yaw"] + 90 + 90) % 180 - 90
        bricks.append((brick["n_studs"], brick["x"], brick["y"], round(yaw, 1)))
    return bricks


def print_wall(studs, wall):
    for course in range(len(wall), 0, -1):
        text = ""
        for i in wall[course - 1]:
            size = max(1, round(studs[i] / 2))
            text += "/" + "||".join([f"{i + 1:->2d}"] * size) + "\\"
        print(f"row {course}: {text}")


def main():
    # 1. Find the bricks
    bricks = find_bricks()
    studs = []
    for stud, x, y, yaw in bricks:
        studs.append(stud)

    # 2. Plan the wall
    wall = plan_wall(studs)
    slots = wall_slots(studs, wall)

    for i, s in enumerate(studs):
        print(i, s)

    # 3. Check the plan
    print("The wall that will be built (top row first, the numbers are the brick numbers in the picture):")
    print_wall(studs, wall)
    if input("Continue and build this wall? Type y and press Enter: ").strip().lower() != "y":
        print("Aborted, the robot was not moved.")
        return

    # 4. Build the wall
    with connect(group_name="ur_manipulator") as robot:
        robot.arm.allowed_planning_time = 5.0
        robot.arm.num_planning_attempts = 10
        robot.arm.max_velocity = 0.1
        robot.arm.max_acceleration = 0.1

        for i, slot in slots:
            studs_i, x, y, yaw = bricks[i]
            z = TABLE_Z + BRICK_HEIGHT / 2
            pickup(robot, x, y, z, yaw)
            align(robot, studs_i, z)
            drop(robot, *slot)
    
    hand.disconnect()


if __name__ == "__main__":
    main()
