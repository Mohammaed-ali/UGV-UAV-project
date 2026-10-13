# Independent simulation workspace

Work only in this Simulation project. Never edit, build in, or launch the original
`/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3` workspace.
The shared PX4 dependency checkout is read-only. Per-instance parameters, logs,
generated worlds, mission files and artifacts belong to this project or its owned
temporary PX4 rootfs directory.

Gazebo is the physical authority, PX4 is the aircraft flight controller, and
`backend/mission.py` is the standalone mission authority. The browser renders
measured poses and submits validated intentions. Never substitute browser motion,
elapsed-time docking, simulator object metadata, or canned detections for physical
flight, contact verification, image perception, or AprilTag servoing.

Use the local Python virtual environment and source `scripts/environment.sh` for
robotics commands. Stop only processes started by this project. Preserve previous
validation evidence, including failed attempts. Validate a single aircraft before
scaling to a fleet. Describe incomplete or untested features accurately.
