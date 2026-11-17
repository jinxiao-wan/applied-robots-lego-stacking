# Steps of a typical work session

If you haven't read *INSTALL.md*, please start from there to get all the software you need. Ignore this if you are working on the lab computer.

Please read the following instructions to start working on your project.
If want to work with real robot for the first time, please ask Sebastiano the super secret procedure.


## Start the robot simulator (optional)

If you are working from home, start the simulator in a new terminal (#1) with

```bash
ros2 run ur_client_library start_ursim.sh -m ur10e
```

and open pendant at

http://192.168.56.101:6080/vnc.html

In the pendant, click the bottom left red circle (close to *Power Off*), and turn the robot on by first clicking the *On* button and then the *Start* button. Next, click on *Exit*. 

Now open the *Program* tab (top left), then on the left menu click on *URCaps* and then *External Control*. This creates a robot program (essentially like RAPID code) that will listen to incoming communication from a computer with IP *192.168.56.1* (if your computer has a different IP, please change it) and allow that computer to send commands to be executed. We'll get back here very soon.


## Start the robot drivers

To start talking with the robot, open a new terminal (#2) and run 

```bash
ros2 launch ur_robot_driver ur_control.launch.py ur_type:=ur10e robot_ip:=192.168.56.101 use_tool_communication:=true tool_device_name:=/tmp/ttyUR launch_rviz:=true
```

You should see a window with the robot in its current position.

Now, you must set the robot in "remote control" mode by running the program in the pendant. Open the pendant and click on the bottom right *Play* button (a triangle pointing right) and then *Play from beginning*.

In the terminal, you should now read *Robot connected to reverse interface. Ready to receive control commands*. If so, you are good to go. In the future, to reduce cluttering, you can remove the `launch_rviz:=true` argument from the command.

This command also prepares the communication with the gripper by creating a virtual TTY device you can interact with.


## Start the MoveIt planner

Now we want to start the motion planning library, which will be running in the background and wait for the our desired targets. Open a new terminal (#3) and run 

```bash
ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur10e launch_rviz:=true
```

This should open another window looking like the one opened by terminal #2, but with extra functionalities. You can see that now the robot is colored in orange, and that you can move its end-effector by dragging it with you mouse. You'll see two robots now, one looking just like the usual robot (gray and blue) and the one in orange, showing how the robot will look like in the desired target. 

When a target is set, you can run the solver by clicking on *Plan* in the bottom left panel. This will make a purple robot appear, showing how the robot will move. To actually move the robot, click on the *Execute* button. 

When testing new trajectories, **ALWAYS PLAN FIRST** and only execute when you are sure that the proposed trajectory is fine.


## Start the RealSense camera drivers

Plug the camera into the laptop and in a new terminal (#4) run

```bash
ros2 launch realsense2_camera rs_launch.py
```

This command has multiple useful arguments depending on what you want to do with the camera and I suggest you have a look at them here

https://github.com/realsenseai/realsense-ros#usage


## Start you own code

Your code is inside the `lego_stacking` ROS Package and you can run it in a new terminal (#5) using

```bash
ros2 run lego_stacking lego_planner
```

At the beginning, I suggest you play with this file only. Things will get more complex as we keep meeting. 
You can modify this file using

```bash
code ~/ws_lego_stacking/src/lego_stacking
```

and opening `lego_stacking/lego_planner.py` in the editor.

Every time you modify the file, you will need to "update" it in the ROS ecosystem. To do so, cuild the package using

```bash
cd ~/ws_lego_stacking/ && colcon build
```

---
Extra info (probably not needed) (note: this was not written by Sebastiano, but it solved an encountered problem with running the commands for starting your own code above)

If you are outside the workspace in the terminal where you want to run the commands above, do the following commands below ("outside" means it looks like this: frtn80_group8_2026@arlecchino, in the terminal).

It should look like this if you are in the workspace: frtn80_group8_2026@arlecchino:~/ws_lego_stacking$

```bash
frtn80_group8_2026@arlecchino:~$ cd ws_lego_stacking/
frtn80_group8_2026@arlecchino:~/ws_lego_stacking$ colcon build
frtn80_group8_2026@arlecchino:~/ws_lego_stacking$ source install/local_setup.bash
```