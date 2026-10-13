#!/usr/bin/env bash
cd "$(dirname "$0")/.."
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=77 ROS_LOG_DIR=/tmp/wildlife-acceptance-logs
python3 tests/live_probe.py > /tmp/wildlife-acceptance-logic.json 2>&1 & probe_pid=$!
timeout -s INT 265 ros2 launch wildlife_bringup subject1_demo.launch.py show_rviz:=false > /tmp/wildlife-acceptance-logic.log 2>&1 & launch_pid=$!
wait "$probe_pid"; logic_result=$?
kill -INT "$launch_pid" 2>/dev/null || true
wait "$launch_pid" || true
cat /tmp/wildlife-acceptance-logic.json
export ROS_DOMAIN_ID=78
timeout -s INT 50 ros2 launch wildlife_bringup gazebo.launch.py > /tmp/wildlife-acceptance-gazebo.log 2>&1 & gz_pid=$!
timeout -s INT 50 ros2 run wildlife_core visualization_node > /tmp/wildlife-acceptance-vis.log 2>&1 & vis_pid=$!
timeout -s INT 50 ros2 run rviz2 rviz2 -d src/wildlife_bringup/rviz/wildlife.rviz > /tmp/wildlife-acceptance-rviz.log 2>&1 & rviz_pid=$!
python3 tests/gazebo_probe.py > /tmp/wildlife-acceptance-gazebo.json 2>&1; gz_result=$?
kill -INT "$gz_pid" "$vis_pid" "$rviz_pid" 2>/dev/null || true
wait || true
cat /tmp/wildlife-acceptance-gazebo.json
exit $((logic_result + gz_result))
