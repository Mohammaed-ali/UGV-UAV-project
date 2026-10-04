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
