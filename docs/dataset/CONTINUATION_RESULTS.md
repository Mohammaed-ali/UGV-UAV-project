# V0.5-B1 continuation results

Continued on 2026-10-05 (Asia/Riyadh) in the same repository and branch,
`codex/v0.5-synthetic-dataset`, from HEAD `947cecb5ccaf607b7466ed8dff29651efe730f9f`.
The frozen `v0.4-final` remains `949baba06fea505147b5a1cff11a53bb523827a4`.
The previous handoff is retained as a historical stopping-point record.

## Gate 4 — PASSED

Inspected actual status/branch/tag, handoff/master prompt, Phase-0/smoke
evidence, configs, generator, validator, storage, comparator and tests.
Gates 0–3 were already complete; no feasibility/smoke/repeat scenes were rerendered.

Problem: exact raw metadata equality rejected 23 of 50 records due to
equivalent quaternion signs and readback roundoff. Minimum change:
`check_determinism.py` now compares realized positions with absolute 1e-10 m,
whole-sign-equivalent unit quaternions with 1e-14 component tolerance,
secondary projection with 1e-8 px and derived IoU with 1e-9.
No relative tolerances are used. These are far below a pixel or the capture
pose tolerance and cover measured maxima 1.82e-12 m, 3.33e-16,
4.18e-11 px, and 3.31e-12 respectively. Commanded poses, IDs, scene factors,
native labels/boxes, YOLO bytes and scenario/config/asset manifests remain exact.
Unexpected schema, type changes and non-finite values fail. Raw records are unchanged.

Added `tests/test_determinism.py`: equivalent signs/roundoff pass; real pose,
orientation, projection, IoU, command, native/YOLO, ID and lighting changes fail.
The first test attempt had three fixture failures because numpy sampler scalars
were compared before JSON serialization. The fixture now uses the actual JSON
contract; the comparator policy was not loosened. Failed output is retained
in `evidence/unit_tests_gate4_attempt1.log`.

Commands:

```bash
python3 -m unittest discover -s tools/synthetic_dataset/tests -v
python3 tools/synthetic_dataset/scripts/check_determinism.py \
  datasets/determinism_a2 datasets/determinism_b2 \
  --report docs/dataset/evidence/determinism.json
```

Result: **40 unit tests PASSED**; existing **50/50 metadata, YOLO and scene
records PASSED** under the explicit equivalence policy; **50/50 RGB bytes exact**.
58 whole-quaternion sign changes were accepted. Evidence: `determinism.json`,
`determinism_compare_final.log`, `unit_tests_gate4.log`. Original comparator
FAIL and diagnostic remain preserved. RGB reproduction is measured only for
these runs in this installed environment, not promised across renderers.

Next: Gate 5 real SIGKILL/resume, with unchanged source/config/HEAD between halves.

## Gate 5 — first attempt FAIL; capture policy corrected

`crash_resume_test.py --output datasets/crash_resume_gate` killed the generator
after 30 committed samples; resume preserved all 30 markers. It stopped at
index 147 after three identical retries of a fully occluded one-person scene.
Final count was 147, with matching indices/no duplicate image hashes, so this
attempt **FAILS** the required 200 count. `crash_resume_attempt1.json/log` and
the original bulk output/logs are retained; all recorded owned processes exited.

A targeted rerender of only seed 76543/index 147 showed the moderate canopy
completely hiding the person from the 9.28 m nadir camera. Zero native visible
boxes were received; the target correctly became `ignored_occluded`. Image,
metadata, script and log are preserved as `crash_rejected_scene.*` and
`inspect_rejected_scene.py`. This necessary diagnostic did not rerun Gate 0/1.

Minimum fix: remove the exception that required every intended positive scene
to have an exported label. The configured ignored-object policy now applies
even when all targets are ignored. Scene `kind=positive` denotes intended
target presence, while empty YOLO labels denote no exportable visible boxes.
No target, difficult factor or scene is dropped; no native annotation changes.
The report must separately count such frames. Three capture-policy tests prove
complete occlusion/tiny targets remain accounted and unexpected native labels
are still rejected. **43 unit tests PASSED** (`unit_tests_gate5.log`).

Next: new live hard-kill/resume run in `datasets/crash_resume_gate_v2`, retaining
seed 76543/count 200 and stable source/config/HEAD throughout both halves.

## Gate 5 — PASSED on second attempt

Ran the same crash harness with output `datasets/crash_resume_gate_v2`, seed
76543/count 200, at unchanged commit `1f10111` and tool/config identity through
kill and resume. SIGKILL after 30 commits, then resume exit 0; all original 30
completion markers unchanged. Validator PASSED: 200 images, labels, frame
JSONs, JSONL records, scenario rows and markers; 200 unique image hashes, no
duplicates/leakage, no remaining temporary files. All owned generator/Gazebo/
service-worker PIDs were absent afterward. Exactly one intended positive frame
(147) has only ignored targets; its occluded person remains accounted.

Evidence: `crash_resume.json`, `crash_resume_gate_v2.log`,
`crash_resume_killed.log`, `crash_resume_resumed.log`,
`crash_resume_processes.json`. Original first-attempt FAIL remains unchanged.

Before pilot, strengthened `preview_dataset.py` to freshly reproject each
audited target from the dataset asset manifest and actual recorded camera/
object pose; verify stored projection agrees within 1e-8 px, then compare
native visible boxes. Added corruption/known-optical-projection tests and
same-class spatial alternative diagnostics. This changes QA only; camera,
assets, sampler and sensor capture/labels are unchanged. **45 unit tests PASS**.
No rerender of accepted smoke or determinism captures was needed.

Next: Gate 6, 2,000 accepted pilot frames, then actual 300-frame/50-lowest audit.

## Gate 6 — first pilot FAIL at 968; association corrected

The first pilot (`datasets/gazebo_aerial_pilot`, seed 12345/count 2,000,
commit `1f9d8fb`) stopped at index 968 after three association rejections.
968 committed images/labels/metadata/markers remain valid; the partial validator
fails only the expected final count. `pilot_attempt1.log` and
`pilot_attempt1_validation.json/log` preserve the failure. It is not a passing pilot.

The targeted diagnostic preserved actual RGB, native candidates, realized
camera/target geometry, timing and association scores (`pilot_rejected_scene.*`,
`inspect_association_scene.py`). All three instances are cars. The canopy leaves
a native **13×7 px** visible rectangle on the first car, correctly within its
97×113 px full projection, giving IoU **0.00827035**. Both other cars match
near 0.99; neither overlaps the sliver. The 0.01 visible/full IoU cutoff rejected
this valid, uniquely located native annotation. Image/annotation timestamps agree.

Minimum fix: keep the existing IoU match, then allow a below-cutoff native box
only when it overlaps **exactly one** same-class full projection and is contained
in that projection within configured **1 px** raster padding. Overlapping
same-class candidates, wrong labels and unexplained boxes still reject. Neither
native boxes nor YOLO geometry are enlarged/changed. Five association regressions
include this exact failure, ambiguous/outside/wrong-class rejection and ordinary
matches. **50 unit tests PASS** (`unit_tests_association_fix.log`).

Because this changes annotation association/config, reconfirm the repaired scene
and current-revision determinism/crash evidence before the new pilot. Camera,
assets, lighting, sampler, ROS packages and feasibility proof remain unchanged.

## Reconfirmed Gates 4–5 at annotation revision `33e41e1` — PASSED

The failed pilot scene was rendered in two independent sessions. All three
native boxes now associate and export unchanged; the correct 13×7 px rectangle
retains IoU 0.00827 rather than being enlarged. RGB bytes match and serialized
metadata compares under the Gate-4 policy. Overlay was inspected. The probe's
first in-memory comparison again hit numpy scalar types; the retained JSON
records were re-compared successfully without rerendering. Original diagnostic
FAIL remains `pilot_association_fix_attempt1.json`, final PASS
`pilot_association_fix.json`; both raw/overlay images and JSONs are preserved.

After the actual association/config change, fresh 50-frame sets
`determinism_a3/b3`, seed 12346, passed both validators and determinism comparison:
50/50 exact RGB/YOLO/scenario files, no metadata errors. Evidence:
`determinism_current.json/log`, `determinism_a3.log`, `determinism_b3.log`.
This repeat was necessary for changed annotation logic, not the earlier comparator repair.

Then `crash_resume_gate_v3`, unchanged revision/config/source through both halves,
was hard-killed at 30 commits and resumed to 200; all 30 markers unchanged,
matching final counts, no duplicates/corruption/tmp files, validator PASS,
owned processes absent. Evidence: `crash_resume_current*.json/log`.
Gate-0/Phase-0 assets/camera/native feasibility were not repeated.

Next: the fresh pilot is `datasets/gazebo_aerial_pilot_v2`, count 2,000/seed 12345.

## Human-priority and visual-fidelity addenda — acceptance changed

Inspected both user attachments and retained their verbatim requirements in HUMAN_SAMPLING_REQUIREMENT.md and HIGHER_REALISM_REQUIREMENT.md. The existing 2,000-frame pilot_v2 technically validates but FAILS the new human quotas: 47.0625% of TRAIN frames contain labelled people, and visible crowd sizes stop at five. No full dataset was approved from that evidence. See pre_addendum_pilot_summary.json and pre_addendum_pilot_analysis.json.

Minimum changes: explicit separate TRAIN/val/test composition quotas, configurable crowd bands and instance-distance schedules; visible-human statistics and overlapping test file lists; checksummed CC0 clothed MakeHuman derivatives, Kenney vehicle meshes, original beveled buses/context and photographic Poly Haven PBR terrain; parsed RGB anti-aliasing; geometry hulls for full-mesh projection; fresh config hashes invalidate stale smoke/pilot/audit gates. All original 40 asset checksums are preserved (legacy_asset_preservation.json). No ROS source changed.

Failed development attempts retained: unit_tests_human_attempt1.log (old overall factor-balance assertion); unit_tests_human.log (heldout vehicle class exceeded three copies); the initial offline sampler probe found an infeasible far vehicle. Updated invariants check balanced factor quotas within each composition; vehicle class allocation respects heldout pool capacity; far vehicles retain their drawn band with clipped geometry rather than redrawing distance. Human placements never silently change band or drop a requested person. unit_tests_human_attempt2.log passes all 57 tests.

Changed-asset alignment: 21 controlled cases PASS, 448 pixel-feasibility cells (26 below threshold), 60-frame benchmark ~113.93 accepted frames/min and ~469.6 KB PNG. Preliminary Gazebo RSS is ~2.2 GB. human_realism_alignment_attempt1 retains the first visual/benchmark attempt; final human_realism_alignment includes improved context. Camera remains source-derived 640x480/10 Hz. Installed SDF schema inspection found anti_aliasing belongs inside camera/image; XML was corrected. The renderer still emits its historical entity-0 visualization warning and a bounding-camera AA warning; image/pose/label checks pass independently. Actual Ogre2 log identifies RTX 4050/NVIDIA GL, despite nvidia-smi failing inside the restricted sandbox.

Status: implementation/controlled alignment PASS; human-realism smoke, current determinism/crash checks, revised pilot and all later gates remain pending.

### Human-realism smoke attempt 1 and mesh correction

The first upgraded 200-frame smoke at 62e4208 passed automated validation and approximate visible quotas (TRAIN 94/160 person frames, 41 single, 53 multi, six ignored persons accounted for). It was **not visually accepted**: signed-volume checks revealed reflected human face winding and inward coach roof/wheel surfaces; the pre-clustering vehicle palette produced 160-216 visual/material meshes per model. qa/realism_review.json records FAIL; original images/metadata/QA remain intact.

Minimum asset fix reverses reflected human and inward coach/wheel triangles, and clusters vehicle face colors into twelve fitted groups (13-14 actual material meshes including semantic rubber/glass groups). Closed coach surfaces now have positive signed volume; draw-call regression coverage added. All 59 unit tests pass in unit_tests_realism_passed.log. Checkpoint 796c48e0622f9ee70efd96e47a79a4075e9a7dbd. No source ROS edits.

Corrected-asset 21-case alignment PASS, benchmark 60 frames at444.06 frames/min and467.48KB average PNG (human_realism_alignment_v2). Identical 40-scene AA probe: RGB AA1=479.92/min, AA4=377.34/min; native box/YOLO bytes EXACT. AA4 retained for smoother image boundaries; fixed camera intrinsics/resolution/rate retained. Cost estimates will use the actual revised pilot, not these short timing probes alone.

Next gate: corrected 200-frame smoke automated/100-preview/human/realism QA, then fresh current-implementation determinism and real crash/resume, then revised 2,000-frame pilot.

### Corrected human smoke Gate 3 PASS; determinism coverage diagnostic

Corrected smoke_v2 at796c48e: 200 accepted, independent CLI validatorPASS, 100 previews across four inspected pages, all eight realism contact sheets and two native high-pixel-size human/mixed samples inspected. Explicit six-criterion qualitative realism review passes as improved **simplified synthetic** imagery, with stylized meshes, planar finite terrain, approximate vegetation/hard shadows and shared human template noted. TRAIN labelled-human93/160=58.125%, single40/multi53, 304 valid person instances and six ignored persons retained. TRAIN has all altitudes, angles, distance/background/lighting levels and eight human variants; mixed46frames includes all vehicle classes. smoke_gate.json now binds the actual config/assets. Throughput including startup/commit overhead ~289.6/min before teardown; final measured performance is in .run.json.

The first current-asset 50-frame determinism replays are EXACT for50 RGB images, YOLO/scenario bytes and allowed metadata comparisons. Both validators flag only heldout mixed_3 missing from their five-frame test split. Their FAIL coverage evidence is retained in human_determinism_a/b.log and dataset qa/validation.json; no corrupted/missing files or scene differences. This is insufficient standalone coverage acceptance, so a100-frame small replay is being used without loosening the validator.

### Current Gate 4 PASS

The100-frame independent replays human_determinism_a100/b100 both pass the standalone validator and match100/100 RGB bytes, YOLO/scenario/config/asset manifest bytes and strict metadata comparisons. human_determinism_100.json records no errors; maxima1.82e-12m position,4.44e-16 quaternion,6.03e-11px secondary projection and1.39e-12IoU. Timing fields are excluded only under strict schema/type checks. No capture edits or rerender solely to relax comparator tolerances occurred. Both current runs use same seed12346/config/assets/revision796c48e. Gate5 real kill/resume now running before pilot.

### Current Gate 5 PASS

Real SIGKILL at30 committed records, followed by original-config/seed/count/assets/code/revision resume to200 accepted. human_crash_resume.json PASS; all original completion-marker hashes preserved; no duplicate/corrupt images, orphaned labels/metadata, count mismatch or remaining temporary files. Independent host process listing confirms all owned simulator/service-worker processes exited (human_crash_resume_processes.json).

Current gates3–5 PASS at796c48e under human/realism addenda; revised2000-frame pilot is running.


### Current Gates 6–7 — PASS, human/fidelity pilot and annotation audit

1. Inspected the completed `gazebo_aerial_human_pilot` (2,000 frames), standalone validation, distribution/asset/resource summaries, 100 overlay previews, all eight dedicated realism sheets, four native samples, and 50 low-tail full-frame/crop pairs.
2. Actual status: validator PASS; TRAIN945/1600=59.0625% visible-human frames,423single/522multi,3000person labels. Person altitude counts620/645/562/603/570 across10/15/20/30/40m; distances902near/911medium/905far/282edge. Crowds1/2–3/4–6/7–10/11+ contribute423/518/915/846/298instances. Largest crowds supply9.93%, isolated people14.1%. All angles/backgrounds/lights/eight shared-template appearances are represented; mixed470humanTRAINframes include all vehicle classes. Val/test each59/200=29.5% human frames. Test has no visible11+ example at this finite pilot size; the TRAINcrowd quotas pass. All7heldoutvehicle/terrainvariants occur only in test.
3. Minimum change: no generator/camera/config/asset changes. Corrected only an obsolete distance explanation in the evidence analysis helper. Added inspectable crop pages, independent native instance-ID replay and finite-ground diagnostic. The incorrect validator `--output` CLI attempt is retained as `human_pilot_validation_attempt1.log`; correct `--report` run passes.
4. Files/evidence: `human_pilot_analysis.json`, `human_pilot_human_statistics.json`, `human_pilot_validation.json`, `human_pilot_realism_review.json`, `human_pilot_annotation_audit.json`, `human_pilot_low_iou_investigations.json`, `human_pilot_instance_identity_audit.json`, `human_pilot_background_extent_review.json`, figures and recorded pilot/audit gates. Dataset captures unchanged.
5. Commands: `generate_dataset.py --count 2000 --seed 12345 --headless --output datasets/gazebo_aerial_human_pilot`; `preview_dataset.py ... --count 100 --audit-count 300`; independent validator `--report`; evidence analyze/instance-replay/low-tail-review/extent helpers; `record_gate.py pilot/audit`.
6. PASS: 300 audit frames,960matched native instances; fresh projection of966objects agrees exactly with stored bounds. Overall IoUmedian.95665,p05.62574,min.03350; person median.91934. All50lowestcases investigated rather than threshold-discarded. Unique per-instance native simulator labels reproduce all50frame associations/visible boxes/YOLO bytes; no swaps or unexplained alignment defect.
7. Performance:397.28s generation,302.05accepted/min;0capture rejections; ~.81GiB simulator RSS, ~190MiB Python peak. ~906MBRGB,1.010GBtotal including QA at analysis time. Synchronization delta0; minimum settling.3s; max realized position error2.04e-12m.
8. Limits: stylized coaches/trees, one human template/static poses, planar finite PBR terrain and hard directional shadows.111/2000frames expose background at high/oblique corners (max5.53%pixels); analytical footprint/far-clip check explains it. Keep difficult levels and document it. Occlusion requests/box IoU are not pixel visibility measurements. Tiny/occluded people stay accounted. No photorealism/sim-to-real claim.
9. Next Gate8: retain10,000 accepted frames, forecast33.1min/~4.53GBRGB/~5.05GBincluding pilot-style QA, comfortably within available33GB. `full_target_decision.json` records the evidence-based decision; full generation follows current committed796c48e code/assets/config unchanged.

## Gates 8–9 — full generation, automated validation and visual QA: PASS

1. **Inspected:** current 2,000-frame human pilot acceptance, full target decision, fixed camera, pinned config/assets/code at `796c48e`, and available disk capacity. The full capture follows the passed revised smoke, determinism, real crash/resume, pilot and annotation gates.
2. **Actual status:** generated 10,000 accepted frames, 8,000 train / 1,000 validation / 1,000 test, seed 12345. The standalone validator and acceptance recorder both pass. All image/label/metadata/JSONL/marker/scenario counts equal 10,000, image hashes are unique, all heldout assets are present in test and absent from train/validation, and no split leakage/corrupt/orphan exports occur.
3. **Minimum change:** no generator, config, camera or asset change during full generation. Recorded the completed manual review and copied small evidence artifacts. Native ground truth and ignored states remain intact.
4. **Files changed:** `DATASET_REPORT.md`, `ASSETS_V2.md`, tooling README and evidence under `docs/dataset/evidence/full_*`; full bulk output remains ignored under `datasets/gazebo_aerial_v1`. Manual `record_full_review.py` stores actual findings; it does not infer visual approval from metrics.
5. **Commands run:** generator `--count 10000 --seed 12345 --headless`; independent validator `--report`; preview `--count 100 --audit-count 300`; actual-pose geometry and private unique-instance audit; background-extent, resource, distribution and table/figure helpers; full gate recorder with explicit visual findings. Exact commands and hashes are in the dataset report/manifests/logs.
6. **PASS:** TRAIN visible-person 4,722/8,000 = 59.025%; single/multi 2,123/2,599; 15,093 TRAIN person boxes. Near/medium/far/edge valid persons 4,540/4,566/4,556/1,431. All altitudes/angles/backgrounds/lights/eight human appearances and mixed vehicle classes are covered. The largest crowds contribute 10.276% of person instances. Test has five visible 11+ crowds. Test human file-list subsets contain all/single/multi/small/far/occluded/shadow examples without copying images.
7. **Evidence:** `full_gate.json`, `full_validation.json`, `full_capture_manifest.json`, full human/statistics/tables/analysis, 100-preview index and copied visual artifacts, six-criterion realism review, 300-frame audit, all 50 low-IoU investigations and independent identity replays. Audit median IoU 0.95760, p05 0.53969, minimum 0.00554; the minimum is a 2×4 px ignored person behind a tree. Labelled-only audit minimum is 0.21099. All 50 identity replays preserve primary boxes and YOLO bytes; fresh geometry has zero stored-box delta.
8. **Warnings/limits:** all 486 ignored targets (279 tiny, 207 occluded) remain accounted for; person ignores are 276 tiny / 189 occluded. No planned people are dropped. Placement constraints leave 354 requested vehicle slots unfilled in 255 frames, explicitly recorded. Simplified/shared human geometry, stylized vehicles/context, hard shadows and planar repeated terrain remain. Fixed clip/finite ground corners affect 643/10,000 frames, maximum 7.045% of pixels. No photorealism or real-world detector claim. Capture is 2,008.20 s / 298.775 accepted per minute, zero capture rejections; 4.527 GB RGB and 4.783 GB total including QA. Python capture peak 192.96 MiB, Gazebo samples ~0.81 GiB; aggregate validation observed 545.0 MiB Python, separate from capture. Owned processes are absent.
9. **Next gate:** final existing V0.4 regression, completed below. Full accepted code/assets/config remain unchanged.

## Gate 10 — final project regression: PASS

1. **Inspected:** frozen release `949baba`, current generator revision `796c48e`, existing prerequisite/build/test scripts, all nine ROS packages, typed interfaces, launch descriptions and synthetic tests.
2. **Actual status:** existing prerequisites pass; nine packages build; colcon reports **56 test entries, zero errors/failures/skips**. Synthetic suite reports **59 tests, OK**. Static baseline parses 67 Python / 23 XML-SDF / 14 YAML / 24 shell files; all 11 launch descriptions import/generate; all package versions remain 0.4.0.
3. **Minimum change:** none to runtime sources. A small evidence runner records each existing command, duration and exit code, stopping on failure. Final aggregate report asserts actual counts/log results instead of inferring success from exit status alone.
4. **Files changed:** evidence runner, six logs, execution/status JSON and final regression JSON; final dataset report, continuation results, asset limits and tooling README.
5. **Commands run:** `ROS_LOG_DIR=/tmp/wildlife-v05-ros-logs scripts/check_prereqs.sh`; `scripts/build_ros.sh`; sourced project environment, `colcon test --base-paths src --executor sequential`; `colcon test-result --verbose`; final static helper; `python3 -m unittest discover -s tools/synthetic_dataset/tests -v`.
6. **PASS:** `src/`, `scripts/` and typed contracts have zero diff against `v0.4-final`. No tenth ROS package or runtime architecture change. Every required gate is complete.
7. **Evidence:** `final_regression.json`, `final_regression_execution.json`, `final_build.log`, `final_test_results.log`, `final_static.json`, `final_synthetic_tests.log`. [Actual report](DATASET_REPORT.md) includes distributions, annotation audit, fidelity review, commands, hashes, performance, storage and limitations.
8. **Warnings/limits:** regression confirms the existing build/tests/static contracts. It does not add PX4 flight, real-camera detector validation or sim-to-real performance claims. Earlier failures and insufficient attempts remain preserved in this document and their logs; original handoff/master/file inventory remain untouched.
9. **Next gate:** none in V0.5-B1. Stop with the validated and documented dataset; do not begin training, VisDrone work, integration, tracking/mission changes or UGV work.
