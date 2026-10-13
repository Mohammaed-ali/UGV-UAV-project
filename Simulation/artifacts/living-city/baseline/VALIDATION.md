# Validation evidence

All work and generated evidence belong to this independent Simulation project.
The existing wildlife workspace is read-only.

## Passed checks

* Frontend TypeScript/Vite production build; three route/validation tests passed.
* Twenty-seven Python tests passed, including correct-aircraft contact, actual latch
  release before takeoff, contact/disarm requirements before docking, tag identity,
  camera frame transforms, landing-frame loss handling, reset after a fault,
  shutdown ordering and remote access controls.
* `artifacts/primary-preservation.json`: 142 original source/script file hashes
  match their baseline, and the original Git status matches. No changes were made
  to the primary wildlife workspace.
* Authenticated internet access: `artifacts/internet-access-validation.json`.
  Anonymous mission state is rejected; key login, secure HttpOnly cookie, live
  state, camera preview and a harmless camera-preview command pass. Cross-origin
  login and command requests are rejected. The public browser received live
  WebSocket telemetry and displayed the physical scene.

Build warnings: the dynamically loaded Three.js scene chunk exceeds Vite's
default 500 KB advisory. Test warning: the installed Starlette version deprecates
its HTTPX test-client adapter. Neither warning caused a check to fail.

## Measured physical mission

`artifacts/validation-eed43582-d8d8-4b4a-92d7-b82f350b3951/result.json` is a passed
one-aircraft, four-wheel, target-absent mission. The carrier drove to its stop;
UAV01 launched from an extended physical tray, searched, loitered, returned,
aligned to tag 1 from rendered pixels, landed with native PX4 control, contacted
the assigned tray, disarmed, latched and retracted. Final state was COMPLETE,
UAV01 DOCKED, disarmed and physically latched. Final tag alignment error was
0.0155 m; mission time was 87.73 simulation seconds and 102.8 wall seconds.
Camera images, telemetry, contact information, command acknowledgements and
native flight logs accompany the report.

That flight predates the separate landing-worker correction below. Its result
does not establish a post-correction flight or an eight-aircraft acceptance gate.
Small mission logs and failed-run reports are retained. On 2026-10-07 the user
requested deletion of disposable native archives: 13 inactive run directories
were removed, freeing 8.66 GiB. See `artifacts/run-cleanup.json`. Native logs
mentioned in older reports may have been removed; the separate UAV05 diagnosis
log was retained. New native archives use a 512 MiB default retention budget.

## UAV01 landing fault and correction

Run `be428ede-d621-42e1-8c83-b563161f53fe` deployed three aircraft at Alpha.
UAV01 acquired the correct tag and began descending. At simulation time 397.22,
the mission faulted with `Landing tag lost; recovery requires operator`.
The camera still detected tag 1. Recorded frame ages during recovery reached
1.31 s; new landing observations arrived approximately 1.2–1.4 s apart. The
controller's 0.5 s freshness threshold rejected them and exhausted two retries.
The cause was a shared sequential image worker: object inference for other
aircraft delayed landing observations even though tag inference itself was fast.

The corrected source gives AprilTag processing its own worker and retains
independent tag/object timestamps. Descent stops immediately when tag observations
are stale. A brief interruption does not consume a recovery attempt; a sustained
two-second loss initiates reacquisition. The original 0.5 s freshness requirement,
tag identity, contact and disarm checks remain enforced.

`artifacts/landing-vision-replay/result.json` passes a scheduling benchmark using
actual captured Gazebo camera pixels replayed at controlled 10 Hz timestamps,
alongside object inference for two other aircraft. It processed 119 distinct
landing frames, detected assigned tag 1 in all 119, and had zero stale samples.
Maximum observation age was 0.1239 s, p99 age 0.1220 s, and p99 tag inference
16.9 ms. This is a processing benchmark, **not physical-flight acceptance**.

`artifacts/landing-vision-probe/result.json` records an attempted read-only live
probe. It received no images because the operator had paused the world. Its
`passed: false` result represents unavailable live input; it does not validate
the new worker in a moving world. The faulted run was archived before the operator
approved a reset and server restart. The corrected worker is now active.

## Post-correction physical regression

`artifacts/gateway-validation-f11588d1-ad08-4fff-b9f3-bb910881725c/result.json`
and `summary.json` record a passed three-aircraft physical mission through the
operator API. The four-wheel carrier, UAV01 upper tray, UAV02 lower tray and UAV03
upper tray all completed launch, no-target search/loiter, tag-guided return,
native PX4 landing, assigned-tray contact, disarm, latch and retraction. Final
mission state was COMPLETE; all three aircraft were DOCKED, disarmed and latched.
Final alignment errors were 0.0211 m, 0.0129 m and 0.0227 m respectively. Maximum
recorded landing image ages were 0.14 s, 0.17 s and 0.18 s, all below 0.5 s.
The run lasted 242.86 simulation seconds and 255.42 wall seconds including startup.

Telemetry, rendered camera images, the original mission backup and flight logs
are preserved. The regression reset its own runtime, restored the original
three-stop mission and left the application ready to initialize a fresh world.

## Deployment blocked after a fault and reset

Run `cc4832ea-18fa-4c4a-ae6c-9c7262ef045f` reached Alpha with all eight aircraft
STORED, disarmed and PX4-ready, but remained DEPLOYING. Reset had retained the
previous run's UAV04 docking reservation and launch timer. A docking reservation
blocks launches, while the old launch timestamp also delays a new world whose
simulation clock starts at zero. The old log timestamp suppressed new telemetry
files as well.

Configuration/reset now clears corridor ownership, launch and logging clocks,
hold/abort flags and command bookkeeping. Runtime shutdown marks itself stopping
before closing telemetry, preventing concurrent controller ticks from using
closed transports. Regression tests reproduce fault/reset with an older, larger
simulation timestamp and verify immediate launch eligibility and new-run logging.
The preserved blocked snapshot, mission and runtime logs are in
`artifacts/deployment-reset-cc4832ea-18fa-4c4a-ae6c-9c7262ef045f/`.

`after-fix-result.json` and `summary.json` in that directory pass physical
deployment verification for run `a2cdb629-d678-4158-81e4-63119ee854ea`. The original
three-stop, eight-aircraft plan was preserved. All three scheduled Alpha aircraft
(UAV01–03) armed, released their measured latches and climbed more than 2 m above
their stored positions under PX4 Offboard control. Measured takeoff heights were
4.719, 3.796 and 4.569 m at simulation times 111.34, 129.13 and 147.12 s.
This check took 173.12 wall seconds including startup of all eight controllers.
The operator mission was left running. These results validate first-stop
deployment after the correction; they do not establish complete eight-aircraft
recovery across all stops. The existing internet gateway reconnected successfully
without restarting its tunnel.

## Carousel update — current validation

The prior flights above used individual sliding trays. The new rack uses two
common square trays with four pads each and physically driven carousel joints.

* 27 backend tests pass: square paired layout, measured actuator gating, lower
  recovery priority, image-relative correction despite estimator bias, independent
  target confirmation, bounded archive cleanup, and the prior mission/access gates.
* TypeScript/Vite build passes; the three active frontend validation tests pass.
* Generated four-wheel SDF validates, with existing PX4 `gz_frame_id` extension
  warnings. Physical runtime construction is separately verified by flight.
* `artifacts/gateway-validation-587d68f5-2b8a-465d-9949-a7c93f5ea846/result.json`: **PASS**,
  one aircraft, four wheels, no target. UAV01 physically launched, searched,
  loitered, acquired tag 1, descended, contacted its pad, disarmed and latched.
  COMPLETE at 67.89 simulation seconds, 93.79 wall seconds; final tag alignment
  error 0.00572 m. The original mission was restored after the test.
* `artifacts/gateway-validation-af7222f2-5c14-4a5e-80db-339b4bccd230/result.json`: **FAIL**,
  interrupted server during descent. Native crash address identifies AprilTag
  family cleanup. The binding freed families before releasing detector references;
  cleanup now clears those references first. Fifteen detector create/detect/destroy
  cycles passed. ROS no longer replaces the server process signal handlers.
  The precise external trigger for shutdown was not established.
* `artifacts/gateway-validation-a83ae2a7-e7d3-4474-a882-7ad311486ecb/result.json`: **FAIL**,
  PX4 telemetry timed out after resetting an earlier run. Each fleet now owns
  its own ROS context and executor, and closes them on reset.
* `artifacts/gateway-validation-d91f267b-8571-4e5a-bb67-a02f55c69493/summary.json`: **PASS**,
  two aircraft, six wheels, no target. UAV01 launched from the upper tray, then
  UAV02 launched after the lower tray rose. UAV02 docked first; the carousel
  restored the upper tray, then UAV01 docked. COMPLETE at 153.53 simulation seconds,
  258.13 wall seconds. Final image errors were 0.0167 and 0.0249 m; maximum landing
  image age was 0.17 s. Across 616 moving-carousel samples, all stored/docked
  aircraft remained latched and disarmed. This flight predates the square chassis.
* `artifacts/gateway-validation-7b130401-2051-48ca-976d-84e1bd1adc71/summary.json`: **FAIL**,
  eight aircraft in the city. All eight physically launched and confirmed a
  person from camera detections. UAV02/04/06 docked. At 387.86 simulation seconds,
  telemetry for all eight controllers aged simultaneously beyond 2.5 wall seconds,
  faulting active aircraft. Processes were still alive; host load or a shared
  publishing backlog was suspected but not proven. The validation observer had
  been interrupted and resumed; its result documents the recording gap.
  Continuous setpoints now use PX4-compatible best-effort, depth-one publishing;
  camera demand is released while aircraft wait to recover. Freshness gates remain.
* `artifacts/gateway-validation-32810c16-74bc-4e39-a4f7-e87069814d32/summary.json`: **PASS**,
  square four-wheel carrier, one aircraft, city, target present. UAV01 confirmed
  a person, approached/observed it, returned with a reactivated landing camera,
  landed, contacted the pad, disarmed and latched. COMPLETE at 60.80 simulation
  seconds, 92.41 wall seconds. Final tag error 0.01952 m, physical XY pad offset
  0.00927 m; maximum recorded landing image age 0.16 s.

`target-confirmation-replay.json` in the failed eight-aircraft directory compares
the new candidate association against saved image-derived detection outputs.
Recorded confirmation delays improve from 19.6 to 1.2 simulation seconds for
UAV03 and from 16.2 to 1.8 seconds for UAV05; other aircraft improve little or
not at all where suitable continuing detections are sparse. This is perception
output replay, **not a new physical-flight gate**.

The chassis/deck now share the square trays' shape: 3.05/3.22 m square around
2.65 m square trays. Physics inertia, wheel placement and browser geometry use
the same dimensions. Camera-demand ownership has a regression test so closing a
preview cannot accidentally disable mission perception.

`artifacts/gateway-validation-5091e0b0-774d-48f9-8f24-c9a0870588f7/summary.json`:
**PASS**, eight aircraft, square six-wheel carrier, city with 18 people and 10
parked vehicles, person targets present. All eight confirmed targets from actual
camera detections, approached/observed them, returned, landed on their assigned
AprilTag pads, disarmed and latched. The observed launch order was 1/3/5/7 then
2/4/6/8; docking order 2/4/6/8 then 1/3/5/7. The loaded lower tray circulated back
down before upper-tray recovery. COMPLETE at 424.36 simulation seconds,
601.74 wall seconds including startup. All stored/docked aircraft were latched
and disarmed across 104 observer samples during indexing.

Maximum recorded landing-image age was 0.21 simulation seconds; maximum airborne
PX4 telemetry age was 0.74 wall seconds. Final image alignment errors ranged from
0.00143 to 0.02419 m; measured final aircraft-to-pad XY offsets ranged from 0.00661
to 0.03300 m. UAV05 specifically docked with 0.00967 m image error and 0.00702 m
physical XY offset. The shared stale-telemetry fault did not recur in this run.
This establishes the complete eight-aircraft carousel cycle at one city stop
under the tested conditions; it does not prove wind or moving-obstacle handling.

The successful run's target replay also documents uneven visibility: seven live
confirmations followed their first recorded matching frame within 0–2.4 simulation
seconds, while UAV07 required 11 seconds. Snapshots omit intermediate detector
frames, so these values describe recorded visibility rather than a guaranteed
detection latency. Camera activation-to-confirmation includes takeoff and took
13.04–25.44 simulation seconds. The source never confirms a target from its
scene metadata or orbit membership alone.

`artifacts/gateway-validation-58849088-5b4d-4f65-b40e-be60a3b0f67f/summary.json`:
**PASS**, square four-wheel carrier, UAV01 at the first stop and UAV02 at a
second stop 8 m farther along the road, no targets. The carrier recovered UAV01,
drove onward with it latched, raised the original lower tray, launched and
recovered UAV02, then restored the original upper tray. The other six aircraft
stayed stored throughout. COMPLETE at 180.32 simulation seconds, 194.53 wall
seconds. Final image errors were 0.00230/0.01040 m, physical pad offsets
0.01658/0.01184 m, maximum landing image age 0.15 simulation seconds and airborne
telemetry age 0.03 wall seconds. No stored/docked aircraft was armed or unlatched
across 83 recorded carousel-motion samples. The original three-stop plan was
restored after the test.

The renewed internet link passes `artifacts/carousel-upgrade/internet-access-current.json`:
anonymous state 401, authenticated state 200, secure HttpOnly cookie, rejected
cross-origin command 403, and working live WebSocket. Earlier temporary tunnels
expired; their logs are retained. A temporary link requires the host and sharing
process to remain online and is not a permanent hosted deployment.

## Remaining acceptance work

Validate larger multi-stop allocations, pause/resume and wind beyond the measured
carousel gates above. The eight-aircraft run covers all eight pads, the six-wheel
carrier, target-present camera detection and full recovery at one stop. The
two-stop run validates partial allocations, carrier travel with a recovered
aircraft, and subsequent deployment/recovery from the other tray.
Moving pedestrians/traffic, broad obstacle avoidance and target-loss tracking
remain incomplete. Static people/vehicles and flat ground-plane localization are
the current scope. The interface and successful build do not prove these gates.

## Two-tray physical exchange

`artifacts/gateway-validation-d91f267b-8571-4e5a-bb67-a02f55c69493/result.json`
records **PASS** for UAV01 and UAV02 on the six-wheel carrier. UAV01 launched from
the original upper tray; both loaded trays circulated, then UAV02 launched from
the raised original lower tray. UAV02 returned, contacted its assigned pad,
disarmed and latched first. Its tray moved down before UAV01's approach and
recovery. COMPLETE at 153.53 simulation seconds, 258.10 wall seconds. Final tag
errors were 0.01672 m and 0.02492 m. Remaining aircraft stayed physically latched
while their trays moved. See the accompanying `summary.json` for measured motion,
ordering, image ages and final physical pad offsets.

`artifacts/gateway-validation-a83ae2a7-e7d3-4474-a882-7ad311486ecb/result.json`
retains a failed startup attempt: UAV01 telemetry timed out before any launch.
ROS context and executor are now scoped to each run and shut down at reset.
The next eight-aircraft test also checks reinitialization without a server restart.
