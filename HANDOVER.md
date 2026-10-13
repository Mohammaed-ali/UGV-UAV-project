# UAV / UGV export handover

Snapshot date: **13 October 2026**, Asia/Riyadh. Target:
`Mohammaed-ali/UGV-UAV-project`, branch `main`.

## Inspected state and authority

The ROS workspace at
`/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3` was inspected at
`43c8f66f2d1b6500cafef75fca21c2671d379ce0`, on
`codex/v0.5-synthetic-dataset`. Its 25 original reachable commits, four original
branches and three original tags are preserved without rewriting their hashes.
The original `v0.4-final` commit is
`949baba06fea505147b5a1cff11a53bb523827a4`.

The older actual repository is nested at
`wildlife_ws_ros2_jazzy_v0_2_final/wildlife_ws`. Its V0.2 and early V0.3 branches
are also exported as `history/v02/*`. Its tag is shared with the primary history.
Top-level `.git` directories in the legacy folder roots are empty placeholders,
not additional repositories. Each actual repository lists only its original
checkout as a worktree. The managed Codex worktree directory and this chat's
artifact list contain no additional active or archived worktrees.

`history/ros-all-refs.bundle` and `history/v02-all-refs.bundle` additionally retain
all original refs, including Codex tree snapshot refs. Three dangling ROS trees
are recovered under `history/unreachable-trees/`; no dangling V0.2 objects were
reported. Dependency submodules are clean and pinned in `export/dependencies.json`.

The main export continues from the original ROS HEAD and includes the additional
local handoff files and evidence. Original file bytes, SHA256, Git classification,
export location and reason for each omission or redaction are recorded in
`export/file-inventory.tsv`. The root ROS workspace remains at this repository's
root; Fieldlab is under `Simulation/`. The earlier folders are under `legacy/`.
The original local files and checkouts were retained. Assembly, Git commits and
uploads were performed from a separate temporary checkout.

## Current implementation

**ROS V0.4:** nine packages and frozen typed `DroneState`, `Detection` and `Target`
interfaces. Existing release evidence covers single/two/eight-PX4 mission gates,
moving-target observation and health/reassignment. Camera acceptance is scoped
to 640×480 at 10 Hz. The ROS UGV is a logical deployment authority with a Gazebo
display proxy; its docking status means measured home landing/disarm, not physical
tray contact. General collision avoidance, eight-camera perception and exact
image-time moving-target localization are not established. See
`README_ROS.md`, `docs/V0_4_VALIDATION.md`, `docs/V0_4_SCOPE.md` and `docs/DEMO_GUIDE.md`.

**ROS V0.5-B1:** the offline synthetic dataset generator passed Gates 0–10 in
the retained evidence. The final `gazebo_aerial_v1` dataset has 10,000 accepted
frames split 8,000/1,000/1,000, with native visible boxes and explicit ignored-target
metadata. Pilot, smoke, rejected, determinism and crash/resume data are also retained.
This milestone includes no detector training. See `docs/dataset/DATASET_REPORT.md`,
`docs/dataset/CONTINUATION_RESULTS.md` and the generator README. Historical handoffs
may describe incomplete earlier gates; the final report and Git evidence supersede them.

**Fieldlab:** independent React/Three.js/Vite browser, FastAPI/WebSocket gateway,
Gazebo Harmonic physics, PX4 SITL, four/six-wheel carrier, eight aircraft, carousel
trays, image detector and AprilTag recovery. Selected native city, physical fleet,
person/car tracking and contact/disarm/latch gates have retained passes. Building
occlusion discovery and the latest browser following trials retain failures or
unverified coverage. Do not promote the prototype to uninterrupted eight-camera
tracking. `Simulation/docs/LIVING_CITY_VALIDATION.md`, `Simulation/VALIDATION.md`
and their JSON artifacts are the authority.

The export itself verifies preservation and archive integrity. It does not repeat
the expensive flight/dataset gates or certify a new Windows/WSL runtime.

## Windows access

Install Git for Windows and [Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage), then clone:

```powershell
git lfs install
git -c core.longpaths=true clone https://github.com/Mohammaed-ali/UGV-UAV-project.git
cd UGV-UAV-project
git config core.longpaths true
git lfs pull
git lfs fsck
```

Open this folder in Windows Codex and read this handover plus the chat index.
Source, documents, media and transcripts can be reviewed on Windows. Linux shell
scripts, ROS/Gazebo bindings, Linux virtual environments and PX4 binaries require
a Linux environment. **Ubuntu 24.04 in WSL2 is the proposed Windows-side runtime;
it has not been validated for this export.** Clone into its Linux filesystem for
builds, preserving executable bits and symlinks. GPU rendering, WSLg, DDS loopback,
QGroundControl and camera timing need a staged check on that installation. Begin
with logic/source checks, then one aircraft before a fleet.

Older copied docs retain original absolute paths as historical context. Export
runtime scripts already derive their project roots. The optional Fieldlab asset
copy helper has one export-only change: it resolves reference assets through the
combined repository's `tools/synthetic_dataset` directory. The original version
is retained locally and in the source inventory. No mission or controller logic
was changed for the export.

## Restore datasets

Every original dataset file has an individual SHA256 in `export/file-inventory.tsv`.
Each independently extractable tar/zstd part has a compressed checksum and member
count in `export/archives.json`; each part is below 900 MiB before compression.
The final dataset spans six parts. Archive paths contain the original `datasets/`
directory names. After LFS download, in Ubuntu/WSL:

```bash
sudo apt install zstd
python3 export/restore_datasets.py --dataset gazebo_aerial_v1 --verify-only
python3 export/restore_datasets.py --dataset gazebo_aerial_v1
# Restore every available historical dataset:
python3 export/restore_datasets.py
```

The helper verifies archive and member hashes, refuses mismatching existing files
unless `--overwrite` is explicit, and reconstructs `datasets/` beneath this
repository root. Budget approximately 17 GB for a full clone, including the Git
LFS cache, and another 8 GB if restoring all datasets. Dependency checkouts/builds
need additional space.
The export validation streamed all 69,053 archived files and checked their hashes.

The preserved `data.yaml` contains the original absolute Ubuntu `path:`. A future
consumer on another installation should use a separate configuration copy with
its local dataset root. Original manifests, metadata and completion hashes should
remain intact. Generator resume identity also checks the recorded code revision
and Git HEAD; the export commit is a new commit, so it must not be presented as
the original capture revision when resuming an incomplete historical run.

## Reconstruct Linux prerequisites and dependencies

The inspected host uses Ubuntu 24.04, ROS 2 Jazzy and Gazebo Harmonic 8.15.0.
Follow the official [Jazzy Ubuntu installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
and [Harmonic Ubuntu installation](https://gazebosim.org/docs/harmonic/install_ubuntu/).
Install colcon, rosdep, `ros-jazzy-ros-gz`, `ros-jazzy-cv-bridge`, RViz, Python
venv/build tools, CMake, Ninja, compilers, FastDDS/FastCDR and fmt development
packages. Install Gazebo simulation/transport/messages development and Python
bindings as required by the pinned PX4 build and `Simulation/scripts/build_city.sh`.
`export/host-packages.tsv` records installed package versions; it is evidence,
not a instruction to install unrelated desktop packages.

Upstream clean dependencies are omitted because they are reconstructible. Exact
root and recursive submodule pins are in `export/dependencies.json`, with an
individual dependency file omission ledger. The main pins are:

| Dependency | Commit |
| --- | --- |
| PX4-Autopilot | `d6f12ad1c4f70ad3230afd7d86e971421e02fef4` |
| px4_msgs | `86d8239e962f6939e05c3737784f60c02fa884db` |
| Micro-XRCE-DDS-Agent | `73622810d984349b80bbac0ef55fc0b694d62222` |

Use a dependency directory without spaces. After installing prerequisites:

```bash
export WILDLIFE_DEPS_DIR="$HOME/wildlife_px4_dependencies"
export FIELDLAB_DEPS="$WILDLIFE_DEPS_DIR"
bash export/setup_pinned_dependencies.sh
```

This helper clones the exact pins, initializes PX4 submodules, builds the message
overlay, isolates PX4 Python build requirements, and invokes the existing Agent
and PX4 build helpers. It refuses to reset existing checkouts. It is syntax
checked here; a clean rebuild on Windows/WSL has not been performed. If additional
PX4 system prerequisites are reported, follow its pinned `Tools/setup` documentation
and rerun the relevant original build helper.

Download the QGroundControl v5.1.5 Linux AppImage from the official release and
verify the SHA256 in `docs/DEPENDENCY_PINS.json`. Place it at
`$WILDLIFE_DEPS_DIR/QGroundControl-x86_64.AppImage` and make it executable.
The binary is omitted and its pin retained. `docs/DEPENDENCIES.md` explains the
system FastDDS/FastCDR Agent flags and preserved build constraints.

## Startup

Set the two dependency variables in each terminal, then build the ROS overlay:

```bash
export WILDLIFE_DEPS_DIR="$HOME/wildlife_px4_dependencies"
export FIELDLAB_DEPS="$WILDLIFE_DEPS_DIR"
source /opt/ros/jazzy/setup.bash
source "$WILDLIFE_DEPS_DIR/msgs-install/setup.bash"
rosdep install --from-paths src --ignore-src --skip-keys px4_msgs -r -y
./scripts/check_prereqs.sh
./scripts/build_ros.sh
source scripts/environment.sh
ros2 launch wildlife_bringup subject1_demo.launch.py
```

Initialize/update rosdep on a new Linux installation before its install command.
For PX4 demos, start QGroundControl in another configured terminal with
`./scripts/start_qgc.sh`; then use `./scripts/start_px4_single.sh` or the real-camera
profile documented in `docs/DEMO_GUIDE.md`. Do not build while a flight is running.

For Fieldlab, install Node.js compatible with its Vite 7 build and pnpm 10; the
lockfile is preserved. Recreate the Python environment and frontend dependencies:

```bash
cd Simulation
export FIELDLAB_DEPS="$HOME/wildlife_px4_dependencies"
./scripts/setup.sh
./scripts/start.sh
```

Open **http://127.0.0.1:8765**, choose a supplied mission, initialize the simulator,
wait for telemetry, then start the mission. Keep the terminal open; Ctrl+C ends
its gateway. A compiled `dist/` snapshot is preserved, but `.venv`, `node_modules`
and the native plugin must be recreated. The detector weights, textures, models,
licenses, scenarios and validation evidence are exported. `Simulation/requirements.txt`,
`pnpm-lock.yaml` and `export/fieldlab-pip-freeze.txt` record dependencies.

Fieldlab owns ROS domain 93, Gazebo partition `fieldlab-independent-93` and XRCE
port 8889. Its PX4 rootfs belongs to a space-free temporary directory. Run one
Fieldlab runtime at a time. Internet sharing can be started anew with
`./scripts/share.sh`; it must create a new key because original keys, private links
and their credential-bearing logs were excluded. Do not reuse a transcript's old
share URL. Stop only processes owned by this project.

## Exclusions, redactions and chat limits

`export/file-inventory.tsv` records all inventoried project files, including
tracked, untracked and ignored files. Original bulk ignored datasets and validation
artifacts are exported. Rebuildable `build/`, `install/`, virtual environments,
frontend packages, bytecode/test caches, native plugin builds, downloaded tunnel
binary and transient process ownership/generated-world files are omitted.
Original ROS build/test logs and meaningful Fieldlab runtime diagnostics are
retained. Empty app/sandbox metadata directories are not project repositories.

Authentication stores, access keys, temporary private share links and sharing logs
were excluded. Eight credential/link-bearing evidence files and relevant transcript
text were sanitized; original hashes and the changed-file ledger are retained.
Harmless test hostnames are retained so test source remains functional.

`chats/README.md` links **46 local transcripts and 10 cloud reader snapshots**.
It includes local archived project chats and review chats, with separate tool
records and available pasted-text/image/video/document attachments. The course
proposal output/template and loose project concept videos were collected from
outside the primary folders. Unrelated MCQ coursework launched from the same
working directory is explicitly excluded.

The linked conversation `6ac54926-2e50-83eb-9bb2-fbd1e6113b26` could not be
resolved; the reader reported an unavailable durable host. Cloud readers returned
bounded snapshots with no older-page cursor; some message items are explicitly
truncated. Full older cloud/account history, deleted chats, uncached content and
images embedded only in inaccessible history cannot be reconstructed by this
export. Local tool logs retain any truncation that was already stored. The active
export conversation is a snapshot before the final commit/upload. These are readable
archives, not a supported automatic import of live Codex conversations. Raw app
databases, authentication stores, system/developer prompts and internal reasoning
are not published.

See `export/VALIDATION.md` for export-specific checks and their actual results.
