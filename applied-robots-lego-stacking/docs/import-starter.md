# Import the lab starter package

On the lab laptop, inspect `~/lego_stacking_ws/src/lego_stacking/` and copy that **source folder** to your computer. Keep its `package.xml`, `setup.py` or `CMakeLists.txt`, resource files, launch files, and Python modules together. Do not copy `build/`, `install/`, or `log/`.

In WSL, from the root of this Git checkout:

```bash
mkdir -p ~/lego_stacking_ws/src
cp -a ros2_ws/src/lego_stacking ~/lego_stacking_ws/src/
cd ~/lego_stacking_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix lego_stacking
```

The `cp` command only works **after** the teacher's folder has been placed at `ros2_ws/src/lego_stacking` in this repository. Then commit its source to Git. Keep large datasets, recordings, and secrets outside Git.
