# Presentation guide: calibration and OpenCV
Updated 22 October 2026. **Preliminary: group implementation has not been reviewed.**

## Evidence and scope
The group GitLab repository requires authentication and could not be cloned. This guide must not be presented as a description of the group's implemented algorithms yet.
The GitHub tree inspected at commit 8e536ffdde4f58ba2885a8e71b79ca19f627b49f contains setup documents and an empty source directory.
The teacher's [work-session instructions](../course-materials/teacher/README.original.md) identify a UR10e, ROS 2, MoveIt, RealSense and a lego_stacking package, initially run through motion_planner.py. They do not specify a vision or calibration algorithm.
The [ABB hands-on reference](../course-materials/robotstudio-abb/01-hands_on_IRB140_READ_AND_BRING_TO_EXERCISE-1-.pdf), slides 42–45, explains tool definition and a four-point TCP method. The [pen exercise](../course-materials/robotstudio-abb/02-RobotStudio_exercise_1_pen.pdf), sections 2.4–2.5, explains workobject frames and frame-relative targets. These are earlier ABB exercises, not evidence of how the UR10e LEGO system was calibrated.

## Suggested story: from an image to a robot grasp
Your part should explain how the system finds a brick and expresses its grasp pose in coordinates the robot understands. A suggested 5-minute structure follows; adapt the time to your group's allocation.

| Slide | Time | Main question | Visual to collect from the actual project |
|---|---:|---|---|
| 1. Role of vision | 30 s | What information does the robot need from the camera? | Setup photo with camera, robot, workspace and axes |
| 2. Calibration | 75 s | How do camera measurements become robot coordinates? | Actual calibration target, reference points and frame diagram |
| 3. OpenCV pipeline | 75 s | How do we detect a brick and estimate its pose? | Original image, intermediate mask and final annotated detections |
| 4. Interface to motion | 45 s | What data is passed to the planner? | One real detection traced to a target pose |
| 5. Validation and limits | 75 s | How accurate and robust is it? | Measured errors, successful grasp and one failure example |

## Slide 1: define the output
Explain the required output: brick identity or color if used, location, orientation, and the coordinate frame. Separate observed brick pose from the final gripper pose, which may include grasp offsets. Do not claim the system estimates full 6D pose unless the code supports that.

## Slide 2: distinguish the calibration tasks
Only include methods actually used after checking the source.

- Camera intrinsics: focal lengths, principal point and distortion. Check whether these came from RealSense calibration/CameraInfo or were estimated with a calibration board. Do not say the group performed chessboard calibration without evidence.
- Camera-to-robot extrinsics: rotation and translation connecting camera and robot frames. Identify whether the camera is fixed in the workspace or attached to the robot. A single target pose estimate is not automatically hand–eye calibration.
- TCP/grasp offset: where the gripping point lies relative to the robot flange or end-effector link. ABB's four-point method is background only.
- Table/workspace frame: the plane, origin and axes used for picking and stacking.

For a rigid camera-to-base transform:
`p_base = R_base_camera * p_camera + t_base_camera`.
Define this explicitly as mapping camera coordinates into base coordinates; check transform direction and units.

If aligned depth is used, for an undistorted pixel and optical-axis depth Z:
`X = (u-cx)*Z/fx; Y = (v-cy)*Z/fy`.
Use intrinsics for the correct stream and pixel representation. Confirm depth units, alignment, invalid-depth handling and time matching. Do not treat raw distorted pixels as already undistorted.

If a planar homography is used instead, explain corresponding image/table points and the plane assumption. A homography maps points on the calibrated plane; brick tops at different heights can introduce error. Do not combine planar and depth-based methods as though both were implemented.

Describe the real procedure: collect reference observations, estimate parameters, save the transform and test independent points. Show held-out physical position error; reprojection error alone does not prove grasp accuracy.

## Slide 3: OpenCV pipeline — candidate structure, not verified code
A common color/contour pipeline is:
image acquisition → region of interest → color conversion → segmentation → mask cleanup → contours → brick filtering → center/orientation → coordinate conversion.
Replace this with the group's real sequence.

| Candidate OpenCV function | What to explain if used |
|---|---|
| cvtColor | Conversion such as BGR to HSV; verify incoming encoding |
| inRange | Thresholds selecting a color range; red may cross the hue boundary |
| morphologyEx | Opening removes small regions; closing fills gaps, but can merge neighboring bricks |
| findContours / contourArea | Extract boundaries and reject small or unsuitable regions |
| moments | Center from m10/m00 and m01/m00; guard against zero area |
| minAreaRect | Rectangle center, dimensions and angle; explain width/height swaps and angle convention |
| undistort / undistortPoints | Correct distortion with matching calibration |
| findHomography / perspectiveTransform | Plane mapping, only if used |
| solvePnP / calibrateHandEye | Distinct pose/extrinsic estimation tasks, only if actually used |

Use the actual thresholds, contour filters and functions from the code. Explain why each step is needed rather than reading code line by line. For orientation, show how the detected rectangle axis maps to the gripper axis, including 90/180-degree ambiguities. A pixel-space angle is not generally a robot-frame yaw under perspective.

## Slide 4: connect vision to motion
Trace one measured detection through the full chain:
pixel/contour → camera or table coordinates → robot-frame brick pose → grasp offset → planner target.
Record actual ROS message/topic/service names, frame_id, units and timestamp behavior once available. Explain whether a fixed approach orientation is used or whether rotation is estimated. Identify where workspace checks, approach height and stale-detection rejection occur.

## Slide 5: validation
Use real measurements only. Suggested evidence:
- Independent calibration points across the workspace: position errors in mm, mean and maximum, number of points.
- Brick localization/orientation against a reference: sample count and error definition.
- End-to-end grasp/stack success: successful trials / attempted trials, with test conditions.
- A failure example: lighting, touching bricks, occlusion, depth holes, height variation, camera movement or gripper offset.
Report perception accuracy separately from overall robot success. If measurements are unavailable, state that and show qualitative results without invented numbers.

## Speaking prompts
Use these as prompts, then fill in the verified method:
1. “My part connects the camera image to the robot's picking target.”
2. “The camera and robot use different coordinate systems. We used [actual method] to connect them.”
3. “Our image processing starts with [input]. We then [actual steps] to estimate [actual outputs].”
4. “We convert this result into [actual frame] and apply [actual grasp offset] before sending it to [actual interface].”
5. “We tested it using [real procedure]. The main limitation was [observed issue].”

## Likely questions to prepare
- Why was calibration needed? Which quantities were already supplied by the camera?
- How was the transform obtained and checked?
- What changes if the camera moves?
- How are pixel/depth coordinates converted into metric coordinates?
- Why use the selected segmentation method?
- How are adjacent bricks and ambiguous angles handled?
- How does detection error affect grasping?
- What did you implement personally, and what came from the starter package?

## Materials needed to finalize this guide
Export the latest group GitLab source as a ZIP and provide it for review, including vision/calibration scripts, launch/config files, README, dependency files and any permitted example images/results. Exclude credentials and private recordings.
Then replace the candidate pipeline with exact filenames/functions, identify the real calibration procedure and add measured results. Do not publish private group source wholesale without confirming its intended sharing scope.

## Technical references
These explain candidate techniques, not proof of the group's implementation:
- [OpenCV camera calibration](https://docs.opencv.org/4.12.0/dc/dbb/tutorial_py_calibration.html)
- [OpenCV contour features](https://docs.opencv.org/4.13.0/dd/d49/tutorial_py_contour_features.html)
- [OpenCV shape API](https://docs.opencv.org/4.13.0/d3/dc0/group__imgproc__shape.html)
- [Group source — authentication required](https://gitlab.control.lth.se/regler/frtn85-frtn80-applied-robotics/projects-ht2026/group-08)
