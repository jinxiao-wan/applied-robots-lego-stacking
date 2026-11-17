import os
import socket
import time

from schunk_gripper_library.driver import Driver as GripperDriver

def retry(call, attempts=4, delay=0.5):
    """Run `call()`, retrying if the gripper does not answer.

    The robot occasionally drops the tool connection for a moment (gripper_bridge reconnects
    within about a second), which can lose a message and makes the gripper library raise.
    """
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except Exception as ex:
            if attempt == attempts:
                raise
            print(f"gripper command failed ({ex}), retrying ({attempt}/{attempts - 1})")
            time.sleep(delay)


ROBOT_IP = "192.168.56.101"


def robot_side_problems():
    """Things on the robot side that are known to leave the gripper silent. Returns a list of plain-language problems."""
    problems = []
    try:
        with socket.create_connection((ROBOT_IP, 29999), timeout=2) as sock:      # dashboard server
            sock.recv(256)
            sock.sendall(b"programState\n")
            state = sock.recv(256).decode().strip()
        if not state.startswith("PLAYING"):
            problems.append(f"the program on the pendant is not running (state: {state}): the driver only sets up the "
                            "tool's serial port while it runs. Press Play -> Play from beginning.")
    except OSError as ex:
        problems.append(f"cannot reach the robot at {ROBOT_IP}: {ex}")
    try:
        for pid in filter(str.isdigit, os.listdir("/proc")):
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="ignore")
            if "ur_control.launch.py" in cmd and "use_tool_communication:=true" in cmd and "tool_parity:=2" not in cmd:
                problems.append("the UR driver was launched without tool_parity:=2, but the gripper needs even parity "
                                "(add it to the ros2 launch ur_robot_driver ... command and relaunch the driver).")
    except OSError:
        pass
    return problems


class Gripper:

    def __init__(self):
        self.driver = GripperDriver()
        if not os.path.exists("/tmp/ttyUR"):
            raise RuntimeError("/tmp/ttyUR does not exist: the gripper bridge is down. "
                               "Run `ros2 run lego_stacking gripper_bridge` in another terminal.")
        try:
            self.driver.connect(serial_port="/tmp/ttyUR", device_id=11)
        except Exception as ex:
            print(ex)
        self.driver.start_module_updates()
        self.driver.update_module_parameters()
        try:
            retry(self.driver.acknowledge, attempts=5, delay=1.0)
        except Exception as ex:
            problems = robot_side_problems()
            if problems:
                raise RuntimeError("The gripper does not answer. Likely cause(s):\n  - " + "\n  - ".join(problems)) from ex
            raise

    def ack(self):
        """ Whenever an error occurs, call this method to re-enable the gripper.
            The `OS` LED on the gripper will turn from red to green.
        """
        return retry(self.driver.acknowledge)

    def grip(self, velocity=None, force=50):
        """ :param velocity: in micrometers/second; leave as None, this gripper has no GPE and
                rejects grip commands that specify an explicit velocity
            :param force: force as a percentage (no need to change it)
        """
        return retry(lambda: self.driver.grip(force=force, velocity=velocity, outward=True))

    def move_to_position(self, position=0_000, velocity=10_000, is_absolute=True):
        """ :param position: in micrometers, zero is open
            :param velocity: in micrometers/second (this gripper's firmware rejects moves below 5500)
            :param is_absolute: if position is absolute or relative to the current
        """
        return retry(lambda: self.driver.move_to_position(position, velocity, is_absolute))

    def release(self):
        return retry(self.driver.release)

    def disconnect(self):
        return self.driver.disconnect()

    def __del__(self):
        try:
            self.driver.disconnect()
        except:
            pass

class FakeGripper():

    def __init__(self):
        pass

    def ack(self):
        return True

    def grip(self, velocity=40_000, force=50):
        return GripperDriver.GripResult.WORKPIECE_GRIPPED

    def move_to_position(self, position=0_000, velocity=3_000, is_absolute=True):
        return True

    def release(self):
        return True

    def disconnect(self):
        return True
