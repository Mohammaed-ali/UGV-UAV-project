# Living city and visually selected tracking

## Run and use

Run `./scripts/start.sh` from the standalone Simulation directory. Open
http://127.0.0.1:8765 (never open index.html directly). Enable Living city,
configure counts, speeds, seed and route, Save, then Initialize and Start.
The original three-stop allocation is preserved. Edits snap within 4 m to the
protected service network or produce a validation error. Stops are deployment
bays along that network. The route connects through its central junction.

Cameras build the Detected targets catalogue during survey. Click **Track** on
any catalogue card to atomically select that identity and switch the latest
healthy airborne camera observer directly to following. The aircraft can come
from either original tray. There is no requirement to complete the other stops,
recover other aircraft, or index the carousel before an airborne switch. Other
survey aircraft return through the normal single-corridor recovery sequence;
launches not yet begun are cancelled. An aircraft already releasing finishes its
safe takeoff before returning. Lower-original aircraft still recover first.
The carrier stops at its measured position during tracking.

A fresh, unambiguous observation starts following in the same command. Stale or
uncertain sightings start visual reacquisition; selecting them does not refresh
their image timestamps. If only a docked aircraft is available, relaunch still
requires the recovery corridor and upper flight deck to be clear. Stop tracking
uses the existing AprilTag contact, disarm and latch sequence.

Choose up to three Search classes in Mission. Aircraft divide their map survey
between sidewalks and vehicle lanes according to those classes, and can observe
camera-confirmed people, cars and buses concurrently. The catalogue retains
individual image identities. Tracking follows one selected individual at a time.
A tentative detector sighting may centre the search camera, but only repeated
high-score images create a confirmed catalogue entry.

Speed controls are adjustable up to UGV **10 m/s**, traffic **20 m/s**, and
people **5 m/s**, including while physics runs. These are cruise limits: turn
curvature, stopping distance, crossings and physical spacing can reduce speed.
The UGV wheel joint limit permits the requested cruise speed, and its approach
controller starts braking using the measured speed and stopping distance.

In Environment, enable **Placement mode**, select a person/car/truck/bus, then
drag it, click a free destination, or enter X/Y and press Move selected actor.
Before initialization, validated positions remain in the editable mission until
Save; exported missions include these placements. During a running world, edits
change only that live run and require measured Gazebo pose confirmation. Resume
physics before a live edit. A position within 0.45 m of an appropriate public
path resumes that path, with its direction; an off-path position stays stationary.
Placement rejects buildings, occupied space, deployment bays and the UGV lane.
The browser shows a drop marker until the backend validates the request; it never
moves a live model independently of physics.

Scenario presets replace the route and population with a one-UAV test mission.
JSON configurations are in missions/scenarios. Import them using the browser's
Import mission button. A count of vehicles determines traffic density. An
optional reserve-aircraft handoff is deferred; this release follows with one UAV.

## Authorities and separate data paths

* Gazebo controls aircraft, wheel-driven UGV motion, contacts, carousel, latches,
  cameras and measured city-body movement. Native CityBody.cc receives bounded
  velocity commands and advances visual gait/wheels from measured displacement.
* PX4 SITL controls actual thrust and flight through bounded offboard setpoints.
* City controls traffic from physical poses and public movement networks. It owns
  actor identities for simulation, but these identities do not reach perception.
* Vision receives camera pixels and synchronized PX4 estimated position/attitude
  with known launch origins. YOLOX supplies primary class evidence. A single supplemental aerial vehicle
  worker runs at no more than 0.5 Hz globally. Registry associates
  observations using image appearance, estimated location and observed velocity.
* Follow consumes only the selected visual track, previous observations and the
  public static map. Public sidewalks/lanes constrain search hypotheses; no actor
  assignment, future destination or simulator position is supplied. Predicted
  search positions never refresh last-seen timestamps.
* Evaluation scripts separately read actor truth to measure movement, error and
  contacts. Truth is never fed back into operational target following.
* Browser interpolates measured Gazebo snapshots. It sends intentions through
  validated run-scoped, replay-protected commands; it cannot move bodies itself.

## City and physical occupancy

The 240 m square map contains three compact public districts with rounded two-way roads,
sidewalk circuits, twelve economical buildings and controlled pedestrian crossings.
A 7.2 m wide cross-shaped UGV corridor is separated from public traffic. Bay
clearance is 4.7 m; geometry checks include loaded trays, supports, carousel
movement and the circular swept footprint of the square carrier.

Background vehicles and pedestrians use controlled kinematic collision bodies
with contact sensors, bounded acceleration, spacing and measured path projection.
Their occupancy remains physical. Cars use a pinned Apache-2.0 Open Robotics
Prius visual asset converted to the same metre-scale frame for both renderers.
Source files, conversion details, hashes and license are retained under assets.
The car visual footprint is bounded by its conservative collision body. This is not tire dynamics or biomechanics.
Walking animation approximates gait; it does not implement foot IK. Vehicle
steering and wheel angles derive from measured yaw rate and displacement.
Pedestrian entry uses crossing reservations and vehicles queue at stop lines.
Gazebo pause freezes movement and simulation-time decisions. Stalled UGV progress
retains the existing hold protection. Actors move only through their path controller or an explicit validated operator placement.

The loaded carousel follows measured prismatic-joint progress. Indexing has a 180-second simulation-time ceiling and faults if physical progress stops for 20 seconds. The controller never forces tray or aircraft poses. Position and attitude are matched independently to capture timestamps when landing images are used; delayed DDS delivery must still satisfy the 0.25-second geometry and 0.5-second image limits.

## Perception limits

Cameras remain 640x480 at 10 Hz, approximately 70 degrees horizontal FoV. At
12 m altitude the nominal ground footprint is about 16.8 x 12.6 m, narrower at
the target's top surface. Buildings occlude pixels. The downward camera cannot
recognize objects simply because they exist inside a requested orbit radius.

The tracker uses ByteTrack-inspired high/low score association with appearance
and motion gates, rather than claiming upstream ByteTrack compatibility. Three
distinct high-score frames confirm a catalogue entry. Selected tracking uses
CSRT seeded by an actual high-score detection; at most two survey observations
receive this additional image tracking. Seed and preceding tracker images are reprojected using timestamped PX4 camera
motion before matching the current image; the original appearance signature is
preserved through those transforms. Reprojection alone is never a new sighting. Class confidence
retains the last detector score and its age. Identity confidence and optical quality are separate heuristics,
not calibrated probabilities. The supplemental aerial model is pinned with a
SHA-256 and its AGPL-3.0 license in assets/detector. Its vehicle subclass labels
are provisional on the reused synthetic models. Choose Any vehicle and confirm
by thumbnail; this does not claim reliable sedan-versus-bus classification.
The Aerial vehicle discovery control can disable the extra inference.
Person appearance association compares saturated clothing pixels inside the
image box. Weak person detections require that cue; repeated high-score class
detections can still establish a candidate through short spatial continuity.
Insufficient foreground cannot support optical or long-gap appearance matching. This
lightweight colour cue is limited by object size, lighting and monochrome clothing.
Ambiguous association is reported and does not
silently switch to the nearest similar target. Prediction stops after 8 seconds;
longer search hypotheses are limited to 120 m of arc travel on the public map
and labeled unconfirmed. Search still ends at the configured timeout.

Follow-goal corrections are rate-limited by the configured flight speed to
reduce aircraft tilt after a pixel-box correction. Continuing confirmed tracks
take precedence over tentative duplicates; simultaneous lookalike checks remain active.
Following keeps a stable aircraft heading for the downward camera and limits
trailing distance using field of view, class-wide object size and a tilt margin.
The requested distance can therefore be reduced to retain useful image coverage.
It uses observed motion, bounded lead, calibrated camera coverage and
static building-volume avoidance. It stops at duration, reserve, operator stop,
loss timeout or the permitted flight boundary. Moving-carrier recovery, face or
number-plate recognition and arbitrary long-gap identification are outside scope.

## Resource limits

Images use latest-frame processing with two detector workers and independent
landing/visual tracking workers. Perception is activated on mission demand.
Catalogue metadata is capped at 250 entries, crops at 128 thumbnails, histories
at 12 observations per entry and event history at 120. No continuous video is
recorded. Native archived ULog/BSON files remain capped at 512 MiB by default.
Duplicate raw mission JSONL logs have a 128 MiB retention budget and a per-run
32 MiB cap with compact summaries. Validation evidence is retained separately.
These budgets do not cap an ongoing native flight or all project files. Mission traces omit repeated catalogue histories and record only new events, while preserving measured poses and safety fields. Native clock updates are monotonic, display pose/joint subscriptions are bounded, and separate timestamped position/attitude histories are matched when a camera image is used.

## Reproduce checks

```bash
cd '/home/mohammed-ali/Downloads/gpt /Simulation'
source scripts/environment.sh
.venv/bin/python scripts/prepare_textured_car.py
.venv/bin/python scripts/prepare_city_assets.py
./scripts/build_city.sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_city.py --seconds 600 --wheels 6
.venv/bin/python scripts/validate_city.py --fault
.venv/bin/python scripts/validate_tracking.py --class person --duration 45
.venv/bin/python scripts/validate_tracking.py --after-survey --duration 45
.venv/bin/python scripts/validate_tracking.py --class vehicle --duration 45
.venv/bin/python scripts/validate_tracking.py --camera-drop --duration 45
.venv/bin/python scripts/validate_tracking.py --scenario similar-people --expect-ambiguity
.venv/bin/python scripts/validate_tracking.py --scenario leaving-area --duration 120 --expected-outcome left-area
.venv/bin/python scripts/validate_gateway_mission.py --city --target --drones 8 --wheels 6 --timeout 2600
.venv/bin/python scripts/validate_gateway_mission.py --city --target --drones 8 --wheels 4 --split --timeout 2600
```

The sequential runner `scripts/validate_living_city_release.py` stops at the first failed gate; `--start-at` resumes from an explicitly selected incomplete gate. It sources the project robotics environment for each child and retains each gate report. Offline `scripts/evaluate_scenario_events.py` verifies measured stop/turn, building obstruction/reappearance and boundary-exit events without supplying truth to perception.

Run one owned physical runtime at a time. The runtime lock prevents independent
validators and the browser from initializing competing worlds. Gateway fleet
validation uses the running web server, saves/restores its mission, and resets
only its generated test run. Existing internet access uses scripts/share.sh and
the private link in .runtime/share-link.txt. The host and tunnel must remain online.

See LIVING_CITY_VALIDATION.md for actual measured passes, failures and limitations.

City path steering runs in the native Gazebo plugin using current physical body poses. The Python controller supplies speed permissions, yielding and crossing reservations; a stale command stops the body after 0.55 simulation seconds. No world-pose reset is used for routine motion. A read-only native latch monitor repeats actual detachable-joint component state every 0.2 simulation seconds, so a lost transition message cannot leave a physically attached aircraft waiting indefinitely. The stock joint system still creates and removes the constraints.

Reproducible walking, lookalike, occlusion and exit scenarios start pedestrians
on an approach to the survey area. They move continuously from world startup;
mission selection never teleports, pauses or secretly slows them. Custom city
keeps its existing seeded placement. A real target can leave a site's radius
before a delayed deployment, in which case no-target recovery is expected.

Survey paths check the nearest public sidewalk/lane first, sweep both directions
within the assigned radius and revisit the centre. Multiple aircraft use staggered
map scans. Actor locations and future routes never guide those scan goals.

Aircraft pose histories use PX4 sensor sample timestamps and the closest
sampled attitude, rather than the callback arrival time. The owned SITL startup
sets `UXRCE_DDS_SYNCT=0` before the DDS client starts because PX4 already follows
the Gazebo clock. This prevents the agent from translating simulated samples to
wall time. The shared PX4 checkout remains read-only. A mismatched attitude or
image time cannot authorize landing descent.

City comfort braking uses a continuous gap limit, including queued actors.
A native 50 Hz emergency check forecasts 0.8 seconds of the commanded physical
motion and tests oriented collision rectangles with a clearance margin. It
includes parked bodies and shared sidewalk branches. This remains controlled
kinematic occupancy, with emergency velocity limiting rather than tire-force
braking. The check never teleports a body or disables collisions.

For selected people, separate nearby image regions with the same observed
clothing hue also challenge identity, including rivals whose class score is too
low to confirm a separate catalogue row. This is a conservative pixel-colour
ambiguity check, not facial recognition or a new person classifier. It can
request confirmation unnecessarily. Disputed IDs remain quarantined until the
operator confirms a fresh candidate, so an older hypothesis cannot repeatedly
challenge its confirmed replacement. A pixel-colour challenge requires matching
clothing inside the current optical box as well as a separate nearby region.
A displaced empty box is a lost lock, not proof of a second person. Appearance
alone does not prove identity.
