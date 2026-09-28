# Set up the project on Windows with WSL 2

These commands run **on your computer**, not inside this repository. Use Ubuntu **24.04** and ROS 2 **Jazzy**. Keep the ROS workspace under your Linux home directory (for example `~/lego_stacking_ws`), not `/mnt/c` or `/mnt/d`.

## 1. Ubuntu and Docker

In PowerShell, check `wsl --list --verbose`. If Ubuntu 24.04 is not installed, run `wsl --install -d Ubuntu-24.04`, then start the new distro and create your Linux account. An existing `Ubuntu` distro can be a different release: check `lsb_release -a` inside it before installing ROS. Do not upgrade or replace your existing distro merely because this guide says 24.04.

For URSim on WSL, install Docker Desktop for Windows, enable the WSL 2 engine and integration with the **Ubuntu-24.04** distro, then restart WSL (`wsl --shutdown` in PowerShell). Inside Ubuntu, check `docker version`. If the daemon is unavailable, fix Docker Desktop integration first. The teacher's `sudo usermod -aG docker "$USER"` is needed only when Docker reports a socket permission error; after changing group membership, log out and in.

## 2. ROS 2 Jazzy

Follow the official [Ubuntu deb installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html) through repository setup and install **`ros-jazzy-desktop`** and the documented development tools. Source ROS in each shell:

```bash
source /opt/ros/jazzy/setup.bash
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
ros2 --help
```

Add the `echo` line only once. The teacher's `echo ... > ~/.bashrc` would replace all existing shell settings, so do not use it.

## 3. Project packages

```bash
sudo apt update
sudo apt install ros-jazzy-moveit ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-ur ros-jazzy-realsense2-camera python3-opencv
```

Set Cyclone DDS for your shell, then optionally add the export to `~/.bashrc` **once**:

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
echo 'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' >> ~/.bashrc
python3 -c 'import cv2; print(cv2.__version__)'
ros2 pkg prefix ur_robot_driver
ros2 pkg prefix ur_moveit_config
ros2 pkg prefix realsense2_camera
```

Exact OpenCV versions can differ from the teacher's example. A successful import is the important check. A camera is not needed to confirm package installation.

## 4. Simulator check

```bash
docker version
ros2 run ur_client_library start_ursim.sh -m ur10e
```

The first run downloads a large simulator image. Open the PolyScope URL printed by the command (the teacher uses `http://192.168.56.101:6080/vnc.html`). WSL 2 networking and Docker configuration can affect access to that address. Follow [the work session guide](work-session.md) for the rest.

## 5. Starter package

The teacher's `lego_stacking` source is only on the lab laptop for now. [Import it](import-starter.md) before attempting `ros2 run lego_stacking motion_planner`. The instructions above do not install that package automatically.
