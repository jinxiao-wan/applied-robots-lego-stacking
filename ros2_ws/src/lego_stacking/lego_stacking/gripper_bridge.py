"""Keeps the gripper serial port (/tmp/ttyUR) alive.

The UR driver starts a socat bridge from the robot's tool port (TCP 54321) to /tmp/ttyUR, but
only once: whenever the robot closes that TCP connection, socat exits, /tmp/ttyUR disappears and
every gripper command fails with "Not connected" until the driver is relaunched.

This node replaces that bridge. It creates /tmp/ttyUR itself and keeps it open, and reconnects
the TCP link to the robot in the background whenever the robot drops it. Programs using the
gripper only see a short timeout (which the gripper library retries) instead of a missing port.
Start it after the driver, in its own terminal, and leave it running.

Never start a second bridge by hand: the robot serves the tool port to one connection at a time,
and an extra connection is accepted but gets no answers ("No response received after 3 retries").
After a connection is dropped, the robot can keep the port locked for a few seconds to about a
minute; the bridge keeps retrying until the gripper answers again.

Run with: ros2 run lego_stacking gripper_bridge
"""
import os
import pty
import signal
import select
import socket
import time
import tty

ROBOT_IP = "192.168.56.101"
TOOL_PORT = 54321
DEVICE = "/tmp/ttyUR"
RETRY_DELAY = 0.1   # seconds between reconnection attempts
TRACE = bool(os.environ.get("GRIPPER_BRIDGE_TRACE"))   # log every byte exchanged, for debugging


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def stop_driver_bridge():
    """The UR driver launch starts its own socat bridge on /tmp/ttyUR. The robot only serves one connection to the
    gripper at a time, so two bridges fight and neither works: stop the driver's one before taking over."""
    stopped = []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\0", b" ").decode(errors="ignore")
        except OSError:
            continue
        if cmd.startswith("socat") and f"link={DEVICE}" in cmd:
            os.kill(int(pid), signal.SIGTERM)
            stopped.append(pid)
    if stopped:
        log(f"stopped the driver's own gripper bridge (socat pid {', '.join(stopped)}); this bridge replaces it")
        time.sleep(3)      # give the robot time to release the tool port


def link(name):
    try:
        os.remove(DEVICE)
    except FileNotFoundError:
        pass
    os.symlink(name, DEVICE)


def connect():
    sock = socket.create_connection((ROBOT_IP, TOOL_PORT), timeout=3)
    sock.settimeout(None)
    return sock


def main():
    stop_driver_bridge()
    master, slave = pty.openpty()   # `slave` stays open so the port never closes on us
    tty.setraw(slave)
    name = os.ttyname(slave)
    link(name)
    log(f"{DEVICE} -> {name}, bridging to {ROBOT_IP}:{TOOL_PORT}. Ctrl+C to stop.")
    sock = None
    pending = b""   # last request sent that the robot has not answered yet
    try:
        while True:
            # Another program (e.g. the socat the driver launch starts) may delete or replace
            # the link when it exits; put it back.
            if os.path.realpath(DEVICE) != os.path.realpath(name):
                link(name)
                log(f"restored {DEVICE} -> {name}")

            if sock is None:
                try:
                    sock = connect()
                    log("connected to the robot's tool port")
                    if pending:
                        # The reply to this request was lost with the old connection.
                        sock.sendall(pending)
                except OSError:
                    if sock is not None:
                        sock.close()
                        sock = None
                    time.sleep(RETRY_DELAY)
                    continue

            ready, _, _ = select.select([master, sock], [], [], 1.0)
            try:
                if master in ready:
                    data = os.read(master, 4096)
                    if data:
                        if TRACE:
                            log(f"-> robot {data.hex(' ')}")
                        pending = data
                        sock.sendall(data)
                if sock in ready:
                    data = sock.recv(4096)
                    if not data:
                        raise ConnectionError("closed by the robot")
                    if TRACE:
                        log(f"<- robot {data.hex(' ')}")
                    pending = b""
                    os.write(master, data)
            except OSError as ex:
                log(f"connection to the robot lost ({ex}); reconnecting")
                sock.close()
                sock = None
                time.sleep(RETRY_DELAY)
    except KeyboardInterrupt:
        pass
    finally:
        os.close(slave)
        os.close(master)
        try:
            os.remove(DEVICE)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
