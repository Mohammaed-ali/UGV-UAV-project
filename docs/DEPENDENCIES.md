# V0.3 dependencies

Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic (observed 8.15.0), RViz, ros_gz_sim/bridge and cv_bridge/OpenCV are installed. The exact source pins and QGC SHA256 are in `DEPENDENCY_PINS.json`.

| Dependency | Pinned version/ref | Local directory |
|---|---|---|
| PX4 | v1.17.0 / d6f12ad1 | shared dependencies/PX4-Autopilot |
| px4_msgs | release/1.17 / 86d8239e | shared dependencies/px4_msgs |
| Micro XRCE-DDS Agent | v2.4.3 / 73622810 | shared dependencies/Micro-XRCE-DDS-Agent |
| QGroundControl | official v5.1.5 x86_64 AppImage | shared dependencies/QGroundControl-x86_64.AppImage |

Shared dependencies means `/home/mohammed-ali/Downloads/wildlife_px4_dependencies`. Keep this upstream build path free of spaces: PX4's generated DDS compiler flags failed in the previous `gpt ` path. The ROS workspace itself retains the user-selected path containing spaces and builds successfully there.

`scripts/environment.sh` sources Jazzy, the available px4_msgs installation, and this workspace's installation. It sets the agent executable/library paths. `WILDLIFE_DEPS_DIR` can override the shared dependency directory. Logic-only runtime does not import the PX4 adapter.

## Rebuild existing pinned dependencies

```bash
scripts/build_px4.sh
scripts/build_agent.sh
scripts/build_ros.sh
```

PX4 uses `px4-venv` with its Python build requirements; keep this isolated from ROS's Python environment. Agent uses the installed system FastDDS/FastCDR, with its optional logger and P2P profiles disabled. The logger profile failed to compile against system fmt 9; logging is disabled rather than replacing system ROS libraries. PX4 and ROS logs plus DDS telemetry provide validation evidence.

The moved px4_msgs installation is at `msgs-install`; a future clean rebuild should use the pinned source and write build/install output in the shared directory. For a new machine, clone the three official repositories with the pins above, initialize PX4 submodules, create the Python venv with PX4's requirements, and build px4_msgs before this workspace. Build commands:

```bash
source /opt/ros/jazzy/setup.bash
colcon build --base-paths "$WILDLIFE_DEPS_DIR/px4_msgs" \
  --build-base "$WILDLIFE_DEPS_DIR/msgs-build" \
  --install-base "$WILDLIFE_DEPS_DIR/msgs-install"
```

For rosdep, source the px4_msgs overlay and use `--ignore-src --skip-keys px4_msgs` because px4_msgs is this pinned external source dependency, not an installed Jazzy apt package. Other dependencies resolve through the normal Jazzy rosdep setup.

## Official references

- [PX4 v1.17 uXRCE-DDS](https://docs.px4.io/v1.17/en/middleware/uxrce_dds)
- [PX4 v1.17 Offboard](https://docs.px4.io/v1.17/en/flight_modes/offboard)
- [QGroundControl download/install](https://docs.qgroundcontrol.com/Stable_V5.1/en/qgc-user-guide/getting_started/download_and_install.html)
- [QGroundControl logging options](https://docs.qgroundcontrol.com/Stable_V5.1/en/qgc-dev-guide/command_line_options.html)

No micro-ROS, Nav2 or YOLO dependency was added. No serial permission or ModemManager change was made for UDP SITL.
