# Vision-guided Duplo wall assembly with a UR10e

In this FRTN85 Applied Robotics project at Lund University, Group 8 programmed a UR10e arm to build a wall from loose Duplo bricks. The system uses a RealSense D435i camera to measure the available bricks, computes a layout from their lengths, and uses MoveIt 2 and a Schunk gripper to assemble the wall. An operator reviews the proposed layout before the arm begins moving.

## Physical demonstration

| Approaching the bricks | Placing a brick | Final wall |
| :---: | :---: | :---: |
| ![UR10e gripper above loose Duplo bricks beside a calibration marker](docs/images/approach.jpg) | ![Robot working alongside a row of placed bricks](docs/images/placement.jpg) | ![Close-up of the gripper above the assembled Duplo wall](docs/images/wall.jpg) |

*Photos from Group 8’s FRTN85 Applied Robotics presentation at Lund University.*

## From camera image to grasp pose

The detector reads a color image from the RealSense camera. An ArUco marker at known table coordinates provides a reference for estimating the camera pose. This lets the detector project image points onto the plane of the brick tops and report each brick’s center and orientation in the robot workspace.

Detection is restricted to the work area around the marker. The implementation classifies red, green, and blue pixels using the two color channels of CIE Lab, which separates color from brightness. It estimates each brick’s pose from its outline, then compares visible studs with the expected patterns for **2 × 2, 2 × 4, and 2 × 6** bricks. This second measurement helps refine the center and angle used for pickup. [Vision implementation](ros2_ws/src/lego_stacking/lego_stacking/new_vision.py)

## Wall planning and assembly

1. **Allocate the bricks.** The planner sorts bricks from longest to shortest and greedily fits them into up to three layers. Each layer is limited to the width filled by the one below it. The planner converts the layout into a target position for each brick using a 16 mm stud pitch, a 3 mm gap between neighbors, and a 20 mm rise per layer.
2. **Review the plan.** The program displays the detected bricks and prints the proposed layers using brick numbers. After operator confirmation, MoveIt 2 plans and executes each arm movement.
3. **Pick, align, and place.** The arm approaches each brick at its measured angle. At a fixed alignment point, it releases the brick, pushes it sideways by a distance chosen for its length, and grasps it again near the center. This gives the gripper a more repeatable hold before placement. The controller checks finger position after closing and stops if the fingers close past the expected holding range.

[Wall planner and motion sequence](ros2_ws/src/lego_stacking/lego_stacking/final_wall.py) · [Gripper interface](ros2_ws/src/lego_stacking/lego_stacking/gripper_connection.py)

## Lab results and limitations

The team demonstrated detection, grasping, and wall assembly on the physical UR10e. During testing, small errors in the estimated brick center affected the grasp and accumulated over successive placements. The team identified camera positioning and mechanical centering as priorities for improving repeatability. The demonstration documents a completed build. The team did not report a measured placement accuracy or success rate in its presentation.

## Contributions

Jinxiao Wan built and calibrated the camera system, set up the hardware and software, and worked with Sahand Hesar to develop and test the wall planner and pick-and-place sequence. The wider team contributed the gripper fingers, alternative implementations, lab testing, and demonstration materials. [Group 8 credits](docs/gitlab-source/README.md)

## Setup and source

The lab setup uses ROS 2 Jazzy, the Universal Robots driver, MoveIt 2, OpenCV, and the RealSense camera driver. The installation guide covers dependencies, and the execution guide describes how to start the drivers and planner. Some commands registered in `setup.py` refer to modules missing from this snapshot. The wall assembly routine is in `final_wall.py`.

[Installation guide](INSTALL.md) · [Lab execution guide](EXECUTE.md) · [ROS 2 package](ros2_ws/src/lego_stacking/) · [Original LTH GitLab project](https://gitlab.control.lth.se/regler/frtn85-frtn80-applied-robotics/projects-ht2026/group-08)
