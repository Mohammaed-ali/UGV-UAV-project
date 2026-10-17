# Living-city acceptance — 2026-10-09

Work is confined to the standalone Simulation project. Gazebo is the physical
authority; PX4 supplies flight control. Detection, target identity and following
consume camera pixels and timestamped PX4 estimates. Actor truth is restricted
to evaluation. The primary wildlife workspace is checked against 142 baseline
file hashes and its recorded Git status.

## Acceptance criteria

City: zero native UGV/actor and actor/actor contacts; full swept body footprints
within 0.1 m of assigned networks; every moving actor travels at least 3 m;
world-pause displacement below 1 mm; completed crossings and measured destination
arrival. A deliberate obstacle must produce a controlled stop within 0.8 m.

Regular tracking: at least 20 fresh measured samples, observation age below 1 s
when reporting TRACKING, median horizontal follow distance below 8 m, zero resolved
ground-truth identity switches or false reacquisitions, and physical return,
contact, disarm and native latch. Geometric visible coverage must reach 0.8 for
the person baseline and 0.5 for the initial car baseline. Deliberate camera loss
and lookalike ambiguity have separate safe-loss/rejection criteria.

Geometric visibility projects the actual target centre into the calibrated camera
and checks static-building ray obstruction at 0.5 s measured samples. It is not
pixel segmentation. Indeterminate identity associations are reported separately.
The swept-footprint check interpolates measured poses at at most 0.1 m translation
and 2 degrees rotation; recording gaps remain visible. This is an approximation
between measurements, not continuous occupancy instrumentation.

## Current measured gates

| Gate | Status | Evidence and measurements |
| --- | --- | --- |
| Crowded city, 18 people / 10 vehicles / six wheels | PASS | `city-d74b8b7a-28cd-458f-84a9-576ab6c7c82c`: 600 simulation seconds / 841.75 wall seconds; zero native contacts or violations, 10 completed crossings, pause displacement zero, destination error 0.4484 m, maximum lane error 0.317 m, zero swept footprint excess; 201,554 swept actor poses |
| Protected UGV lane and deliberate obstruction | PASS | `city-1059191b-5e18-4a96-acac-d551c4bdad51`: measured stop displacement 0.1044 m, zero contact; injection acknowledgement timed out but the physical intrusion was measured |
| Focused lower UAV02 landing and carousel recovery | PASS | `gateway-validation-94fe0b8f-777e-4c1f-8637-b6d228058bd0`: native contact/disarm/latch at 94.77 s, tag error 12.85 mm; cruise carousel COMPLETE at 115.16 s; zero contacts and swept excess; maximum descent image age 0.16 s |
| Focused UAV02 after telemetry/history correction | PASS | `gateway-validation-5cdb2500-6647-4c48-8131-26abe00026e2`: final COMPLETE at 106.37 s; native contact/disarm/latch and carousel recovery, tag error 17.28 mm; zero city contacts/swept excess |
| Focused lower UAV04 after pose-order correction | PASS for landing/recovery | `gateway-validation-e71c16d9-696f-4786-84e3-fced40a14d96/landing-gate.json`: DOCKED at 112.77 s, final COMPLETE at 132.99 s, contact/disarm/native latch verified, 6.28 mm tag error; accepted capture synchronization 0.004 s; zero contacts/swept excess. Parent survey report remains FAIL because no target was detected |
| Post-survey person selection, relaunch, confirmation and following | PASS | `tracking-505ce791-f8cf-4067-aa6b-0c8715a9b4f7`: selected historical observation age 32.54 s; explicit confirmation of fresh Person-002 at 162.492 s; 87 fresh samples, max age 0.99 s, median distance 3.283 m, geometric visible coverage 0.870, active fresh fraction 0.989; zero switches, false reacquisitions or city contacts; physical docking at 270.56 s with 9.76 mm tag error |
| Moving car | PASS | `tracking-db3ffdb8-0fa2-4114-96ed-16fd5db1db0e`: 82 fresh samples, max age 0.94 s, median distance 3.458 m, coverage 0.930, active fresh fraction 0.932; same Vehicle-001 throughout, zero resolved switches/false reacquisitions/contacts; actual docking at 138.728 s, tag error 6.09 mm |
| Camera loss | PASS | `tracking-c0cc8ca9-8fe1-4076-8877-b4b4a9743de9`: disabled at 72.196 s, LOST/RETURNING at 79.86 s, physical docking at 116.964 s; zero switches/false reacquisitions/contacts |
| Lookalikes | PASS for ambiguity rejection | `tracking-57c56afe-7437-4402-9a55-b730be8f4c5c`: two confirmed candidates, closest separation 1.908 m, 143 ambiguity samples, zero switches/false reacquisitions/contacts; physical docking at 130.82 s. Five fresh samples: safe rejection, not continuous following |
| Eight UAVs / six wheels | PASS | `gateway-validation-891ea8f7-bb29-44f3-84d3-24d849c76fe2`: COMPLETE at 514.34 simulation seconds / 936.90 wall seconds; all eight physically landed, disarmed and latched, zero actor/UGV contacts, zero swept-footprint excess; maximum recording gap 1.68 s, median RTF 0.54 |
| Fully loaded native carousel | PASS | `loaded-carousel-96d6ad5a-2388-4e6f-b7b0-10fcdbc11de9`: lower/upper indexing took 20.340/20.384 simulation seconds with all eight stored aircraft attached; final displacement under 0.05 m. Mechanical test only, no flight claim |
| Eight UAVs / four-wheel split | PASS | `gateway-validation-f2d227a4-9e78-4861-a8d0-0bb2bf323b47`: COMPLETE at 639.72 simulation seconds / 1058.19 wall seconds; four aircraft at each of two stops, all eight physically docked/disarmed/latched, zero native city contacts or swept-footprint excess; maximum recording gap 1.84 s, median RTF 0.59 |
| Stopping vehicle and turn | PASS with limited continuity | `tracking-fe2a9a45-3339-4f2c-8d95-ebd0a43d254e`: 95 fresh samples, max age 0.66 s, median follow distance 4.073 m, geometric coverage 0.764, active fresh fraction 0.546; zero resolved switches/false reacquisitions/contacts, five indeterminate associations; physical docking at 182.70 s. Actual stop, subsequent fresh moving observations and 0.351 rad of turning while fresh were measured; later-turn lock was lost |
| Operating-area exit | PASS | `tracking-15511632-a65f-48f5-9a6e-e2efac048564`: boundary return at 139.84 s, physical docking at 192.636 s; 136 fresh samples, max age 0.99 s, median distance 3.200 m, geometric coverage 0.883, zero switches/false reacquisitions/indeterminate associations/city contacts |
| Building occlusion/reappearance | FAIL during initial discovery | Both preserved surveys missed the three-frame initial confirmation requirement and returned safely; following through a building obstruction is not accepted |
| Browser selection and relaunch | PASS for controls; FAIL for following in this attempt | `browser-follow-ce6aa96d-f54a-484b-b1d4-1a2e390f78bc`: the public browser surveyed, physically docked, selected historical Person-001 and relaunched. The 67-second-old uncertain identity was not reacquired within 60 s. This does not establish successful GUI following |
| Browser early-selection and operator recall | FAIL for discovery; PASS for recall/recovery | `browser-follow-cb018294-b9f7-4ded-b088-f7ccdfa5c868/browser-gate.json`: the survey missed initial confirmation; operator recall physically docked/disarmed/latched at 146.49 s, tag error 11.58 mm. Fresh GUI following remains unverified |

Evidence directories are below `artifacts/living-city`, except gateway fleet
reports directly below `artifacts`. Each physical report retains its result,
evaluation, measured telemetry and representative native camera frames.

## Corrective evidence

An earlier fleet run (`gateway-validation-9c858300-5824-4848-9889-2754c9994b8a`)
failed with true background-actor contacts and UAV02 tag alignment oscillation.
It remains FAIL. Corrected following spacing and a native 50 Hz forecast of
oriented body footprints prevent crowd/queue overlap without teleportation or
disabling occupancy. Actual 600-second bus travel and contacts were rechecked.

PX4 camera alignment uses sample timestamps, not ROS callback arrival time.
Owned SITL startup disables XRCE translation into wall-clock time; the shared
PX4 checkout is unchanged. `px4-sample-clock-audit.json` records actual Gazebo,
PX4 sample/publish and camera clocks: 92.46, 92.46 and 92.40 seconds. The focused
lower-UAV02 gate verifies the resulting physical landing without relaxed tag,
contact, disarm or latch criteria.

Person repeats `tracking-4339a1d7-86d6-46df-a448-0384c02c35cc`,
`tracking-ad8c7caf-3fa7-409a-a728-116c31470a6b` and
`tracking-9b7cc8ef-8899-41ad-becb-05419b4a135f` failed coverage and remain FAIL.
Their images revealed shadow/background appearance matches, competing tentative
hypotheses and abrupt follow corrections. Disputed identities now remain
quarantined, weak person observations require clothing cues, established tracks
take precedence over tentative duplicates, and follow-goal changes are bounded.
The passed person repeat above uses the original numerical threshold.

Older pre-contact-topic reports do not establish zero contacts: their sensor
subscription was inactive. Older tracking passes also precede the final sample
clock and identity corrections. They remain historical evidence, not current
acceptance. Other failed trials and their causes are in `fix-diagnoses.json`.

The carousel now allows 180 simulation seconds while requiring measured progress; a 20-second physical stall still faults. No pose is forced and docking criteria are unchanged. The focused fully loaded mechanical test passed.

In fleet repeat `93813841`, UAV04 continued seeing tag 4 while its controller tag error stopped refreshing. Landing now records capture/position/attitude synchronization checks. Position and attitude are resolved independently at image use time, allowing a matching later-arriving attitude to repair a previously unusable capture. The strict 0.25-second geometry and 0.5-second image limits remain. This fixes a reproducible callback-order flaw; the focused lower-tray and subsequent six- and four-wheel full-fleet physical gates passed.

Fleet repeat `5cccc9fa-fc62-41e9-89de-2c28ba30acde` remains FAIL: UAV02 TAG_ACQUIRE timed out at 394.37 s. Captured-image time 394.10 s had nearest retained position/attitude samples at 395.276/396.768 s, so descent was correctly refused. Raw timestamp matching is unchanged. The bridge now bounds display pose/joint callback rates, reads the native Gazebo clock directly without allowing old stats to rewind it, and retains larger separate estimator histories. Quaternion conversion runs at image lookup rather than every position callback. Focused clock/landing and both full-fleet physical repeats passed.

Fleet repeat `84cdcaf6-2d59-443c-8c1d-f16cd733cd89` reached COMPLETE at 674.10 s with all eight aircraft physically docked, disarmed and attached, zero actor/UGV contacts or footprint excess, and 11 pedestrian crossings. Its acceptance report remains FAIL because the API observer left a 4.08-second recording gap (limit under 3 seconds) at the loaded-index transition. The authority trace hit its 32 MiB cap just before that gap, so the missing measurements cannot be reconstructed. Camera capture is now asynchronous and limited to changed aircraft phases; mission traces omit duplicate target histories without changing physical/safety fields or the storage cap. The subsequent six-wheel and four-wheel split full repeats passed without relaxing the recording-gap limit.

## Processing and honest limits

Current post-survey person: peak owned RSS 2251.7 MiB, median CPU 356.1% (about
3.6 logical cores), median Gazebo RTF 1.00, maximum telemetry age 0.02 s.
542 primary detector frames and 438 optical frames were processed during the
278.69-second run. Median image-centre error was 125.8 pixels. Coverage and
centering remain measured limits; uninterrupted visual lock is not claimed.
Current car: peak RSS 2967.1 MiB, median CPU 252.8%, median RTF 1.00,
maximum telemetry age 0.03 s, median image-centre error 83.2 pixels. Measured
aircraft peak horizontal speed was 2.788 m/s and target peak 1.646 m/s at the
configured 3.0/1.6 m/s limits; `speed-margin.json` records sampled reacquisition
closing speed. This does not justify higher-speed traffic.
Crowded-city median RTF was 0.77. Native cameras remain 640×480 at 10 Hz.
Public browser preview was observed at 37 FPS. GPU utilization was unavailable.

Background people and traffic use controlled kinematic collision bodies,
approximate gait, measured wheels and physical occupancy. These are not full
biomechanics or tire dynamics. Vehicle subclasses from supplemental aerial
inference remain provisional; inspect the crop and use Any vehicle when needed.
Appearance confidence is a heuristic, not permanent identification. Monochrome,
tiny or occluded objects can lack useful appearance cues. Lookalike ambiguity can
require operator confirmation. Moving-carrier landing, faces/plates and optional
reserve-aircraft handoff are deferred. SITL battery is not calibrated endurance.

## Browser, persistence and cleanup

HTTP/WebSocket access checks and actual authenticated public browser rendering
passed for the current owned Cloudflare tunnel. Anonymous access is blocked;
authentication uses a Secure/HttpOnly cookie; cross-origin commands are rejected.
The private URL works while the host PC and tunnel are running. The tunnel name
can change after restart. Startup remains `./scripts/start.sh`; open the HTTP
address rather than a file URL.

Native mission export's download observer timed out in the in-app browser; no
successful export claim is made. A visible unsaved four-aircraft browser draft
was backed up separately; the saved three-stop mission is preserved. Browser mission import and save succeeded, and the saved one-person configuration survived a documented server cold restart. All three perception systems were ready after restart. Primary-isolation comparison passed for all 142 baseline hashes and the recorded Git status. Public-browser selection/relaunch and native recall/recovery were exercised with the qualified results above. Fresh GUI following did not pass. Final cleanup is recorded below.

Junk cleanup was applied after the physical runtime and recorders were idle. `artifacts/junk-cleanup.json` records 1,848,606,986 bytes freed, the exact removal manifest and folder review. Raw traces were compacted with hashes, state/event timelines, final state and measured travel before deletion. Required source, tests, assets, detector weights/licenses, dependencies, compiled browser app, native plugin and compact pass/failure/camera evidence were retained. Regenerable caches can reappear during normal startup.

Post-cleanup cold start passed: restored three-stop/balanced mission matched both the saved file and preserved original; all three perception systems were ready; 142 asset parts, compiled app and export API returned successfully; native plugin was retained. HTTP/authenticated WebSocket checks passed again. Primary preservation passed for all 142 hashes and recorded Git status. The service is left online with physics offline until Initialize is clicked.

Current software: 81 backend checks and three frontend checks passed; the production frontend build passed after the repeated-return correction. Large Three.js chunk and upstream test-client deprecation warnings remain informational.

The first stopping-car launch (`tracking-a1bd1718-36d3-4f06-8bb7-a194d9b83ec8`) failed initialization with missing FIELDLAB_DEPS; no flight occurred. The sequential runner now sources the project robotics environment for each child gate. That failed attempt is retained separately.

Building-occlusion survey `tracking-bffb2012-de74-43e6-afd2-ee39862e8a1f` remains FAIL: only two camera person observations met the score threshold during the initial pass, below the three-frame catalogue confirmation requirement. It returned/docked at 153.36 s without selecting a target. A six-second arrival-timing adjustment was also tested in `tracking-46443ce8-3aca-4644-bb3c-eeae043f02c6`; it still failed to confirm the initial target and docked at 151.344 s. The ineffective adjustment was reverted. This preset remains a known failed scenario; safe no-target recovery is verified, occlusion/reappearance following is not.

The public-browser run exposed a repeated-stop defect: a stop during DESCENDING restarted RETURNING while the approach reservation remained held. That run remains FAIL and was reset after preserving measured state. Follow finish is now idempotent, recall preserves all existing recovery phases, and the browser disables Stop during RETURNING/DOCKED/FINISHED. Two focused regression checks passed; the subsequent native operator recall and docking passed. Actual repeat-stop-during-approach physics was not repeated.

Final public-browser handover rendered the restored three-stop/eight-aircraft city preview at approximately 29–33 FPS after cleanup. `browser-final-city.jpg` is the actual browser screenshot; it is a scene preview, with physical runtime offline until initialization.

## Compact city and immediate Track controls — 2026-10-14

109 backend tests, 3 frontend tests, and the production build pass. Browser
selection, drag, validated placement, and Save were exercised; the test moved
a person from (-85, -55) to (-98.5, -55.5). The operator mission was restored.

The native speed/placement gate passes with UGV cruise set to 10 m/s, traffic
20 m/s, and people 5 m/s. Measured UGV speed reached 10.0 m/s. Six people and
six vehicles stayed within their networks with zero actor/UGV contacts, zero
actor contacts, and zero crossing violations. A person, car and bus were moved
into free space and then returned to proper public paths; native pose confirmation
and resumed path motion passed. The protected service lane rejected placement.
This is a focused 100-simulation-second control gate, not a full fleet mission.

A native PX4 camera flight confirmed a person and switched to TRACKING in the
same start_tracking command (5.06 ms inside the controller; network/browser
latency is additional). It returned, disarmed and latched physically at 114.2 s.
No identity switches or false reacquisitions were measured. The uninterrupted
follow benchmark remains partial: only 16 fresh samples, 0.410 fresh fraction,
and 0.343 geometric-visible coverage. Its failing result and camera evidence
are retained. Earlier tracking acceptance results apply to the preceding map.

The private internet HTTP/WebSocket check and primary workspace preservation
check pass. Full details and evidence paths are in
`artifacts/instant-tracking/release-summary.json`.
