# V0.5-B1 continuation handoff — safe stop during Gate 4

Prepared on 2026-10-05, Asia/Riyadh, from the actual repository and retained
evidence. **This milestone is unfinished. Gates 0–3 passed; Gate 4 is partially
validated. Gates 5–10 have not run.** The immediate Gazebo operations completed
before this handoff. No larger gate was started after the handoff request.

All repository-relative paths below resolve under this exact primary workspace:

```text
/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3
```

The full original task is preserved in `docs/dataset/V0_5_B1_MASTER_PROMPT.md`.
Read it together with this handoff; the next session needs no conversation
history to continue. `docs/dataset/V0_5_B1_FILE_INVENTORY.tsv` enumerates the
individual source/document/evidence files with absolute paths and purposes.

## 1. Repository state

| Item | Actual state at safe stop |
| --- | --- |
| Primary workspace | `/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3` |
| Branch | `codex/v0.5-synthetic-dataset` |
| Current HEAD | `947cecb5ccaf607b7466ed8dff29651efe730f9f` |
| Frozen `v0.4-final^{commit}` | `949baba06fea505147b5a1cff11a53bb523827a4` |
| Original branch / HEAD | Clean `codex/v0.4-development`, at the same frozen tag commit |
| Workspace policy | Same physical repository; no copy, rename or worktree created |
| Runtime changes | None under `src/` or the existing root `scripts/` |
| Bulk data | Existing local `datasets/`, ignored by Git |
| Safe stop | All recorded generator, service-worker and Gazebo PIDs absent |

The branch was created in this workspace with:

```bash
git status
git branch --show-current
git rev-parse HEAD
git rev-parse 'v0.4-final^{commit}'
git switch --detach v0.4-final
git switch -c codex/v0.5-synthetic-dataset
```

Four implementation checkpoints were committed, in this order:

| Commit | Purpose |
| --- | --- |
| `e323ebe0a4bb088e98fcc77c62ec1b4fd8a43b8b` | Offline generator, original pinned assets, Phase-0/alignment evidence |
| `fd1ebd194533ff2af356a7307d748146d3dbff66` | JSON-stable string histogram keys after smoke statistics failure |
| `d7252090afb941ff34ad296184c523c833c9c98e` | Smoke validation/visual QA evidence and ignored-target previews |
| `947cecb5ccaf607b7466ed8dff29651efe730f9f` | Sort numerical samples before summarizing, eliminating traversal-order roundoff |

The handoff and final evidence preservation are deliberately saved as
**uncommitted documentation/evidence**, while the pipeline implementation is
committed at HEAD above. Do not discard them. No generator source repair was
made after the safe stopping point. The exact final status is retained in
`docs/dataset/evidence/handoff_git_status.txt`; uncommitted paths are:

```text
modified: docs/dataset/PHASE0.md
modified: docs/dataset/evidence/smoke_gate.json
modified: tools/synthetic_dataset/README.md
new: docs/dataset/V0_5_B1_HANDOFF.md
new: docs/dataset/V0_5_B1_MASTER_PROMPT.md
new: docs/dataset/V0_5_B1_FILE_INVENTORY.tsv
new: docs/dataset/evidence/determinism.json
new: docs/dataset/evidence/determinism_a2.log
new: docs/dataset/evidence/determinism_a2_validation.json
new: docs/dataset/evidence/determinism_b2.log
new: docs/dataset/evidence/determinism_b2_validation.json
new: docs/dataset/evidence/determinism_compare2.log
new: docs/dataset/evidence/determinism_attempt2_exact_comparison.json
new: docs/dataset/evidence/determinism_diagnose.py
new: docs/dataset/evidence/determinism_diagnostic.json
new: docs/dataset/evidence/handoff_processes.json
new: docs/dataset/evidence/handoff_static.json
new: docs/dataset/evidence/handoff_git_status.txt
new: docs/dataset/evidence/lighting_probe.py
new: docs/dataset/evidence/smoke_initial_validation_retained.json
```

The tool README and Phase-0 prose now point to the current handoff; Phase-0
final benchmark figures supersede its earlier approximate figures.
`smoke_gate.json` was refreshed after the aggregate-statistics correction.
The new determinism evidence records the unresolved comparison, not a PASS.

Git had no configured author identity. The first commit attempt failed with
“Author identity unknown.” Successful commits used command-scoped identity:

```bash
git -c user.name=Codex -c user.email=codex@local.invalid commit -m '...'
```

No global identity was changed. In restricted Codex execution `.git` mutations
required sandbox escalation; authorization came from the user's explicit
branch/checkpoint instructions. No automatic-approval rejection occurred.

## 2. Exact task and boundaries

**V0.5-B1 — Synthetic Gazebo Aerial Detection Dataset Generator** builds a
reproducible offline Gazebo Harmonic still-image generator and validated
YOLO-format dataset. Exact class order is **0 person, 1 car, 2 truck, 3 bus**.
One intentionally configured scene produces one accepted sample; labels come
from simulator sensors/state, never from a detector.

Preserve the frozen V0.4 release, existing nine ROS packages, typed interfaces,
operator HOLD/RETURN semantics, perception/tracking and PX4 adapter ownership.
No mission controller, state machine, tracker or tenth ROS package is added.
Use the existing repository and unmodified down-camera model. Keep dependencies
lightweight and installed already. Preserve failed attempts and historical
evidence. Commit coherent implementation checkpoints. Report actual measured
PASS/FAIL/limitations; no fabricated capability or acceptance.

Out of scope: **YOLO training; VisDrone download/training; PX4 dataset flight
capture; ROS YOLO integration**; model selection; real-camera collection;
eight-camera flight; moving-target/video data; wildlife/animal classes;
tracker/mission changes; UGV navigation, carrier, docking/mechanical work;
pretrained inference as a core gate; sim-to-real accuracy claims.

Default full target remains **10,000 accepted frames, 8,000/1,000/1,000
train/val/test**. Any changed target requires documented Phase-0/pilot evidence
and an explicit proposal. Nothing below claims a pilot or full dataset exists.

## 3. Gate status, commands and measured evidence

Commands below were run from the primary workspace. Gazebo commands require
`source scripts/environment.sh`; restricted Codex runs needed escalation for
local transport sockets/GPU rendering. These are historical commands, not a
request to rerun passed gates now.

| Gate | State | What actually passed or remains |
| --- | --- | --- |
| 0 — Baseline | **PASS** | Frozen tag/source inspection, prerequisites, nine-package build, 56 test entries, baseline static/launch parsing |
| 1 — Phase 0 | **PASS, known limitations** | Installed native sensors/headless rendering, all four feasible classes, pinned assets/scales, fixed camera, pixel table, benchmark |
| 2 — Ground-truth proof | **PASS** | 21 controlled cases, programmatic checks and actual visual inspection |
| 3 — Smoke | **PASS** | 200 accepted frames, full validator, 100 previews and factor/low-IoU QA reviewed |
| 4 — Determinism | **PARTIALLY VALIDATED; current comparator FAIL** | Two independently rendered 50-frame sets validate individually and match RGB/YOLO/scenarios exactly; raw readback float/sign comparator still needs repair/tests |
| 5 — Crash/resume | **NOT TESTED** | Script implemented; no live SIGKILL/resume test yet |
| 6 — 2,000 pilot | **NOT STARTED** | No pilot dataset |
| 7 — >=300-frame audit | **NOT STARTED** | Smoke audit has only 200 frames; insufficient for this gate |
| 8 — Full dataset | **NOT STARTED** | No 10,000-frame dataset |
| 9 — Full validator | **NOT STARTED** | Smoke/repeat validators do not substitute |
| 10 — Final V0.4 regression | **NOT RUN after implementation** | Baseline passed; final build/test/static regression remains required |

### Gate 0

Inspected `README.md`, `ARCHITECTURE.md`, `V0_4_BUILD_REPORT.md`,
`V0_4_TEST_RESULTS.md`, `docs/V0_4_VALIDATION.md`,
`docs/V0_4_CAMERA_GEOMETRY.md`, `docs/DEMO_GUIDE.md`, simulation worlds,
camera SDF, perception/config/geometry, bringup altitude profiles, existing
`set_pose` usage and validation/release scripts. No applicable `AGENTS.md`
was found in the repository/ancestors during the initial inspection.

```bash
scripts/check_prereqs.sh
scripts/build_ros.sh
source scripts/environment.sh
colcon test --base-paths src --executor sequential
colcon test-result --verbose
```

Results: nine packages built in about 6.38 s; **56 entries, zero errors,
failures or skips**. Baseline static checks parsed 67 Python, 23 XML/SDF/config,
14 YAML and 24 shell files and generated all 11 launch descriptions.
Evidence: `docs/dataset/evidence/baseline.json`, `baseline_tests.log`,
`baseline_static.json`. Initial/tag state is recorded in baseline.json.

### Gates 1–2

```bash
source scripts/environment.sh
python3 tools/synthetic_dataset/scripts/phase0.py
python3 tools/synthetic_dataset/scripts/record_gate.py feasibility \
  docs/dataset/evidence/phase0 --visual-review-note 'Specific actual inspection findings'
```

Native sensor spike/probes also tested the installed SDF examples and
`tools/synthetic_dataset/worlds/sensor_spike.sdf`. The historical standalone
`sensor_spike.py` contains temporary probe paths/partition choices; it is
preserved evidence, not the preferred production CLI.

Evidence: `PHASE0.md`, `evidence/dependencies.json`, `native_sensors.{json,log,png}`,
`lighting_changes.{json,log}`, `phase0.log`, `phase0_gazebo.log`,
`phase0/report.json`, `phase0/alignment.json`, `phase0/benchmark.json`,
`phase0/pixel_size_feasibility.csv`, controlled labels/metadata/contact sheet,
and `evidence/feasibility.json`. Metrics are detailed in sections 7–13.

### Gate 3

```bash
source scripts/environment.sh
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --config tools/synthetic_dataset/configs/synthetic_dataset.yaml \
  --count 200 --seed 12345 --output datasets/gazebo_aerial_smoke --headless
python3 tools/synthetic_dataset/scripts/validate_dataset.py datasets/gazebo_aerial_smoke
python3 tools/synthetic_dataset/scripts/preview_dataset.py datasets/gazebo_aerial_smoke
python3 tools/synthetic_dataset/scripts/record_gate.py smoke datasets/gazebo_aerial_smoke \
  --visual-review-note 'Specific actual inspection findings'
```

The initial automatic validator failed only aggregate statistics, as described
in section 14. Aggregates/manifests were rebuilt from valid completion records
with `storage.summarize`; original RGB, YOLO and per-frame metadata were
preserved. Standalone validation and the smoke gate subsequently passed.
Actual accepted/attempted count: **200/200**, zero rejected captures.

Evidence copies: `smoke_validation.json`, `smoke_statistics.json`,
`smoke_annotation_audit.json`, `smoke_preview_index.json`,
`smoke_representative.jpg`, `smoke_gate.json` under `docs/dataset/evidence/`.
Initial failed log/report remain `smoke_attempt1.log`,
`smoke_attempt1_validation.json`, with an extra retained copy in
`smoke_initial_validation_retained.json`. The bulk dataset's current
`qa/validation.json` is PASS, not its historical failure.

### Gate 4 attempted commands

An initial 50-frame run `datasets/determinism_a` exposed a one-ULP summary
order issue, fixed in commit `947cecb`. After that fix, two fresh runs were
rendered consecutively at the same HEAD/config/asset pool:

```bash
source scripts/environment.sh
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --count 50 --seed 12346 --output datasets/determinism_a2 --headless
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --count 50 --seed 12346 --output datasets/determinism_b2 --headless
python3 tools/synthetic_dataset/scripts/check_determinism.py \
  datasets/determinism_a2 datasets/determinism_b2 \
  --report docs/dataset/evidence/determinism.json
```

Both generators accepted **50/50**, no rejected captures, and their own full
validators **PASSED**. Comparator exit code was **1**, status **FAIL**, with
23 exact metadata mismatches and **50/50 identical RGB files**. All YOLO label
files and `manifests/scenarios.csv` match exactly. The count-specific seed
12346 was used because a prior sampled 50-frame set with 12345 missed a
required held-out bus; no class/holdout validation rule was weakened.

Preserved: `determinism_attempt1.{log}` / `determinism_attempt1_validation.json`,
`determinism_a2.log`, `determinism_b2.log`, both corresponding validation JSONs,
`determinism_compare2.log`, `determinism.json`, and immutable historical copy
`determinism_attempt2_exact_comparison.json`. `determinism_diagnose.py` and
`determinism_diagnostic.json` quantify the unresolved metadata issue.

## 4. Current gate and exact stopping point

Work stopped **during Gate 4**, after both independent runs and the failing
comparison finished and their Gazebo/service processes exited. The production
`check_determinism.normalized()` excludes only these measured timing fields:

```text
simulation_timestamp, annotation_timestamp, timestamp_delta_s,
scene_readback_timestamp, settling_sim_seconds, generation_timestamp
```

It then compares remaining dictionaries with exact Python equality. Actual
Gazebo readback can represent the same orientation as `q` or `-q`; minor
roundoff propagates into realized positions, projected boxes and derived IoU.
Capture pose verification already compares quaternion signs correctly, while
the determinism comparator does not.

The diagnostic traversed all 50 normalized record pairs. It found **no
structural/non-numeric differences**, no changed native boxes/YOLO/scenarios,
and only the following numeric categories after aligning quaternion signs:

| Measurement | Maximum absolute difference |
| --- | --- |
| World position components | `1.8189894035458565e-12` m |
| Sign-invariant quaternion components | `3.3306690738754696e-16` |
| Secondary projection coordinates | `4.172306944383308e-11` px |
| Derived IoU | `3.305800078123866e-12` |

There were **58 quaternion sign changes** across realized camera, target and
distractor poses; 27 records match exactly even under the old comparator.
Example frame `scene_994331f2c9664dcc_000001`: actual camera X is 500.0 vs
500.0000000000001; quaternions differ by overall sign and tiny rounding.
The raw recorded measurements remain unchanged. Diagnostic status is
`DIAGNOSTIC_ONLY_GATE_4_NOT_PASSED`.

Next required implementation: repair `check_determinism.py` with explicitly
scoped sign-invariant realized-pose comparison and narrowly justified float
tolerances. Keep commanded scene/config/IDs/classes/label states/native boxes,
YOLO bytes and scenario CSV exact. Do not blanket-ignore poses or approximate
all metadata. Add meaningful regression tests: equivalent signs/tiny rounding
must pass; real position/orientation/box/label/scene changes must fail. Treat
unexpected fields/types/non-finite data as failures. Recompare **the existing
a2/b2 captures**, preserving the original FAIL before writing a PASS report.
Then document the measured equivalence policy and commit a coherent Gate-4
checkpoint. Do not render those sequences again merely to repair comparison.

The current comparator reports RGB equality separately and does not itself
fail on RGB differences, consistent with the master prompt's separate RGB
reproducibility reporting. Here RGB is exact; do not claim renderer determinism
beyond the installed environment and these measured runs.

## 5. Files created/modified and purposes

The companion inventory enumerates every nonignored file under the tool and
dataset documentation, plus `.gitignore`. No runtime ROS source is modified.
The principal source paths are:

| Path | Purpose |
| --- | --- |
| `.gitignore` | Ignore bulk datasets and Phase-0 raw RGB/overlays/runtime, preserve compact evidence |
| `tools/synthetic_dataset/README.md` | CLI/workflow, dependencies, resume semantics and current checkpoint |
| `configs/synthetic_dataset.yaml` under tool | Authoritative factors/thresholds/world/capture/QA/default count/seed |
| `configs/class_mapping.yaml` | Single ordered YOLO/Gazebo class namespace mapping |
| `configs/visdrone_class_map.yaml` | Future mapping preparation only, explicit unresolved categories |
| `assets/LICENSE` | CC0 dedication for original procedural assets only |
| `assets/manifests/assets.json`, `assets.csv` | Complete pinned provenance, dimensions/bounds/geometry/checksums/eligibility |
| `assets/textures/{grass,dirt,road,mixed}_{0,1,2,3}.png` | 16 original 256x256 seeded textures; index 3 test-only |
| `models/person_{0,1,2,3}/model.sdf` | Four human template variants |
| `models/car_{0,1,2,3}/model.sdf` | Four vehicle geometries; car_3 test-only |
| `models/truck_{0,1,2,3}/model.sdf` | Four truck body forms; truck_3 test-only |
| `models/bus_{0,1,2}/model.sdf` | Three bus geometries; bus_2 test-only |
| `models/clutter_{0,1,2,3,4,5}/model.sdf` | Six unlabeled crates/trees/barriers |
| `models/{canopy_mild,canopy_moderate,shadow_wall}/model.sdf` | Supported occluders and deliberate shadow wall |
| `worlds/sensor_spike.sdf` | Installed native sensor proof world |
| `scripts/common.py` under tool | Root/config/camera/asset validation, hashes, UTC, durable atomic writes |
| `scripts/geometry.py` | Quaternion/projection/ground footprint/clip/YOLO/IoU functions |
| `scripts/build_assets.py` | Offline deterministic generation of original pinned assets; not needed per capture |
| `scripts/sampling.py` | Seeded disjoint scene schedules, factors, targets, placement, clutter/lighting |
| `scripts/world.py` | Generated SDF world, preloaded zones/model pool, aligned sensor rig |
| `scripts/gazebo_backend.py` | Owned Gazebo runtime, subscribers, scene RPCs/readback/settling/synchronized capture/annotation |
| `scripts/transport_worker.py` | Persistent isolated service-request process, protobuf JSON-line protocol |
| `scripts/storage.py` | Atomic sample/marker commit, resume checking, aggregate manifests/statistics |
| `scripts/generate_dataset.py` | Required primary CLI, identity/lock/gates/retry/export/validation |
| `scripts/validate_dataset.py` | Standalone full dataset integrity/labels/coverage/leakage/holdout/statistics validator |
| `scripts/preview_dataset.py` | Representative previews, factor sheets, stored-secondary IoU audit and lowest-IoU overlays |
| `scripts/phase0.py` | Reproducible controlled proof, pixel feasibility and actual rendering benchmark |
| `scripts/record_gate.py` | Record validated gate plus explicit real visual-review note |
| `scripts/check_determinism.py` | Two-run comparison; current unresolved exact-realized-metadata bug |
| `scripts/crash_resume_test.py` | Implemented real SIGKILL/resume acceptance harness, not yet run |
| `scripts/sensor_spike.py` | Historical installed sensor probe with temporary probe-path assumptions |
| `tests/test_generator.py` | 30 unit/regression tests including validator corruption checks |
| `docs/dataset/PHASE0.md` | Measured Phase-0 capabilities, decisions and limitations |
| `docs/dataset/V0_5_B1_MASTER_PROMPT.md` | Original task preserved verbatim for continuation |
| `docs/dataset/V0_5_B1_HANDOFF.md` | This continuation record |
| `docs/dataset/V0_5_B1_FILE_INVENTORY.tsv` | Absolute individual paths and purposes |

Paths in the table from `assets/` through `tests/` are below
`tools/synthetic_dataset/`; they are not root ROS package folders.
Individual evidence files and controlled per-case files are enumerated in the
inventory. Sections 3, 12–14 explain their measured meaning and failure status.

Locally retained generated outputs:

| Dataset/root | State/purpose |
| --- | --- |
| `datasets/gazebo_aerial_smoke/` | 200 committed frames, PASS validator, QA completed, 69,703,214 bytes at handoff |
| `datasets/determinism_a/` | Historical 50-frame first attempt; summary roundoff failure, 12,736,173 bytes |
| `datasets/determinism_a2/` | Current comparison A: 50 frames, own validator PASS, 12,736,619 bytes |
| `datasets/determinism_b2/` | Current comparison B: 50 frames, own validator PASS, 12,736,597 bytes |
| `docs/dataset/evidence/phase0/alignment/images/`, `overlays/` | Ignored full-resolution RGB/overlays preserved locally |
| `docs/dataset/evidence/phase0/benchmark/`, `runtime/` | Ignored benchmark PNGs and generated runtime SDF/log/ownership records |

Each dataset contains `images/{train,val,test}/*.png`, matching `labels/*.txt`,
`metadata/frames/{split}/*.json`, `metadata/{train,val,test}.jsonl`, `.state/*.json`,
`.run.json`, `.lock`, `data.yaml`, `README.md`, `manifest.json`, `statistics.json`,
`manifests/{generation_config.yaml,class_mapping.yaml,visdrone_class_map.yaml,
assets.json,assets.csv,scenarios.csv,files.sha256.json}`, `qa/validation.json`,
and `runtime/run_*/{world.sdf,gazebo.log,owned_processes.json,...}`.
Smoke also has `qa/previews/`, `qa/review_pages/001.jpg` through `004.jpg`,
`qa/contact_sheets/`, `qa/low_iou/*.png`, its contact sheet,
`qa/annotation_audit.json`, `qa/preview_index.json`, `qa/representative.jpg`.
Do not commit bulk dataset directories. `docs/dataset/DATASET_REPORT.md`
does **not yet exist** and remains a required final deliverable.

## 6. Implemented architecture

The primary CLI loads and validates pinned configuration/assets and the
unaltered repository camera. A SHA-derived RNG per master-seed/sample index
produces the intended scene and exact split/factor schedule. Each still scene
has a stable ID, digest and unique seed family; continuous camera/target yaw,
altitude/angle jitter, target variants/positions, family-specific sun parameters,
background texture choice and clutter/occlusion vary within the recorded policy.

One generated headless world preloads 16 texture zones (240 m surfaces separated
by 500 m), three copies per each of 15 target variants, nine clutter/occluder
models and a static aerial rig. Unused models stage at X=-1000, Z=-50, outside
the camera frustum. UserCommands, Physics, SceneBroadcaster and Sensors/Ogre2
plugins are installed/used. `set_pose_vector` moves the rig/active models and
deactivates prior models; `light_config` changes the actual directional sun.

The main process subscribes to RGB, native visible boxes, pose info and
CameraInfo. A private persistent worker owns blocking service requests,
communicating via JSON lines/base64 protobuf over pipes in the same isolated
Gazebo partition. Capture waits for actual poses, settling and fresh matching
sensor timestamps. Primary native visible boxes are matched to intended
class/instances using separately projected actual primitive geometry.

Per-frame metadata retains intended scene, commanded and actual camera/target
poses, camera model/live K, identity/seeds, lighting/background parameters,
dimensions/ranges/distance category, both box methods/IoU, truncation,
label state/ignored reason, generation UTC and measured simulation timestamps.
Some range/yaw/factor descriptors originate in the intended scene, whereas
secondary geometry explicitly uses actual readback poses. There is no claimed
independent light-state subscriber/photometric calibration or pixel visibility
fraction; realized RGB lighting was tested empirically.

The writer atomically writes RGB, YOLO text and per-frame JSON and then the
hash-bearing completion marker last. Split JSONL, scenario CSV, data.yaml,
manifest, file index and statistics are rebuilt from committed records sorted
by index. A process lock prevents concurrent writers. Resume validates complete
records, skips valid frames and regenerates corrupt/incomplete frames. Gate
guards validate Phase-0 camera/asset hashes; counts over 200 require smoke;
counts over 2,000 require pilot and audit. Determinism/crash gate ordering is
still a required manual discipline rather than a complete CLI guard.

The standalone validator checks every split and filesystem/state/metadata/
labels/manifests/hash/coverage/holdout/statistics relationship. QA selects
100 representative previews with seeded factor set coverage and random fill,
25-image review pages, factor sheets, up to 300 representative audit frames,
and 50 lowest-IoU frame overlays. The secondary box method is independent of
the native renderer but also supplies box-to-instance association, so do not
claim a completely independent third instance-association proof.

## 7. Verified installed Gazebo capabilities

No dependency was installed or upgraded. Existing versions:

| Component | Verified installed version |
| --- | --- |
| Gazebo Harmonic / gz-sim8 | 8.15.0 |
| gz-sensors8 | 8.2.2 |
| gz-rendering8 | 8.2.3 |
| gz-transport13 / Python transport13 | 13.6.0 |
| gz-msgs10 / Python msgs10 | 10.4.0 |
| numpy / OpenCV / PyYAML | 1.26.4 / 4.6.0 / 6.0.1 |

`gz` is exposed after sourcing the existing project environment; executable is
`/opt/ros/jazzy/opt/gz_tools_vendor/bin/gz`. Actual invocation:

```bash
gz sim -s -r --headless-rendering -v 2 <generated-world.sdf>
```

Observed renderer: **Ogre2, EGL headless, OpenGL 3+**, NVIDIA GeForce RTX 4050
Laptop GPU; rendering log reported OpenGL 4.5.0 NVIDIA 595.91.07. Restricted
default sandbox devices/sockets were insufficient; escalated actual runs worked.

The retained spike received **five messages each** for headless RGB, visible
2D, full 2D, oriented 3D, semantic segmentation and instance segmentation,
plus **22 pose/info messages**, and observed all labels 10/20/30/40.
Relevant spike topics: `/rgb`, `/visible`, `/full`, `/three`,
`/semantic/labels_map`, `/instance/labels_map`,
`/world/dataset_spike/pose/info`. Semantic pixels repeat the class label in
RGB; instance pixels encode `[instance_low_byte, instance_high_byte, class_label]`.
Model labels use installed `gz-sim-label-system`.

Production uses RGB/native visible 2D only; segmentation/full/3D support is
**tested capability**, not a claim that all sensors run in bulk capture.
Production RGB is `/dataset/rgb`, boxes `/dataset/visible`, CameraInfo
`/dataset/rgb/camera_info` and poses `/world/aerial_dataset/pose/info`.
References inspected for this installed family:
[sensors 8 segmentation](https://gazebosim.org/api/sensors/8/segmentationcamera_igngazebo.html),
[sim 8 headless rendering](https://gazebosim.org/api/sim/8/headless_rendering.html),
installed sensor examples/headers and gz-sim8 UserCommands source. Do not infer
behavior from a different version's documentation.

## 8. Exact camera and altitude values

Authoritative unchanged source:
`src/wildlife_simulation/models/mono_cam/model.sdf`.
SHA-256: `7ad6bc5ea6d3e708149246edea6219aebba80f9773e59ea9a7ca78f067a9c765`.

| Property | Value |
| --- | --- |
| Resolution / update rate | 640x480 / 10 Hz |
| Horizontal FOV | 1.74 rad |
| Derived vertical FOV, square pixels | 1.453401713389793 rad |
| Near / far clipping | 0.1 / 100.0 m |
| Calculated fx = fy | 269.9681840122649 px |
| Principal point cx / cy | 320 / 240 px |
| Live fx / fy | 269.96816635131836 / 269.9681854248047 px |
| Live K | `[269.96816635131836,0,320, 0,269.9681854248047,240, 0,0,1]` |
| Noise | None configured in source SDF; no image augmentation implemented |
| Optical convention | Gazebo +X forward, -Y image right, -Z image down; ENU world |
| Quaternion serialization | xyzw |
| Nominal AGL buckets | 10, **15**, 20, 30, 40 m; +/-1 m jitter |
| Off-nadir buckets | 0,10,20,30 degrees; +/-2 degrees, clamped at zero |
| Yaw / roll | Continuous uniform [0,360) degrees / fixed zero roll |

Calculated/live K agreement is enforced within 0.01 px. RGB and box sensors
share the rig link with zero relative pose and identical image size/FOV/
clips/rate. The freely teleported rig records the optical-center world pose
directly; it does not need PX4 or a UAV body/mount transform. Fixed intrinsics,
FOV, principal point, resolution and clipping are not randomized.

V0.4 camera search profiles use 10 and **15 m**; 15 m was deliberately added
for the operational two-camera profile. Logical standoff search+3 yields
13/18 m; these are included only in the feasibility table, with nearby 15/20 m
already represented in dataset quotas. Camera-free fleet layers 10+1.5*i did
not create extra dataset buckets. AGL is actual camera Z minus local ground
reference Z=0, and both nominal/commanded and actual values are recorded.

## 9. Assets, provenance, scale and holdout

Pinned pool: **40 original procedural assets**: 15 targets (4 person, 4 car,
4 truck, 3 bus), 16 background textures (four per family), nine distractor/
occluder structures. No external model/mesh/texture/Fuel download is needed.
Regular generation reads/verifies pinned assets, not mutable network resources.
Original assets are CC0-1.0, separately from upstream runtime/code licensing.

Manifests record source `repo:` URI, procedural author/provider/version,
creation date 2026-10-05, download date null, license, checksum, local path,
dimensions, min/max bounds, primitive parts, sampled geometry points, notes and
split eligibility. Min geometry Z is normalized to zero before placement.
Recorded dimensions include attachments/wheels; no imported scale assumption.

| Target | Actual L/W/H bounds in metres, rounded for display |
| --- | --- |
| person_0 / 1 / 2 / 3 | `.252/.700/1.680`; `.277/.810/1.750`; `.273/.923/1.820`; `.465/1.031/1.880` |
| car_0 / 1 / 2 / 3 | `4.200/1.860/1.420`; `4.650/1.956/1.550`; `4.900/2.004/1.650`; `4.700/2.100/1.850` |
| truck_0 / 1 / 2 / 3 | `6.255/2.345/2.525`; `7.655/2.532/3.400`; `8.655/2.580/3.200`; `9.055/2.628/3.500` |
| bus_0 / 1 / 2 | `10.520/2.580/3.000`; `12.020/2.628/3.300`; `12.820/2.628/4.050` |

These recognizable, low-detail primitive representations are not realistic
scanned/rigged models. Persons differ in height, arm configuration/backpack,
but **share one human template**. Vehicles differ in geometry dimensions/body/
cabin/roof/type, including box/open-bed/tanker trucks. Recoloring is not counted
as independent geometry. All are static ground scenes, without dynamic contact
simulation or human animation.

Test-only target models: **car_3, truck_3, bus_2**. Persons remain eligible in
all splits: **no independent person-model holdout claim**. Background families
each have three train-visible textures (indices 0–2) plus test-only index 3;
test backgrounds use that held-out index. Test target scenes may include both
normal and held-out eligible models; the validator requires all configured
held-out assets to appear in test and none to leak to train/val. Texture holdout
tests a procedural pattern family, not a new real-world domain.

## 10. Annotation design and accounting

Authoritative labels: installed Gazebo **native visible 2D bounding-box camera**.
Secondary cross-check: pinhole projection of sampled original primitive surface
geometry (box vertices/cylinder surfaces) transformed by **actual simulator
camera and target poses**, using the fixed camera. It describes full geometry,
whereas native visible boxes can shrink under occlusion.

| Class | YOLO ID | Gazebo label |
| --- | --- | --- |
| person | 0 | 10 |
| car | 1 | 20 |
| truck | 2 | 30 |
| bus | 3 | 40 |

Native messages expose class labels, not stable per-instance IDs. A greedy
maximum-IoU, same-class match associates native boxes to projected instances
(threshold 0.01). Unexplained native boxes reject capture. This method deserves
particular pilot QA for crowded/occluded same-class targets; do not claim a
proved ambiguity detector beyond what code actually implements.

Native integer maxima are inclusive: add 1 to maximum X/Y, convert to half-open
coordinates and clip to `[0,640] x [0,480]`. Positive finite rectangles normalize
to YOLO center/width/height with nine decimal places. Min side **3 px**, min
area **9 px²**. Below-threshold native boxes produce no YOLO row but retain
`ignored_tiny` and the reason/bbox in metadata. Each intended target has one
of `labelled`, `ignored_tiny`, `ignored_outside`, `ignored_occluded`.

No native box + projected outside => ignored_outside; no native box + projected
inside => ignored_occluded. These are operational reasons, not measured visible
pixel fractions. Positive scenes must have at least one exportable label.
Negative and distractor-only frames have valid empty label files. Distractors
never receive target labels. Truncation is tracked from full-vs-clipped projection;
normal non-edge placement must fit, explicit edge challenge permits clipping.
Native/secondary IoU is **not** a pixel visibility fraction; visible_fraction
and visibility_threshold are null.

The preview audit recomputes IoU from stored native and secondary boxes and
checks that stored IoU reproduces. It currently **does not freshly reproject
geometry from manifests/poses during that audit**. The secondary boxes were
computed independently during capture. Before claiming stronger end-to-end
independence, consider fresh projection in the Gate-7 audit and document it.

## 11. Capture integrity and service architecture

Per sample: update all poses and light; require pose/info newer than the old
RGB timestamp; read back every commanded entity (including newly staged
deactivated objects); verify position tolerance **0.001 m** and sign-invariant
quaternion tolerance **1e-5**. Then wait **three 10-Hz sensor periods** (>=0.3
simulation seconds) after pose readback. Capture a fresh RGB/box pair with
timestamp difference <=**0.001 s**. Controlled retained pairs had delta zero.
Actual readback time, pair timestamps, settling duration and commanded vs
actual poses remain in metadata. Buffers hold 32 timestamp-keyed messages.
RGB dimensions/layout and live CameraInfo are checked; native-box errors cause
capture rejection rather than silently exporting invented boxes.

Earlier synchronous Python transport service requests made in the process
handling subscriber callbacks began failing after several scene updates.
Failures occurred at requested RTF 0, 8 and 1; this did **not** establish a
high-RTF-only issue. Shared service/subscriber execution is the observed
interaction; GIL/dispatcher blocking is a plausible interpretation, **not a
proved internal binding root cause**. Moving RPC requests into a separate
persistent Python worker empirically resolved the failures. Keep that worker
architecture unless an evidence-backed improvement is needed.

Partitions are isolated UUIDs, with GZ_IP=127.0.0.1 before Node construction.
The worker uses the same partition. Owned Gazebo runs in its own process group;
normal cleanup sends SIGINT, waits up to eight seconds, then kills only that
owned group if necessary. Worker closes on pipe EOF, with bounded fallback.
`runtime/owned_processes.json` records generator PID, Gazebo PGID, worker PID,
partition. SIGKILL may orphan the separate Gazebo group, so the crash harness
cleans only the recorded owned group. Never broadly pkill other simulations.
Handoff's read-only ownership/PID check found no live recorded processes;
`handoff_processes.json` retains it. PIDs may be reused later: inspect before
acting on historical ownership files.

## 12. Failed attempts and lessons retained

| Failure | Evidence / resolution / remaining qualification |
| --- | --- |
| Default shell `gz` unavailable | Source existing `scripts/environment.sh`; no install |
| Sandbox local transport socket failure | Reported Socket creation failed / invalid 127.0.0.1 / Node range exception; escalated authorized local Gazebo runs worked. Not a generator logic failure; original exploratory console, summarized in PHASE0.md |
| Light request missing entity ID | Initial Light.id default zero led to entity-0 visualization warnings. Final request includes actual sun ID from pose/info. `lighting_changes.json/log` proves RGB changes. Entity-0 visualization warnings still appear; do not claim all warnings vanished or a fully proved internal cause |
| Synchronous set_pose_vector failure | `capture_attempt_fast.log`, `fast2.log`, `rtf8.log`, `shared_client.log`, `fast_gazebo.log`: intermittent service failure/transport_ok=False after several scenes. Observed also at RTF 1; separate request process resolved empirically |
| Private-worker verification | `capture_worker.log` contains successful repeated 20-scene capture; accepted Phase-0/smoke/repeat runs also demonstrate reliability |
| Generated protobuf registration error | Exploratory Scene/Pose import combination reported No message class registered for gz.msgs.Pose. Large exploratory console was not preserved in full; PHASE0.md records the lesson. Production capture uses Pose_V/CameraInfo and excludes that Scene import path |
| Early shadow-wall placement could intersect targets | Changed to 8-m wall and conservative all-target clearance before final Phase-0/smoke data; accepted evidence uses corrected assets. Exact pre-fix exploratory data was not retained as an accepted dataset |
| Smoke histogram JSON mismatch | Initial validator failed after 200 valid captures because integer Counter keys became strings on JSON write. Fixed storage/test; initial FAIL retained and smoke later PASS |
| First repeat summary one-ULP mismatch | Stored/recomputed mean order differed by ~1e-16. Sorted numerical values before reductions; added order-independence regression. Failed evidence retained; both new repeats individually PASS |
| Current determinism exact metadata failure | 23/50 metadata comparisons reject equivalent quaternion signs/rounding. Preserved FAIL and diagnostics; production comparator repair **pending** |
| Lighting probe JSON aliasing | `lighting_probe.py` appended the mutable scene lighting dictionary without copying it. All saved requested_light fields in lighting_changes.json therefore show the final shadow settings. The per-iteration console log and different RGB means retain evidence of color/intensity changes; do not use that JSON field as four independent parameter snapshots. This historical evidence bug is documented, not silently rewritten |
| Git commit author unavailable | Command-scoped Codex author identity, no user/global config mutation |

Gazebo logs also contain EGL/Ogre warnings despite working headless RGB on the
observed GPU. Evidence of output and labels supports the tested behavior;
warnings are not suppressed or represented as absent.

## 13. Phase-0 measured results and qualifications

Alignment: **21 actual controlled renders**: centered, near, far,
edge/truncation and partial occlusion for each of four classes, plus one
all-four-class scene. All programmatic case statuses PASS, matching timestamps
delta 0. Visual contact sheet and full-resolution centered_person,
partial_occlusion_person and edge_bus examples were inspected. Centered IoUs:
person .902597, car .989347, truck .972608, bus .988128; partial-occlusion IoUs
are lower as expected for visible vs full geometry (.729495 person, .814286 car,
.765209 truck, .775085 bus). This proves tested cases, not every future scene.

Pixel feasibility: **448 cells**, four classes x seven altitudes
(10/13/15/18/20/30/40) x four angles x four distance bands. Each cell samples
eight footprint directions/four target yaws and reports min/mean width/height/
area. **50 cells** include a side below 3 px. These are geometric estimates,
not detector results. Decision: retain difficult factor levels, normal placements
must fit, explicit edge truncation allowed, native tiny boxes accounted in
ignored metadata. No required altitude/angle was silently removed.

Final retained representative benchmark (`phase0/benchmark.json`):

| Metric | Actual measurement |
| --- | --- |
| Accepted / attempted | 60 / 60 |
| Elapsed | 8.640455194 s |
| Accepted and attempted throughput | 416.644715952 frames/min |
| Average PNG size | 200,392.633333 bytes |
| RGB image write rate | 1,391,542.196567 bytes/s |
| Gazebo sampled RSS | 911,120–911,252 KiB |
| Gazebo sampled lifetime CPU | 125–177% |
| 10,000 RGB extrapolation | 2,003,926,333 bytes, about 2.00 GB decimal |
| 10,000 time extrapolation | 1,440.075866 s, about 24.0 minutes |

Single renderer, 640x480/10Hz aligned sensors, shadows, representative clutter,
1–8 targets, requested finite RTF 8. CPU is sampled process lifetime percentage,
not total host load. Benchmark excludes full dataset bookkeeping/QA overhead.
An earlier measurement was ~443 frames/min/~23 minutes; **the final retained
416.645 result is authoritative**. Smoke end-to-end throughput was
**320.182277 frames/min**, elapsed 37.478652 s, Python CPU 10.580502 s,
peak Python RSS 190,680 KiB. Pilot must replace planning extrapolations with
measured total cost before full generation.

Phase-0 report's generator_git_commit is the baseline tag because new tool
source was uncommitted when it ran; that source was committed in e323ebe.
Do not claim v0.4-final itself contains the generator. The asset and camera
hashes pin the measured proof; accepted source/runtime evidence is retained.

## 14. Smoke dataset details, fixes and visual QA

Requested/accepted/attempted **200/200/200**, no rejected captures. Splits
**160 train / 20 val / 20 test**. Images, label files, per-frame metadata,
JSONL records, scenario rows and completion markers each count **200**.
No duplicate frame IDs/images/scene-family leakage; 200 unique RGB hashes.
All required factors/classes and all configured held-out assets appear.
Current validator **PASSED**, errors empty; person holdout limitation is a warning.

Frame mix: **160 positive, 20 negative, 20 distractor-only**. Targets:
person 149, car 140, truck 174, bus 140 = **603 intended/realized instances**.
Exported: person 146, car 140, truck 174, bus 140 = **600 labels**.
Ignored: two occluded persons and one tiny person. Truncated instances: **148**.
Placement shortfall: **2 target slots**, recorded explicitly. Frame-level factor
quotas are exact: 40 per altitude, 50 per off-nadir/light/background family.

First validator failure was aggregate-only: `Counter(len(r['objects'])...)`
used integer histogram keys in memory, while JSON loaded keys are strings.
Fix: use `Counter(str(len(r['objects']))...)` in storage.statistics. Regression
asserts the statistics JSON roundtrip in `test_manifest_and_dataset_yaml`.
Later fix sorts numerical arrays in `distribution` before all reductions,
eliminating order-sensitive one-ULP means; the new
`test_distribution_order_independence` covers `[1e16,1,1]` versus reverse order.

Smoke capture provenance stays e323ebe with code hash
`a70c16819b3da7c9a698993ab63d3521fafd24e211b7b0eb1025f1ed28fd1a65`.
Only aggregate statistics/manifests were refreshed; .run/manifest separately
record `statistics_generator_commit=947cecb5ccaf607b7466ed8dff29651efe730f9f`.
All original image/label/frame-metadata bytes were preserved. The smoke gate
was revalidated after both fixes and is current PASS.

Visual review completed for **100 representative previews** through all four
25-image review pages, the representative sheet, negative sheet and
50-lowest-IoU sheet. Required factors were represented in the reviewed set;
32 dedicated factor sheets were generated. Inspection of every one of those
32 separate sheets is not individually recorded. Ignored-tiny boxes are amber with an explicit state rather
than misleading green exported-label overlays; primary boxes are green and
secondary geometry is blue in audit views. Individual full-resolution review
of every one of the 50 lowest-IoU smoke PNGs was **not recorded**; the contact
sheet and selected difficult examples were viewed. Pilot Gate 7 requires the
full >=300 audit and adequate individual low-IoU investigation.

Smoke audit: **200 frames / 601 matched instances** (includes the tiny visible
box, excludes two fully occluded boxes); mean IoU .917111556, median
.968757179, p05 .669159471, p25 .905806008, min .097636270. Class medians:
person .917814, car .971885, truck .981793, bus .983803. Median meets .90 goal;
low tail falls below configured .75 investigation level. Lowest cases include
person/moderate occlusion around frame 34, truck edge around 155, and a
person around 139 with requested none (possible inter-object occlusion;
**not conclusively diagnosed**). Do not declare the entire low tail explained.

Accepted distance distribution is biased by placement rejection:
near **153**, medium **198**, far **101**, edge **151** instances.
Edge is about 25% despite a 10% proposal weight; far large buses/trucks are
underrepresented (bus 10, truck 12). At low altitude large objects cannot fit
many normal far placements; the sampler redraws a category on each placement
attempt. All categories remain represented and accurately recorded. Investigate
this in pilot analysis and document any sampling correction/restriction;
do not silently relabel normal far samples as edge or drop difficult factors.
Also assess recorded shortfalls, actual partial shadow coverage and greedy
association in crowded scenes before full acceptance.

## 15. Configuration, seeds and splitting

Authoritative YAML: `tools/synthetic_dataset/configs/synthetic_dataset.yaml`.
Important current settings:

| Parameter | Value |
| --- | --- |
| Full count / seed / output | 10,000 / 12345 / datasets/gazebo_aerial_v1 |
| Class order | person, car, truck, bus |
| AGL / jitter | 10,15,20,30,40 m / +/-1 m |
| Off-nadir / jitter | 0,10,20,30 deg / +/-2 deg; zero clamp |
| Camera / object yaw | Continuous [0,360) degrees |
| Roll | 0 |
| Frame fractions | .10 pure negative, .10 distractor-only, .80 positive |
| Positive target count weights, counts 1–8 | [2,3,3,3,2,2,1,1] |
| Near/medium/far/edge | [0,.35] / [.35,.70] / [.70,.90] / [.90,1.0] of directional usable footprint |
| Proposed distance weights | .3 / .3 / .3 / .1; accepted distribution differs |
| Target spacing / placement attempts | Conservative footprints plus .5 m / 300 |
| Proposed occlusion none/mild/moderate | .75 / .15 / .10; not exact accepted quotas |
| Distractor count | 2–6 |
| Backgrounds | grass, dirt, road, mixed; four texture variants each |
| Ground / surface size / zone spacing | 0 m / 240 m / 500 m |
| Pool / staging | Three copies per target variant / X=-1000, Z=-50 |
| Render engine / timestep / requested RTF | Ogre2 / .01 s / 8 |
| Settle / synchronization | Three sensor frames / .001 s |
| Pose / orientation tolerance | .001 m / 1e-5, sign invariant |
| Timeout / retries | 40 s / three |
| Native min side / area / association IoU | 3 px / 9 px² / .01 |
| Visibility threshold / fraction | Null, not measured |
| QA | 100 previews / 300 audit frames / 50 lowest-IoU frames |
| IoU goal / tail investigation | Median .90 / low percentile .75 |

Directional light families change real direction/intensity/color, with shadows
enabled and constant ambient `[.35,.35,.35,1]`:

| Family | Elevation deg | Azimuth deg | Intensity | RGB |
| --- | --- | --- | --- | --- |
| morning | 10–30 | 20–160 | .8–1.1 | [1,.88,.7] |
| noon | 60–85 | 0–360 | 1–1.3 | [1,1,.96] |
| evening | 3–15 | 200–340 | .65–.95 | [1,.65,.4] |
| shadow | 25–55 | 0–360 | .85–1.1 | [.95,.97,1] |

Shadow scenes try to place an 8-m wall up-sun with all-target clearance; some
may fall back to other clutter shadows when a wall cannot safely be placed.
Material pattern selection is randomized; current texture rotation/scale/offset
fields are **fixed 0/1/[0,0]**, not active randomization. Mixed textures provide
two surfaces and varying road strips. No augmentation/noise/exposure is applied.

Split schedule: exact 80/10/10 seeded assignment by unique scene seed family,
factor quotas balanced **within each split**. Each sample is a fresh still
scene rather than adjacent video frames. Counts/config affect quota schedules
and are part of resume identity; a 200 run cannot be extended to 2,000 with
--resume. Test-only assets are enforced as section 9 describes.

Actual smoke seed **12345**; repeat a2/b2 seed **12346**, count 50. Crash harness
default seed **76543**, count 200, unused so far. Pilot/full planned seed 12345
unless an evidence-backed change is documented. All samples have their own
recorded SHA-derived scene seed and scenario digest.

## 16. Test and static status

| Check | Status / evidence |
| --- | --- |
| V0.4 baseline prerequisites/build/tests | PASS, nine packages, 56 entries, zero errors/failures/skips; baseline*.json/log |
| Baseline static/launch check | PASS, 67 Python/23 XML/14 YAML/24 shell, 11 launch descriptions; baseline_static.json |
| Synthetic unittest suite | **30 tests PASS**, 2.262 s, evidence/unit_tests.log |
| Synthetic current source parsing at handoff | PASS, 17 Python, 25 SDF, three YAML; handoff_static.json |
| Smoke full standalone validator | PASS, all 200 samples, evidence/smoke_validation.json and gate |
| Both new repeat standalone validators | PASS, all 50 each; determinism_a2_validation.json and b2 |
| Raw exact repeat comparator | **FAIL**, metadata precision/sign issue; determinism.json |
| Live crash/resume | NOT TESTED |
| Final V0.4 regression after implementation | NOT RUN |

Unit command already run:

```bash
python3 -m unittest discover -s tools/synthetic_dataset/tests -v
```

Coverage includes class ordering/separate simulator labels, YOLO conversion,
clips/invalid boxes/edge positive dimensions, split/family/holdout policy,
seed reproduction/changed seed, factor quotas/yaw/off-nadir/ground footprint,
projection axes/upward rays, spacing/grounding, negatives/distractors,
finite metadata/IoU/dimensions, atomic completion/corrupt-frame detection,
data.yaml/manifests/statistics JSON, numerical traversal order, ignored-target
accounting, validator missing files/duplicate images/orphans. These are meaningful
unit/corruption checks; they do **not** prove live hard-kill recovery. No
regression tests for the pending comparator repair exist yet.

Handoff parse checks do not count as the complete Gate-10 regression. No ROS
runtime source changed, but the master still requires the full final suite.

## 17. Next steps in exact order

1. Read this handoff, preserved master prompt and actual status/HEAD/tag. Preserve
   the uncommitted documentation/evidence. Check whether anything changed since
   this snapshot. Gate 3 is already complete; only revalidate it if new changes
   or evidence concerns justify doing so.
2. **Finish Gate 4**: inspect current comparator/diagnostic; repair narrowly scoped
   realized-state sign/tolerance comparisons; add tests rejecting meaningful
   perturbations; run affected unit tests; compare existing a2/b2. Preserve
   failed report, write honest final comparison evidence, update docs and commit.
3. **Gate 5**: execute the real crash/resume harness in a new output using the
   exact same source/config/HEAD through both halves. Require final count 200,
   original completed markers unchanged, matching files/metadata/manifests,
   no duplicates/corruption/tmp files. Inspect owned process cleanup/logs.
4. **Gate 6**: after both preceding gates pass, generate approximately 2,000
   pilot frames. Fully validate; produce previews/statistics/audit outputs;
   review >=100 representatives and factors, balance, sizes, clipping, shortfalls,
   occlusion, shadows, holdouts, disk usage and actual throughput. Investigate
   distance acceptance bias and same-class associations. Make only justified
   corrections with appropriate earlier-proof/regression updates, preserving
   old evidence. Record the pilot gate from actual accepted/reviewed data.
5. **Gate 7**: independently cross-check >=300 representative pilot frames and
   analyze mean/median/p05/p25 by class/altitude/angle, plus at least 50 lowest-IoU
   frames. Distinguish legitimate visible/full occlusion/quantization differences
   from annotation/association bugs. Do not waive a poor tail by quoting median.
   Consider fresh secondary re-projection rather than only stored-box IoU.
   Record actual investigation and audit gate.
6. Use Phase-0 + pilot evidence to confirm 10,000 or explicitly propose/document
   a revised final count/cost. Current default stays 10,000. Gate recorder
   presently hardcodes a 10,000 full minimum; a justified revision would also
   need coherent policy changes, not just --count.
7. **Gate 8**: generate the accepted full target, default 8,000/1,000/1,000 split,
   in `datasets/gazebo_aerial_v1`; preserve crash-safe generation/provenance.
8. **Gate 9**: full validator and visual/annotation QA must prove matching counts,
   valid YOLO coordinates, no corruption/scene leakage/holdout leakage, complete
   representation. Inspect/review before recording the full gate.
9. **Gate 10**: rerun complete existing prerequisites/build/tests/static/launch
   regression. Preserve final evidence and keep all nine packages/contracts.
10. Create `docs/dataset/DATASET_REPORT.md` with actual commands, metrics,
    distributions, QA, crash/determinism evidence, licenses and limitations;
    update tooling docs/checkpoints and report milestone status honestly. Stop
    before training/VisDrone/PX4/runtime integration.

Commands for subsequent stages (templates; **not executed yet**):

```bash
# Only AFTER Gate 4 acceptance, with no code/config/HEAD changes mid-test:
python3 tools/synthetic_dataset/scripts/crash_resume_test.py \
  --output datasets/crash_resume_gate --report docs/dataset/evidence/crash_resume.json

# Only AFTER real crash/resume acceptance:
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --config tools/synthetic_dataset/configs/synthetic_dataset.yaml \
  --count 2000 --seed 12345 --output datasets/gazebo_aerial_pilot --headless
python3 tools/synthetic_dataset/scripts/validate_dataset.py datasets/gazebo_aerial_pilot
python3 tools/synthetic_dataset/scripts/preview_dataset.py datasets/gazebo_aerial_pilot \
  --count 100 --audit-count 300
# Actually inspect QA, then use record_gate.py pilot and audit with findings.

# Only AFTER pilot/audit and final-count decision:
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --config tools/synthetic_dataset/configs/synthetic_dataset.yaml \
  --count 10000 --seed 12345 --output datasets/gazebo_aerial_v1 --headless
python3 tools/synthetic_dataset/scripts/validate_dataset.py datasets/gazebo_aerial_v1
python3 tools/synthetic_dataset/scripts/preview_dataset.py datasets/gazebo_aerial_v1 \
  --count 100 --audit-count 300

# Final existing regression, retaining logs/evidence:
scripts/check_prereqs.sh
scripts/build_ros.sh
source scripts/environment.sh
export ROS_LOG_DIR=/tmp/wildlife-v05-regression-logs
colcon test --base-paths src --executor sequential
colcon test-result --verbose
# Also run the applicable full tracked-source static/launch checks.
```

## 18. Do not redo these items without a reason

- Do not create a copied V0.5 folder, rename this folder, create another repo,
  reset the branch, move the frozen tag or replace the baseline with an old copy.
- Do not redo source inspection/baseline/Phase-0/native-capability probes/21
  controlled cases because conversation context changed. Evidence is retained.
  Rerun only if geometry/camera/environment changes invalidate it or a real
  verification concern is identified.
- Do not regenerate assets or download models merely to restore context;
  pinned manifest hashes/assets already exist and regular generation is offline.
- Do not recollect smoke frames to fix aggregate or comparator metadata.
  Smoke is PASS and its captures are valid/preserved.
- Do not rerender the two current repeat runs to fix the comparator. Use a2/b2.
- Do not return to shared-process blocking RPCs or assume RTF alone caused the
  historical transport problem. The private worker solved observed failures.
- Do not add PX4, QGC, a ROS mission graph, ML framework, detector-generated
  labels, tenth package, training or VisDrone work.
- Do not count the 200-frame smoke audit as the >=300-frame pilot audit or
  claim crash safety based only on storage unit tests.
- Do not delete failed evidence or bulk local captures. Preserve their
  provenance; separate historical failures from current accepted outputs.
- Do not treat the old PHASE0 next-gate prose or README example --resume
  as permission to resume an old capture with a different HEAD/code identity.

## 19. Bugs, expected limitations and pending decisions

### Actual unresolved bug

`check_determinism.py` requires exact uncanonicalized simulator quaternion signs
and binary floats in realized metadata. It therefore falsely fails physically
equivalent readback on otherwise exact scene/RGB/YOLO repeats. Repair and test
the comparison policy before Gate 4 PASS. The diagnostic does not fix it.

Historical lighting-probe evidence also has a metadata aliasing bug: all
`lighting_changes.json` requested_light dictionaries show the final loop values.
`lighting_probe.py` and `lighting_changes.log` preserve the exact probe and
per-iteration commands. It kept sun direction fixed and changed family color/
intensity, so it demonstrates those photometric changes, not independent
elevation/azimuth readback. Production scenes record their sampled lighting
parameters; this aliasing is in the separate exploratory probe's accumulated
report. Preserve the old evidence and correct its interpretation; if stronger
lighting proof is needed later, save copied snapshots without repeating unrelated
Phase-0 work.

### Fixed bugs; do not reopen without evidence

Numeric histogram integer-to-JSON-string key mismatch, numerical reduction
traversal-order roundoff, ignored-tiny previews styled as exported labels,
early shadow-wall clearance and production request/subscriber service failure
workaround. Failures and corresponding accepted evidence remain recorded.

### Expected or documented limitations

- Low-detail original procedural imagery and shared person template limit
  diversity; no independent person-model holdout or real-world accuracy claim.
- Visible native boxes and full geometric projection differ under occlusion,
  truncation and raster quantization. IoU is not pixel visibility.
- Native class-only labels require geometric same-class association; severe
  occlusion/crowding merits actual manual audit. Current greedy matching does
  not prove all ambiguity is detected.
- Placement acceptance changes proposed distance probabilities and records
  two smoke target-slot shortfalls. Factor presence alone does not establish
  ideal object-level balance.
- Requested occlusion mode is not a measured visible fraction; other targets
  may occlude a requested-none target. Actual deliberate partial shadow coverage
  requires pilot analysis, particularly wall-placement fallback cases.
- Texture transforms are recorded constants; only family/variant selection is
  implemented. No animation, dynamic-contact or sensor-noise randomization.
- Headless throughput depends on this GPU/driver/environment; short benchmark
  extrapolation is not full-run timing/storage measurement.
- Resume intentionally requires exact config/count/seed/assets, tool-script
  hash **and Git HEAD**. Even a docs-only commit changes HEAD and blocks an old
  run's --resume. Do not change source/config/HEAD during the crash harness.
  Existing completed smoke/repeats need validation/comparison, not resume.
- Capture source hashes remain their real historical values. Phase-0 ran
  before first tool commit; smoke aggregates record the later summary commit
  separately. Do not rewrite provenance to imply new code rendered old images.
- Gate CLI guards do not enforce every gate/verify all reviewed evidence against
  changed code; follow ordered manual acceptance, inspect staleness explicitly.
- Some renderer/entity-0 visualization warnings remain, despite validated
  output and empirical lighting changes. Internal transport warning/root causes
  are not fully proved.

### Decisions pending evidence

Narrow comparator tolerances and exactness contract; stronger fresh-projection
audit; pilot sampling refinements for large-object distance/edge bias; sufficient
shadow/occlusion quality/diversity; acceptability of procedural asset fidelity;
final dataset count from measured pilot cost/quality. Do not silently adjust
the master scope, difficult factor levels or acceptance rules.

## 20. Exact first continuation commands

```bash
cd "/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3"
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse 'v0.4-final^{commit}'
cat docs/dataset/V0_5_B1_HANDOFF.md
cat docs/dataset/evidence/determinism.json
cat docs/dataset/evidence/determinism_diagnostic.json
source scripts/environment.sh
sed -n '1,220p' tools/synthetic_dataset/scripts/check_determinism.py
```

Expected branch/HEAD/tag are section 1. If different, inspect changes and retain
all authorized work. Do **not** switch back to the frozen tag or start a new
branch. Then implement/test the Gate-4 comparator repair. The appropriate
post-repair comparison command, using existing captures, is:

```bash
python3 -m unittest discover -s tools/synthetic_dataset/tests -v
python3 tools/synthetic_dataset/scripts/check_determinism.py \
  datasets/determinism_a2 datasets/determinism_b2 \
  --report docs/dataset/evidence/determinism.json
```

The current unmodified comparator is expected to fail; merely rerunning it
does not complete Gate 4. Historical exact FAIL is already preserved in
`determinism_attempt2_exact_comparison.json`.

## COPY THIS INTO THE NEW CHAT

Continue V0.5-B1 Synthetic Gazebo Aerial Detection Dataset Generator in the
existing primary workspace `/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3`.
Read `docs/dataset/V0_5_B1_HANDOFF.md` and `V0_5_B1_MASTER_PROMPT.md` first.
Branch `codex/v0.5-synthetic-dataset`, HEAD
`947cecb5ccaf607b7466ed8dff29651efe730f9f`; frozen v0.4-final remains
`949baba06fea505147b5a1cff11a53bb523827a4`. Four implementation commits exist;
handoff/current diagnostics/docs/evidence are intentionally uncommitted and
must be preserved. No copied folder, worktree, rename or runtime ROS source
change. Do not reset/rebranch or repeat passed gates just to restore context.

Gates 0–3 PASS: nine-package V0.4 baseline/56 entries, Phase-0 installed native
sensors/headless proof, 21 controlled alignment cases, 200-frame smoke validator
and actual 100-preview visual QA covering the factors. Smoke is `datasets/gazebo_aerial_smoke`,
160/20/20 splits, 600 labels/603 target instances, two ignored occluded and one
tiny. JSON histogram key and one-ULP statistics-order bugs were fixed with
regressions; 30 synthetic unit tests pass. No owned capture process remains.

Stopped during Gate 4, PARTIALLY VALIDATED. Existing independent runs
`datasets/determinism_a2` and `datasets/determinism_b2` contain 50 frames each,
same seed 12346/config/assets/HEAD; both standalone validators PASS. RGB, YOLO
and scenario CSV bytes match exactly. `check_determinism.py` still FAILs 23 raw
metadata records because realized quaternions can be q or -q and Gazebo floats
differ by roundoff. Diagnostic finds only actual-position/quaternion/secondary
projection/IoU differences, max ~1.82e-12 m / 3.33e-16 / 4.17e-11 px / 3.31e-12,
no structural/non-numeric changes. Preserve original FAIL; repair narrowly scoped
sign-invariant realized-state comparison with justified tolerances and tests
rejecting meaningful changes. Keep commanded scenes/IDs/native labels/boxes/
YOLO/scenario manifests exact. Recompare EXISTING captures; do not rerender them.

Actual tool is under `tools/synthetic_dataset`, no tenth ROS package. Native
visible 2D boxes are primary; actual-pose primitive projection is secondary QA.
Private persistent service worker avoids observed request/subscriber blocking.
Pose readback, >=0.3-s simulation settling and <=.001-s RGB/box timestamps are
enforced. Fixed repository camera: 640x480/10Hz, hFOV1.74, clips .1–100m,
fx/fy~269.968, altitude10/15/20/30/40 +/-1m, off-nadir0/10/20/30 +/-2deg.
Installed sim8.15/sensors8.2.2/rendering8.2.3/transport13.6/msgs10.4; source
environment before Gazebo, restricted Codex needs local socket/render escalation.
No installs. Forty original CC0 procedural assets: 4 persons,4 cars,4 trucks,
3 buses,16 textures,9 clutter. Person template shares geometry, no independent
person holdout; car_3/truck_3/bus_2 and texture index3 are test-only.

After Gate4: real Gate5 SIGKILL/resume harness (new output, stable source/config/
HEAD), Gate6 2,000 pilot, Gate7 >=300-frame independent audit +50 low-IoU
investigations, documented final-count decision, Gate8 default10,000 full
(8,000/1,000/1,000), Gate9 full validator/QA, Gate10 complete V0.4 regression,
then actual DATASET_REPORT.md. Gates5–10 unrun; no pilot/full exists. Inspect
pilot distance acceptance bias (smoke edge25% vs proposal10%, large far objects
underrepresented), low IoU tail/shadows/association, and stored-secondary-audit
limitations. No training, VisDrone download/training, PX4 capture, ROS YOLO,
mission/tracker changes or sim-to-real claims. Tag stays unchanged; bulk
datasets stay ignored; preserve all failed evidence. First commands: cd exact
workspace, git status/branch/rev-parse HEAD and v0.4-final, read handoff and
determinism diagnostic, source scripts/environment.sh, inspect comparator.
