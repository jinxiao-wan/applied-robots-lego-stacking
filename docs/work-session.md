# Simulator work session

Open separate Ubuntu terminals. In each, run `source /opt/ros/jazzy/setup.bash` and, after you build the starter package, `source ~/lego_stacking_ws/install/setup.bash`. Use the simulator first.

| Terminal | Command | Action |
| --- | --- | --- |
| 1 | `ros2 run ur_client_library start_ursim.sh -m ur10e` | Open the PolyScope link printed by URSim; power On, Start, then create an External Control program under URCaps. |
| 2 | `ros2 launch ur_robot_driver ur_control.launch.py ur_type:=ur10e robot_ip:=192.168.56.101 launch_rviz:=true` | Start ROS driver; in PolyScope press Play → Play from beginning. Check for the reverse-interface connected message. |
| 3 | `ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur10e launch_rviz:=true` | Inspect targets in RViz; **Plan and inspect** each trajectory before Execute. |
| 4 | `ros2 launch realsense2_camera rs_launch.py` | Optional until a camera is connected. “No RealSense devices were found” is expected without one. |
| 5 | `ros2 run lego_stacking motion_planner` | Requires the teacher's package and a successful build. |

PolyScope defaults in the teacher's guide: `http://192.168.56.101:6080/vnc.html`; External Control host IP `192.168.56.1`. Verify these against the address printed by URSim and the actual host interface. Do not blindly use simulator IPs for the physical robot.

After each source change:

```bash
cd ~/lego_stacking_ws
colcon build --symlink-install
source install/setup.bash
```

For the physical robot, ask Sebastiano for the lab procedure, robot IP, and required supervision before connecting or executing. The gripper code was pending in the teacher's September 25 note.
