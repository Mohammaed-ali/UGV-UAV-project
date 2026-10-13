# Offline synthetic aerial detection dataset

V0.5-B1 development tooling in the existing primary repository, based on the
unchanged `v0.4-final` release. No tenth ROS package, mission change, PX4 flight,
QGC, ROS graph, YOLO installation or training is required.

```bash
cd "/home/mohammed-ali/Downloads/gpt /wildlife_ws_ros2_jazzy_v0_3"
source scripts/environment.sh
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --config tools/synthetic_dataset/configs/synthetic_dataset.yaml \
  --count 200 --seed 12345 --output datasets/gazebo_aerial_smoke --headless
python3 tools/synthetic_dataset/scripts/validate_dataset.py datasets/gazebo_aerial_smoke
python3 tools/synthetic_dataset/scripts/preview_dataset.py datasets/gazebo_aerial_smoke
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
and settling. Independent projection of primitive geometry provides QA boxes.
Visible boxes and full projected silhouettes have different occlusion semantics.
No unvalidated pixel visibility fraction or photometric realism is claimed.

Train/val/test are 80/10/10 by independently seeded scene families. Frame factors
are quota-balanced within each split; count changes intentionally change the
quota schedule, so count is part of resume identity. Each accepted sample is one
intentional still scene. Distance is a fraction of the usable ground footprint
around the optical-axis ground intersection, with a separate edge challenge.
Targets have conservative footprint separation. Source assets are original
low-detail CC0 geometry/textures; person variants share a template and therefore
have no independent heldout person-model claim. Test-only vehicle geometry and
texture variants are enforced by the asset manifest.

Generation commits image, label and per-frame JSON atomically, then writes a
hash-bearing completion marker last. Split JSONL/manifests are rebuilt from
committed records, never appended. Interrupted/corrupt samples are regenerated;
valid completed samples are skipped. Resume requires the original config,
count, seed, asset checksums, generator code and Git revision:

```bash
python3 tools/synthetic_dataset/scripts/generate_dataset.py \
  --count 200 --seed 12345 --output datasets/gazebo_aerial_smoke --headless --resume
```

An output lock prevents two writers. Process partitions are unique and only
owned Gazebo/service processes are stopped. Diagnostic runtime worlds/logs
remain under each dataset's `runtime/`. Do not run another generation process
against the same output. The generator cannot extend an existing run's count.

The exporter creates `images/{train,val,test}`, corresponding `labels`, per-frame
JSON plus `metadata/{train,val,test}.jsonl`, asset/scenario/config/hash manifests,
`data.yaml`, `manifest.json`, `statistics.json` and README. Empty negative labels
are valid; zero-byte images or metadata are rejected. Every target has a label
state and ignored reason, even if tiny, outside or occluded. Bulk `datasets/`
is ignored by Git. `qa/` holds previews, factor contact sheets and low-IoU evidence.

The CLI refuses dataset generation without recorded Phase-0/alignment evidence;
counts over 200 require smoke acceptance, and counts over 2,000 require pilot
and 300-frame audit acceptance. Gate records require actual validators and a
visual review note. Follow these stages in order:

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

`build_assets.py` regenerates original pinned geometry/materials; it is a
development action, not part of ordinary generation. Changes invalidate
feasibility/resume identity. Asset licensing/provenance is under `assets/manifests/`
and `assets/LICENSE`. The VisDrone map is preparation only, with unsupported
categories explicitly unresolved.

## Continuation checkpoint

Gates 0–3 passed, including the 200-frame smoke dataset and its visual QA.
Gate 4 remains partially validated: two independent 50-frame runs have
identical RGB, YOLO and scenario-manifest bytes, while the current comparator
incorrectly requires exact raw simulator quaternion signs and float values.
Read [V0_5_B1_HANDOFF.md](../../docs/dataset/V0_5_B1_HANDOFF.md) before continuing.
Reuse the existing captures to repair and test that comparison. No crash/resume,
2,000-frame pilot, 300-frame pilot audit or 10,000-frame full run has started.

Synthetic Gazebo imagery is not equivalent to real aerial-camera imagery.
This pipeline validates simulator annotation/export and reproducible sampling;
it establishes no detector accuracy or sim-to-real success. See
[Phase 0](../../docs/dataset/PHASE0.md) and the continuation handoff for current
gate evidence and limitations. `docs/dataset/DATASET_REPORT.md` is a pending
final deliverable; it must describe actual pilot/full results after those gates.
