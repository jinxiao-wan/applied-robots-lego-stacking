# Presentation: calibration and OpenCV
Source review updated 22 October 2026.

## What was reviewed
- Uploaded group-08-main.zip, archive commit c6fae96355a7d6b78d513499f2dae63df013743c (archive files dated 6 October). Read the README, execution/install instructions, package metadata and all nonempty Python modules.
- Separately uploaded camera_real_test.py and final_wall.py. These are not in that archive.
- Earlier ABB PDFs are background references, not the calibration procedure for this UR project.

**Remaining gap:** final_wall.py imports lego_stacking.new_vision, but new_vision.py is absent from all supplied files. tracker_test.py is mentioned only in calibration comments and is also absent. No actual calibration output, camera image, detection results or trial measurements were supplied. This document describes code behavior, not verified hardware performance. Original group source is not mirrored here; this is a documentation summary.

## Recommended presentation story
Explain how a camera measurement becomes a robot grasp. Use 5 slides for roughly 5–6 minutes.

| Slide | Key content | Visual from your lab |
|---|---|---|
| 1. Why calibration? | Camera optical and robot base coordinates differ | Setup photograph with both frames |
| 2. ArUco and depth | Detect four labeled corners, read depth and reconstruct camera-frame points | Saved /tmp/camera_marker_view.png |
| 3. Rigid transformation | Match camera points to known robot points; estimate R and t by SVD | Correspondences and transformation equation |
| 4. Vision-to-motion interface | Detector supplies size, x, y and yaw; wall code builds grasp targets | Saved /tmp/wall_preview.png and one detection |
| 5. Checks and limitations | Fit residual, independent physical check, placement/depth errors, missing measurements | Real console output and one trial |

## 1. Actual calibration method
This is **depth-assisted camera-to-base extrinsic calibration using an ArUco marker and rigid point registration**. It is not a chessboard intrinsic calibration, solvePnP, or a robot-pose-based hand–eye solver.

### Acquire the input
camera_real_test.py subscribes to:
- /camera/camera/color/image_raw — converted through CvBridge to BGR8.
- /camera/camera/color/camera_info — supplies fx, fy, cx, cy from K.
- /camera/camera/aligned_depth_to_color/image_raw — depth aligned to color pixels.

Its documented camera launch is:
```bash
ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true
```
The script uses the driver's intrinsics; it does not estimate them.

### Detect the reference marker
main() converts BGR to grayscale. detect_marker() calls OpenCV ArUco detection, trying DICT_4X4_50, 100, 250 and 1000 until marker ID 0 is found. It labels corners 0–3 and saves an annotated image. The intended marker is 100 mm across; the registration actually uses the hardcoded CORNER_BASE_XYZ coordinates, not MARKER_SIZE_M directly.

Known corner coordinates in the robot base frame, in metres:

| Corner | x | y | z |
|---|---:|---:|---:|
| 0 | 0.100 | 0.600 | -0.020 |
| 1 | 0.100 | 0.500 | -0.020 |
| 2 | 0.000 | 0.500 | -0.020 |
| 3 | 0.000 | 0.600 | -0.020 |

The setup assumes a flat marker with edges aligned to robot x/y. Corner 2 is the manually confirmed reference. The corner order is essential: correct image detection with incorrect real-world correspondence gives an incorrect transform.

### Turn each pixel into a 3D point
median_depth_m() samples a clipped 5×5 neighborhood around each rounded corner pixel, removes zero readings and takes the median. It divides by 1000, **assuming the depth values are millimetres**.

deproject() implements:
```text
X = (u - cx) Z / fx
Y = (v - cy) Z / fy
p_camera = [X, Y, Z]
```
Camera optical axes are x right, y down, z forward. Positive-depth filtering and the median reduce invalid samples and local noise; they do not remove systematic error. The script does not apply explicit distortion correction.

### Solve the rigid registration
rigid_transform() finds:
```text
p_base ≈ R p_camera + t
```
by minimizing the sum of squared correspondence errors:
1. Subtract the centroid from each point set.
2. Form H = centered_camera.T @ centered_base.
3. Compute H = U S V.T using NumPy SVD.
4. Compute R = V diag(1,1,d) U.T, with d chosen from det(V U.T).
5. Compute t = centroid_base - R centroid_camera.

The determinant correction enforces a proper rotation rather than a reflection. The code requires at least three depth-valid corners; the geometric requirement is three noncollinear correspondences. It does not explicitly reject nearly degenerate configurations.

### Inspect the output
The script prints R, t, roll/pitch/yaw and:
```text
residual_i = norm(R p_camera_i + t - p_base_i)
```
These are **3D fit residuals in metres**, not pixel reprojection errors. It prints copyable CAMERA_POSITION_BASE and CAMERA_ROTATION_BASE values. It does not save a calibration configuration or publish a TF transform in the provided implementation.

No actual R, t or measured residual values were supplied. The message “a few mm” in the code is an expectation, not a result.

## 2. OpenCV: exactly what can be claimed
| Location | Verified operations | Purpose |
|---|---|---|
| camera_real_test.py | cvtColor, aruco.detectMarkers, drawDetectedMarkers, putText, imwrite | Detect and label calibration marker; save a visual check |
| final_wall.py | resize, imshow, waitKey, imwrite | Display and save a detection preview |
| Missing new_vision.py | grab_color_image, BrickDetector, find_bricks, boxes_image are called | Internals not available for review |

Do not claim HSV segmentation, morphology, contour filtering, minAreaRect, homography, or a specific size classifier until new_vision.py is reviewed. Commented-out contour drawing in save_preview() is not executed detection code.

The verified integration is:
```python
image, K = new_vision.grab_color_image()
detector = new_vision.BrickDetector(image, K)
found = detector.find_bricks()
preview = detector.boxes_image(found)
```
Each returned brick is consumed through these keys:

| Key | Use in final_wall.py |
|---|---|
| n_studs | Longitudinal size category used to plan row lengths and alignment |
| x, y | Passed directly into robot picking positions, intended as base-frame metres |
| yaw | Converted to gripper yaw in degrees |

The caller expects base-frame x/y, but the missing module is needed to verify how they are produced and whether it uses this calibration. final_wall.py does not directly import camera_real_test.py or its transform.

## 3. How detection drives the robot
find_bricks() rotates each detected yaw by 90 degrees modulo 180:
```python
yaw = (brick["yaw"] + 90 + 90) % 180 - 90
```
It rounds to 0.1 degrees. gripper() then adds a separate 3-degree tuning offset, normalizes to [-90,90), and converts roll=pi, pitch=0, yaw into a quaternion. Explain this as the detector-to-gripper orientation convention plus a configured correction; do not claim its empirical accuracy without lab evidence.

Pickup height is not supplied by vision in this file:
```text
TABLE_Z = -0.020 m
BRICK_HEIGHT = 0.020 m
grasp z = TABLE_Z + BRICK_HEIGHT/2 = -0.010 m
commanded down z = grasp z + TOOL_LENGTH = 0.144 m
TOOL_LENGTH = 0.154 m
hover clearance = 0.070 m
```
These are code settings, not independently measured dimensions or a demonstrated TCP calibration. Verify the configured planning link/TCP before interpreting the tool-length compensation physically.

After pickup, align() places the brick at a known location, pushes it using size-dependent distances, then re-grasps it centered. The code comment identifies its purpose as centering the grasp. This mechanical alignment is distinct from camera calibration.

The robot uses a single detection batch before building, rather than continuously tracking during motion in final_wall.py. An operator confirms the wall plan before the build loop.

## 4. Important limitations to discuss honestly
- A calibration comment records a possible approximately 9 mm marker offset toward -x relative to the assumed coordinates. This is a historical note, not a measured current error. Re-measure the physical corner positions.
- Low residuals do not prove absolute accuracy: all reference coordinates could share a placement error and still fit well.
- The camera callbacks retain the latest messages without explicit timestamp synchronization.
- Depth conversion assumes millimetres and the pinhole calculation has no explicit undistortion.
- Depth is sampled at marker boundaries, where mixed or missing depth can occur.
- The complete detector and the connection from calibration to detection are not available.
- The archived setup.py registers neither camera_real_test nor final_wall. The uploaded snapshots are not a complete runnable package; the calibration docstring's ros2 run command needs an entry point in the actual package.
- The archive's earlier wall_builder uses 23 mm brick height; final_wall uses 20 mm. Keep presentation constants tied to the specific version used in the demonstration.
- No hardware execution was attempted in this review.

## 5. Suggested speaking notes
### Slide 1
“The camera measures positions in its own coordinate system. The robot moves in its base coordinate system. We therefore need a transformation between these two frames.”

### Slide 2
“Our calibration script detects a 100 mm ArUco marker. We know the positions of its four corners in the robot frame. We use aligned depth and the camera intrinsics to calculate the same corners in the camera frame. A median over a small neighborhood reduces local depth noise.”

### Slide 3
“We now have matching 3D points in two coordinate systems. We use SVD to estimate the rotation and translation between them. The transformation is p-base equals R times p-camera plus t. The script reports the fitting error for each corner. We also need an independent physical check because fitting error alone cannot detect every placement error.”

### Slide 4
“The wall-building code receives the brick size, x and y position, and orientation from the vision module. It adjusts the orientation for the gripper, uses a fixed pickup height, and plans the pickup. The brick is then mechanically aligned before placement.”
Add the actual detection algorithm here after reviewing new_vision.py.

### Slide 5
“The main sources of error are the reference marker placement, depth measurements and the conversion between frames. The supplied code also includes a note about a possible marker position offset. We should report measured accuracy from independent points and real picking trials.”
Replace “should report” with actual results if collected.

## 6. Collect before presenting
1. new_vision.py and any local modules/configuration it imports; tracker_test.py if it is used.
2. /tmp/camera_marker_view.png showing corner labels.
3. Actual calibration console output: transform and per-corner residuals.
4. /tmp/wall_preview.png with detected bricks.
5. Independent point errors across the picking area and successful/attempted grasp counts.
6. Confirm the physical robot model: archive instructions target UR10e, while its short README title says UR5e or YuMi.
7. Confirm your individual contributions with the group; file contents do not establish authorship.

The ABB pen/TCP materials can support a brief explanation of coordinate frames but should not be presented as the method used by camera_real_test.py.
