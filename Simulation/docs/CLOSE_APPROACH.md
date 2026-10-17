# Close approach to a selected tracked target

This stage adds an operator-triggered overhead close hold. It does not spray,
release a parcel, show a product effect, or perform any delivery action.

## Operator workflow

1. Run a Living city survey and click **Track** on a camera-confirmed target.
2. Wait for a fresh, unambiguous observation from the tracking aircraft.
3. In **Detected targets → Close in on tracked target**, set the minimum clearance.
   The initial setting is **0.50 m**, adjustable from 0.50 to 10.00 m.
4. Click **Close in from above**. The view follows the tracking aircraft closely.
5. The aircraft aligns over the observed surface, descends gradually and holds.
   A ruler shows current depth clearance; the wire sphere shows the chosen
   minimum-gap scale around the observed surface point.
6. Click **Back off to tracking** to climb vertically and resume ordinary tracking.
   **Stop & return** still ends the tracking mission and recovers the aircraft.

The setting is a minimum gap, not a commanded distance to the target's centre.
The controller uses a conservative 0.50 m sphere around the aircraft centre and
targets the requested gap plus a 0.25 m control buffer. This includes an allowance
for the aircraft's rotors and landing gear. All displayed units are metres, with
one world unit equal to one metre. The 0.50 m starting value is provisional for
simulation-scale review, not a validated real-aircraft safety distance.

Clearance can be changed between approach attempts. Back off before changing the
setting during an active operation. Normal mission duration, battery reserve,
recall and recovery policies remain in force.

## Motion and observations

Gazebo remains the physical authority and PX4 remains the flight controller.
The browser submits `approach_start` or `approach_stop`; it never positions the UAV.

A co-located downward depth camera supplies 160 × 120 metric float32 images at
10 Hz. It is subscribed only for the selected tracking aircraft, beginning when Track is selected and ending when that tracking flight finishes. Existing RGB cameras remain
640 × 480 at 10 Hz. Current camera and depth observations must be synchronized
with PX4-estimated position/attitude before the controller uses them.

The controller projects the selected RGB bounding-box region into measured depth
to locate its upper visible surface. Depth samples also estimate clearance to
other visible surfaces beneath the aircraft. It does not read the selected city's
actor name, assigned path or actual actor pose to guide the flight.

Close viewing can crop the full vehicle out of the camera image. RGB/depth continuity therefore associates visible raised surface regions with the already selected image identity, retaining appearance, spatial-continuity and ambiguity checks. The optical fallback can follow an interior patch and use measured surface height for camera-motion compensation. This continues an existing identity; it cannot
discover or identify a replacement object without detector evidence.

Descent is limited by `approach_speed` (default 0.40 m/s) and requires horizontal
alignment. Close hold also requires low relative horizontal speed, low vertical
speed, limited tilt and sustained stability.

A brief missing range frame stops descent and holds position. A sustained range
gap, stale or disputed identity, excessive target speed, boundary conflict,
excessive tilt or protective-clearance breach causes vertical backoff.
An aircraft limited to a few metres per second cannot close on fast traffic
moving at 20 m/s. The operator sees the reason when approach is cancelled.

A mission hold cancels close approach and requests a climb. The operator must
request a new approach after normal tracking is restored.

## Limits

- The range check covers surfaces visible to the downward depth camera. It is
  not an all-direction obstacle sensor or a real-world safety certification.
- Occlusion, similar-looking objects, weak image texture or a surface leaving
  the field of view may prevent close hold; the controller must back off.
- Static map routing still protects building clearance. No scene metadata is
  substituted for camera identity or a measured target range.
- Payload dynamics and payload effects are deliberately absent.
- The native validation evaluates actual actor collision-envelope clearance
  separately. Actor truth is used by the evaluator, never the controller.

## Implementation and validation

Primary files: `backend/service.py`, `backend/follow.py`, `backend/mission.py`,
`backend/transport.py`, `backend/vision.py`, `backend/optical.py`,
`backend/world.py`, `backend/depth_visual.py`, `web/CloseApproach.tsx` and `web/World.tsx`.

Run controller/geometry regressions with:

```bash
.venv/bin/python -m pytest tests/test_close_approach.py tests/test_follow.py -q
```

With the browser server running and its physics runtime offline, the owned
single-aircraft native gate is:

```bash
.venv/bin/python scripts/validate_close_approach.py
```

The gate preserves/restores the current mission configuration, follows a slow
moving car, requests a 0.50 m minimum gap, measures close hold, backs off, and
checks return/contact/disarm/latch. Compact evidence, including failed attempts,
is retained in `artifacts/close-approach/native-*/`.

Gazebo's [DepthCameraSensor implementation](https://github.com/gazebosim/gz-sensors/blob/gz-sensors8/src/DepthCameraSensor.cc)
publishes metric depth images on the configured topic. This feature uses that
sensor interface, not a logical camera containing object identities.

## Current validation result

- Backend regression suite: **142 passed**, with one pre-existing dependency warning.
- Frontend checks: **3 passed**; TypeScript/Vite production build passed.
- Native one-aircraft slow-moving-car cycle: **PASS**.
- Continuous close hold: **8.02 simulation seconds**.
- Minimum independently evaluated aircraft-envelope clearance to the car collision
  shape: **0.6105 m**, above the requested **0.50 m** minimum.
- Backoff, return, physical landing, confirmed disarm and latch: **PASS**.
- Original operator mission configuration restored after validation.

Evidence: artifacts/close-approach/native-371fa69b/result.json and its compact
telemetry. Earlier failed attempts are retained. The preceding inspection-pause
run reached close hold but failed on resume with stale PX4 telemetry; it is not
counted as a passing complete mission. A bounded post-pause telemetry
reacquisition path now has a regression test; the passing complete native cycle
was run without an inspection pause.

This validates one slow-moving car with one UAV. Native close-hold qualification
for pedestrians, buses, dense lookalike groups and faster traffic remains open.
The previously documented wider tracking/occlusion limitations still apply.
