# Getting started on your machine

Here you'll find all the required commands and instructions to get started on your machine.

IMPORTANT: whenever you read commands starting and ending with the ` character, DO NOT copy-paste that character into the terminal.

Also, "kill the program" is achieved by pressing *CTRL + C* on the keyboard (as usual).


## Install Ubuntu 24.04

This this either on metal (e.g. dual boot) using Windows WSL2.

https://learn.microsoft.com/en-us/windows/wsl/install


## Install ROS Jazzy Jalisco

ROS serves the purpose of simplifying the interaction with robots and deals most of the communication between hardware.

Follow all the instructions found at this page:

https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

and install the DESKTOP version (not the BASE).

DO NOT SKIP the **Install development tools (optional)** section.

Finally, since the tutorial doesn't mention this explicitely, run

`echo source /opt/ros/jazzy/setup.bash > ~/.bashrc`


## Install MoveIt2

MoveIt is a motion planning library and will create all the trajectories required to go from point A to point B.

Open a terminal and run

`sudo apt install ros-jazzy-moveit`

and next run the following three commands

`sudo apt install ros-$ROS_DISTRO-rmw-cyclonedds-cpp`
`echo export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp > ~/.bashrc`
`source ~/.bashrc`


## Install UR10e drivers and simulator

Every robot communicates with external machines (e.g. your laptop) with a proprietary protocol. This library is required when working with the UR10e robot via ROS.

https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver

The install procedure seems a bit chaotic, but here are the steps.


### Install the drivers

First, install the above mentioned drivers:

`sudo apt install ros-jazzy-ur`

To test the drivers, run

`ros2 launch ur_robot_driver ur_control.launch.py ur_type:=ur10e robot_ip:=192.168.56.101 launch_rviz:=true`

This should open a window with a (not so good looking) robot. This is fine, you can close the window and kill the program.


### Install the simulator

Next, install a local simulator of the robot. You will have a digital twin of the actual robot running on your machine, so you'll need to keep an eye at the web interface just as if you were looking at the teaching pendant (i.e. the tablet) of the robot. This is important to remember, as sometimes the robot won't move until you clicked something in this pendant.

First, add your used to the docker group:

`sudo usermod -a -G docker $USER`

Log out and log in again (or reboot your machine) and then run

`ros2 run ur_client_library start_ursim.sh -m ur10e`

This will take a while the first time, as it will download all the required files. When done, it should tell you to open PolyScope at

http://192.168.56.101:6080/vnc.html

This is the web interface mentioned above. At the link, click *Connect* to open the teach pendant and test if everything works fine.


## Install RealSense drivers

Working with cameras is always a little messy, as sooner or later you'll need to calibrate it to do coll things with them. Fortunately, RealSense cameras come with a neat ROS package that you can use to get started immediately.

To install the camera drivers, simply run

`sudo apt install ros-jazzy-realsense2-camera`

You can test the package by running

`ros2 launch realsense2_camera rs_launch.py`

If the camera is connected and everything went well, you should read *RealSense Node Is Up!*, if instead you don't have a camera with you, it should say *No RealSense devices were found!*. Both message are ok, and you can kill the program now.


## Install OpenCV

Images are rich in features and content, and various techniques are required to extract information from them. OpenCV is a library that does exactly that, employing state-of-theart algorithms and well-established pipelines.

To install the library, simply run

`sudo apt install python3-opencv`

and check that it works by running

`python3 -c "import cv2; print(cv2.__version__)"`

You should read something like *4.6.x*.


## Create your ROS package

Your project will be implemented as a ROS Package so to be able to interact with the system we just set up.

You will find all the boilerplate folders and file you need in the `lego_stacking_ws` folder in your home directory. To get started working, open a terminal and run

`code ~/lego_stacking_ws/src/lego_stacking`

and modify the `lego_stacking/motion_planner.py` file.



IMPORTANT: you don't need to know the exact details of how all this works (that rabbit hole is too deep, trust me), but if you really are dying to know more about it, have a look at how a package is created at

https://docs.ros.org/en/jazzy/Tutorials/Beginner-Client-Libraries/Creating-Your-First-ROS2-Package.html

Don't come to tell me I didn't warn you.
