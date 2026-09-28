# Applied Robots · UR10e LEGO stacking

Course project workspace for ROS 2 Jazzy, MoveIt 2, a UR10e, and a RealSense D435i. The starter `lego_stacking` ROS package is supplied on the lab laptop and **has not yet been added**.

## Start here

1. Follow [docs/setup-wsl.md](docs/setup-wsl.md) on your own Windows/WSL Ubuntu 24.04 machine.
2. Follow [docs/work-session.md](docs/work-session.md) to run the simulator, driver, planner, camera, and project code.
3. Copy the teacher's `~/lego_stacking_ws/src/lego_stacking/` folder into `ros2_ws/src/lego_stacking/` when it becomes available; see [docs/import-starter.md](docs/import-starter.md).

## Layout

| Path | Purpose |
| --- | --- |
| `docs/` | Local setup, workflow, and source links |
| `course-materials/teacher/` | Original teacher instructions |
| `course-materials/robotstudio-abb/` | Earlier ABB RobotStudio course references; separate from UR10e setup |
| `ros2_ws/src/` | Future ROS package source |

The UR10e setup uses ROS 2. The ABB RobotStudio PDFs are included only as course references; RobotStudio is not an installation prerequisite for this project. Do not commit passwords, robot credentials, camera recordings, or calibration files containing private lab details.

## Status

- [x] Repository skeleton and source documents organized
- [ ] Ubuntu 24.04 / ROS 2 Jazzy installed on Olivia's computer
- [ ] MoveIt, UR driver, simulator, RealSense, OpenCV verified there
- [ ] Teacher's starter package imported from lab laptop
- [ ] Simulator session verified
- [ ] Real robot procedure obtained from Sebastiano

## References

- [ROS 2 Jazzy installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [MoveIt 2](https://moveit.picknik.ai/main/index.html)
- [Universal Robots ROS 2 driver](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver)
- [RealSense ROS wrapper](https://github.com/realsenseai/realsense-ros)
- [librealsense](https://github.com/realsenseai/librealsense)
- [OpenCV](https://github.com/opencv/opencv)
