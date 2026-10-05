# Offline synthetic aerial detection dataset

V0.5-B1 development tooling in the existing primary repository, based on the
unchanged `v0.4-final` release. No tenth ROS package, mission change, PX4 flight,
QGC, ROS graph, YOLO installation or training is required.

```bash
cd "/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3"
source scripts/environment.sh
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --config tools/synthetic_dataset/configs/synthetic_dataset.yaml \
  --count 200 --seed 12345 --output datasets/my_new_smoke --headless
python3 tools/synthetic_dataset/scripts/validate_dataset.py datasets/my_new_smoke
python3 tools/synthetic_dataset/scripts/preview_dataset.py datasets/my_new_smoke
```

The validated dependencies already come from the project/Jazzy environment:
Python stdlib, numpy, OpenCV, PyYAML, Gazebo Harmonic 8 and its transport13/msgs10
bindings. No package installation is performed. A GPU/EGL-capable host is needed
for the observed throughput; in restricted Codex execution, local transport/
rendering requires sandbox escalation. Ordinary terminal use requires no desktop UI.

Classes are exactly **0 person, 1 car, 2 truck, 3 bus**. The separate simulator
namespace is defined only in `configs/class_mapping.yaml`. The primary YAML
controls scene factors, counts, split quotas, lighting, backgrounds, asset
manifest, thresholds, settling and synchronization. Camera intrinsics are read
from the current unmodified V0.4 camera SDF and verified against live CameraInfo.
The dataset does not randomize them. No detector supplies training labels.

The world preloads pinned target variants, texture zones and distractors;
`set_pose_vector` changes active models and an aerial sensor rig. `light_config`
changes actual directional light parameters. A private service worker avoids
the observed blocking-request/subscriber issue in the installed bindings.
RGB/native visible 2D boxes are paired by timestamp after actual pose readback
and settling. Independent projection of rendered mesh hull/primitive geometry provides QA boxes.
Visible boxes and full projected silhouettes have different occlusion semantics.
No unvalidated pixel visibility fraction or photometric realism is claimed.

Train/val/test are 80/10/10 by independently seeded scene families. Frame factors
are quota-balanced within each split and scene composition; count changes intentionally change the
quota schedule, so count is part of resume identity. Each accepted sample is one
intentional still scene. Distance is a fraction of the usable ground footprint
around the optical-axis ground intersection, with a separate edge challenge.
Targets have conservative footprint separation. TRAIN requests 60% human-positive,
20% vehicle-only, 10% distractor-only and 10% empty frames; val/test request 30/50/10/10.
Within TRAIN human scenes, 45% request one person and 55% groups, with configurable
2–3/4–6/7–10/11+ bands. Acceptance uses exported visible boxes with a five
percentage-point absolute tolerance. Person-instance distance quotas persist across placement retries.
Source assets are checksummed CC0 clothed MakeHuman derivatives, Kenney vehicle
meshes, original buses/context and photographic Poly Haven PBR terrain. Person
variants share hm08, so no independent heldout person-model claim is made.
Test-only vehicle geometry and photographic source textures are enforced by the
manifest. See [asset provenance](../../docs/dataset/ASSETS_V2.md).

Generation commits image, label and per-frame JSON atomically, then writes a
hash-bearing completion marker last. Split JSONL/manifests are rebuilt from
committed records, never appended. Interrupted/corrupt samples are regenerated;
valid completed samples are skipped. Resume requires the original config,
count, seed, asset checksums, generator code and Git revision:

```bash
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --count 200 --seed 12345 --output datasets/my_new_smoke --headless --resume
```

An output lock prevents two writers. Process partitions are unique and only
owned Gazebo/service processes are stopped. Diagnostic runtime worlds/logs
remain under each dataset's `runtime/`. Do not run another generation process
against the same output. The generator cannot extend an existing run's count.

The exporter creates `images/{train,val,test}`, corresponding `labels`, per-frame
JSON plus `metadata/{train,val,test}.jsonl`, asset/scenario/config/hash manifests,
`data.yaml`, `manifest.json`, `statistics.json`, `human_statistics.json` and README.
Human test subsets are overlapping file lists with no copied images. Empty negative labels
are valid; zero-byte images or metadata are rejected. Every target has a label
state and ignored reason, even if tiny, outside or occluded. Bulk `datasets/`
is ignored by Git. `qa/` holds previews, factor contact sheets and low-IoU evidence.

The CLI refuses dataset generation without recorded Phase-0/alignment evidence;
counts over 200 require smoke acceptance, and counts over 2,000 require pilot
and 300-frame audit acceptance. Gate records require actual validators and a
visual review note and explicit realism criteria; audit/full require 50 documented
low-IoU investigations. Gate hashes bind the reviewed config/assets. Follow these stages in order:

1. `scripts/phase0.py`: reproduce controlled alignment, pixel table and benchmark;
   inspect the contact sheet and full-resolution cases before `record_gate.py feasibility`.
2. Generate/validate/preview 200 smoke frames; inspect at least 100 previews and
   all factor sheets before `record_gate.py smoke`.
3. Generate a small scene sequence twice; `check_determinism.py RUN_A RUN_B --report REPORT`
   compares scene, realized pose, labels and metadata, reporting RGB hashes separately.
4. `crash_resume_test.py --output DATASET --report REPORT` SIGKILLs the generator after
   30 committed samples, cleans only its owned simulator, then resumes and validates 200.
5. Generate/validate/preview 2,000 pilot frames. Review factor balance, storage,
   annotation audit and 50 lowest-IoU cases; record `pilot` and `audit` gates.
6. Generate the default 10,000 frames to `datasets/gazebo_aerial_v1`, validate,
   preview and record `full`. Stop before any training or VisDrone work.

`record_gate.py GATE EVIDENCE --visual-review-note 'specific inspection findings'`
records a review; it is not a substitute for looking at the images. Timing/UTC
fields vary between runs and are excluded from determinism comparison. Scene
specifications, realized pose, annotations and scenario manifests must match.
Rendered RGB determinism is measured rather than assumed.

```bash
python3 -m unittest discover -s tools/synthetic_dataset/tests -v
scripts/check_prereqs.sh
scripts/build_ros.sh
source scripts/environment.sh
colcon test --base-paths src --executor sequential
colcon test-result --verbose
```

`prepare_realism_assets.py` rebuilds upgraded assets offline from retained
licensed inputs (scipy is needed only for asset preparation). `build_assets.py`
is the historical primitive builder and overwrites the primary asset manifest;
it is not part of ordinary generation. Changes invalidate
feasibility/resume identity. Asset licensing/provenance is under `assets/manifests/`
and `assets/LICENSE`. The VisDrone map is preparation only, with unsupported
categories explicitly unresolved.

## Current acceptance checkpoint

The user added human-priority and visual-fidelity requirements after the original
technical pilot. The corrected current 200-frame smoke, 100-frame independent
replays, real SIGKILL/resume test, revised 2,000-frame pilot and 300-frame audit
pass. The pilot's TRAIN visible-human fraction is 59.0625%, with single/crowd,
distance, altitude, viewpoint, terrain, light and appearance coverage. All 50
lowest-IoU frame overlays and enlarged crops were inspected; private unique
native instance labels independently reproduce their primary box association
and YOLO bytes. Production labels remain the four configured class IDs.

The 10,000-frame full dataset passes automated/visual acceptance and the final
V0.4 regression: 8,000 train / 1,000 validation / 1,000 test, 10,000 unique image
hashes, 59.025% of TRAIN images with visible people, 2,123 single-person and
2,599 multi-person TRAIN scenes, and 16,631 total person labels. The full
300-frame projection audit and all 50 low-tail identity investigations pass.
All nine ROS packages build; 56 existing test entries and 59 synthetic tests pass.
No runtime sources or typed contracts changed from `v0.4-final`.

These completed captures pin generator revision **796c48e**. Exact replay/resume
requires that revision and identical count/seed/config/assets, even after a
documentation-only commit. Use a new output directory for a new run.
Earlier failed or insufficient attempts remain retained and explained.
Directory existence does not establish acceptance. Actual status and results are
in the [dataset report](../../docs/dataset/DATASET_REPORT.md) and
[continuation results](../../docs/dataset/CONTINUATION_RESULTS.md).
The [historical handoff](../../docs/dataset/V0_5_B1_HANDOFF.md) remains preserved.

Synthetic Gazebo imagery is not equivalent to real aerial-camera imagery.
This pipeline validates simulator annotation/export and reproducible sampling;
it establishes no detector accuracy or sim-to-real success. See
[Phase 0](../../docs/dataset/PHASE0.md) and the dataset report for actual gate
evidence and limitations, including shared human geometry, simplified assets,
very small aerial people and finite-terrain corners. V0.5-B1 stops at validated
dataset generation; no model training or detector integration was performed.
