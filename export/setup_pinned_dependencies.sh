#!/usr/bin/env bash
# Clone clean upstream pins into a NEW directory; prerequisites must be installed.
set -euo pipefail
EXPORT_ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
EXPORT_DEPS="${WILDLIFE_DEPS_DIR:-$HOME/wildlife_px4_dependencies}"
if [[ "$EXPORT_DEPS" == *' '* ]]; then
  printf '%s\n' 'Use a dependency directory without spaces; PX4 build tooling requires it.' >&2
  exit 1
fi
if [[ -e "$EXPORT_DEPS/PX4-Autopilot" || -e "$EXPORT_DEPS/px4_msgs" || -e "$EXPORT_DEPS/Micro-XRCE-DDS-Agent" ]]; then
  printf '%s\n' 'Dependencies already exist. Inspect their pins; this helper refuses to reset existing checkouts.' >&2
  exit 1
fi
mkdir -p "$EXPORT_DEPS"
git clone https://github.com/PX4/PX4-Autopilot.git "$EXPORT_DEPS/PX4-Autopilot"
git -C "$EXPORT_DEPS/PX4-Autopilot" checkout d6f12ad1c4f70ad3230afd7d86e971421e02fef4
git -C "$EXPORT_DEPS/PX4-Autopilot" submodule update --init --recursive
git clone https://github.com/PX4/px4_msgs.git "$EXPORT_DEPS/px4_msgs"
git -C "$EXPORT_DEPS/px4_msgs" checkout 86d8239e962f6939e05c3737784f60c02fa884db
git clone https://github.com/eProsima/Micro-XRCE-DDS-Agent.git "$EXPORT_DEPS/Micro-XRCE-DDS-Agent"
git -C "$EXPORT_DEPS/Micro-XRCE-DDS-Agent" checkout 73622810d984349b80bbac0ef55fc0b694d62222
source /opt/ros/jazzy/setup.bash
colcon --log-base "$EXPORT_DEPS/msgs-log" build --base-paths "$EXPORT_DEPS/px4_msgs" \
  --build-base "$EXPORT_DEPS/msgs-build" --install-base "$EXPORT_DEPS/msgs-install" \
  --parallel-workers 2
python3 -m venv "$EXPORT_DEPS/px4-venv"
"$EXPORT_DEPS/px4-venv/bin/python" -m pip install -r "$EXPORT_DEPS/PX4-Autopilot/Tools/setup/requirements.txt"
export WILDLIFE_DEPS_DIR="$EXPORT_DEPS"
"$EXPORT_ROOT/scripts/build_agent.sh"
"$EXPORT_ROOT/scripts/build_px4.sh"
printf 'Pinned dependencies built in %s\n' "$EXPORT_DEPS"
printf 'Set WILDLIFE_DEPS_DIR and FIELDLAB_DEPS to this directory in each startup terminal.\n'
