# Validation evidence

All work and generated evidence belong to this independent Simulation project.
The existing wildlife workspace is read-only.

## Passed checks

* Frontend TypeScript/Vite production build; three route/validation tests passed.
* Eighteen Python tests passed, including correct-aircraft contact, actual latch
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
Earlier failed integration runs are retained under `artifacts/runs/`.

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

## Remaining acceptance work

Validate four/eight aircraft, all eight tray positions, six-wheel carrier,
multi-stop recovery, target-present camera detection, pause/resume and wind.
Moving pedestrians/traffic, broad obstacle avoidance and target-loss tracking
remain incomplete. Static people/vehicles and flat ground-plane localization are
the current scope. The interface and successful build do not prove these gates.
