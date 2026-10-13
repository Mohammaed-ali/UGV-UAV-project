# Fieldlab — independent UGV and drone simulation

This project lives in `/home/mohammed-ali/Downloads/gpt /Simulation`. It is separate
from the existing wildlife ROS workspace. Its browser interface connects to a
local Gazebo Harmonic / ROS 2 Jazzy / PX4 SITL backend.

## Open the application

**Use the server URL, not `index.html`.** The source HTML needs compiled assets,
API routes and the live telemetry connection.

```bash
cd '/home/mohammed-ali/Downloads/gpt /Simulation'
./scripts/start.sh
```

Keep that terminal running and open **http://127.0.0.1:8765** in your browser.
The page first shows a scene preview. Configure the route and aircraft allocation,
click **Initialize simulation**, then **Start mission** once telemetry is ready.
Reset stops this project's simulator processes and allows configuration changes.
Closing the browser does not stop the local backend; Ctrl+C in its terminal does.

## Open it from another computer over the internet

Leave `./scripts/start.sh` running. In a second terminal, run:

```bash
cd '/home/mohammed-ali/Downloads/gpt /Simulation'
./scripts/share.sh
```

The script downloads the pinned official `cloudflared` binary into this project's
`.runtime/bin/` and checks its release SHA-256. It prints a private HTTPS link.
Open that complete link on another computer in a browser with WebGL enabled.
No ROS, Gazebo or PX4 installation is needed on the viewing computer.
The first visit exchanges the key in the URL fragment for an HttpOnly session cookie
and removes the key from the address bar. The plain link instead shows an access
key form. The generated private link is also saved in `.runtime/share-link.txt`.
Treat the complete link as a password: it grants mission controls.

Physics and camera rendering run on the host PC; the viewing browser draws the 3D
scene from live telemetry. The host PC, its internet connection, the simulation
server and the sharing terminal must remain running. Ctrl+C in the sharing terminal
closes internet access without stopping the simulator. The URL changes each time
the tunnel is restarted. This temporary development link has no uptime guarantee;
a permanent deployment requires a configured host/domain and an always-on machine.
See [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

Dependencies and compiled frontend have been prepared on this machine. To rebuild:

```bash
./scripts/setup.sh
```

`FIELDLAB_DEPS` defaults to the existing read-only
`/home/mohammed-ali/Downloads/wildlife_px4_dependencies` installation. The project
uses its pinned PX4 binary and message definitions without changing that checkout.
Source `scripts/environment.sh` for standalone validation commands.

## Implemented structure

* React, TypeScript, Vite and Three.js operator interface: route editing,
  stop-by-stop aircraft allocations, target class, no-target policy, camera view,
  orbit/follow/top/docking views, event timeline and JSON import/export.
* FastAPI/WebSocket gateway and an independent measured-state mission controller.
* Dynamic four/six-wheel skid-steer carrier and two common 2 × 2 trays,
  with a vertical carousel, detachable physical latches and contact sensors.
* PX4-controlled x500 aircraft with calibrated downward 640×480, 10 Hz cameras.
* Pinned YOLOX-s ONNX image detector for person/car/truck/bus and AprilTag 3
  detection using actual rendered tray textures. Scene object metadata is not
  passed to the detector.

Stored aircraft contribute their own physical mass through latches. The chassis
mass does not include their payload mass again. Normal carrier motion uses wheel
actuation. Aircraft motion uses PX4 thrust control. No browser animation controls
the physics world.

Both trays measure 2.65 × 2.65 m. The supporting chassis is 3.05 × 3.05 m and
the deck 3.22 × 3.22 m, with a small support border around the square tray.
Four and six-wheel variants share this square footprint. Wheel cylinders stand
upright and the browser uses measured physical joint angles for their rotation.

## Units and frames

All geometry uses meters, mass kilograms, time seconds, and yaw radians. Gazebo
world coordinates are ENU. Three.js uses the same Z-up coordinates. PX4 local NED
maps to ENU as `(east, north, up) = (y, x, -z)` plus a measured per-aircraft origin.
NED yaw is `pi/2 - ENU yaw`. Camera optical `(right, down, forward)` maps into the
aircraft body frame as `(-down, -right, -forward)`; the camera sits 0.08 m below the
body origin. Images are matched to the closest measured pose, with a maximum
accepted synchronization error of 0.25 simulation seconds.

Trays use tag36h11 IDs 1–8. Odd aircraft occupy the upper level and even aircraft
the lower level. Printed texture size is 0.38 m with a white border; the AprilTag
detection corner square is 0.304 m. Initial recovery uses carrier/tray telemetry;
final alignment requires the assigned tag from current camera pixels. Docking
requires contact with the assigned tray, low velocity, stable contact, PX4 landed
status, confirmed disarming and latch confirmation. The original lower tray
recovers first, moves down, then the original upper tray recovers. Tray access
requires measured actuator positions at the indexed endpoint.

The four bays pair UAV01/02, UAV03/04, UAV05/06 and UAV07/08. The odd IDs belong
to the original upper tray; even IDs belong to the original lower tray. Both
rigid trays remain level on a vertical circulation path driven by coupled physical
horizontal and vertical prismatic joints. This models guided carousel carriages,
not a flexible belt or detailed transmission. Partial allocations are supported:
undeployed aircraft remain latched while their complete tray moves. Indexing
requires a stopped carrier, locked stored aircraft and clear flight corridors.

Landing uses tag displacement relative to the camera, rotated into ENU and applied
as a displacement in the PX4 estimator frame. It does not subtract a Gazebo tag
position from a PX4 position estimate. This corrects the UAV05 frame-bias fault.
Native landing starts from a centered, fresh tag observation before the marker
fills the camera image. The existing tag-age, contact and disarm gates remain.

Two object-detector workers prioritize searching aircraft. Search can confirm a
visible target during climb once the aircraft clears the rack. High-confidence
candidates need two distinct frames; other candidates need three. Other drones
observing targets no longer block confirmation. Detection still requires actual
camera visibility and suitable image evidence; targets outside the field of view
or behind buildings cannot be identified merely because they lie in the orbit.
Confirmation follows the nearest continuing candidate rather than switching to a
distant person whenever their confidence scores exchange rank. Cameras deactivate
while returning aircraft wait in their holding ring, reactivate for landing, and
deactivate after docking. Opening a browser camera preview adds its own sensor
demand; closing it releases only that demand and leaves mission perception active.

## Configuration and isolation

Mission schema version is 1. Backend validation rejects duplicate or unknown
aircraft, invalid units/ranges and route segments through building clearance zones.
Each aircraft may be assigned to one stop in a mission. Zero-deployment stops are
valid. The current deployed group must recover before driving to the next stop.
Stop overrides take precedence over mission defaults for target class, search
timeout and no-target duration; remaining parameters come from the mission.
The UI accepts seconds or minutes and stores durations in seconds.

Saved configuration is `missions/current.json`; exports use the same schema.
Logs and run evidence are under `artifacts/`. Runtime files are under `.runtime/`.
PX4's startup scripts split paths containing spaces, so each owned transient
rootfs is created in a space-free `/tmp/fieldlab-sitl-*` folder. Native flight logs
are archived here before that temporary directory is removed. Logging uses an
armed-only flight profile in each owned PX4 rootfs. Disposable native archives are pruned oldest
first after reset to a default total budget of 512 MiB; set FIELDLAB_ARCHIVE_MB
before starting the server to change it. Small mission JSONL records and validation
reports are preserved. This quota covers archived native logs, not an ongoing
flight, diagnostics retained elsewhere, or all project storage.

The city covers 240 × 240 m, with 25 buildings and an eight-street grid. Defaults
are 18 people and 10 parked vehicles; the lighter open-field option remains.
Route coordinates are meters from the map center, within −108 to +108 m.

Gateway binding is localhost. ROS domain 93, XRCE UDP 8889 and Gazebo partition
`fieldlab-independent-93` keep this simulator separate from other projects.
Do not initialize two Fieldlab runtimes at once. Operational cameras are activated
on mission demand; optional browser previews are throttled independently.
Internet sharing starts a separate gateway on localhost port 8766 and an outbound
tunnel to it. Opening, closing or restarting a link does not restart a live flight. Remote API,
camera, model asset and WebSocket access require a signed, expiring session; commands
and live connections require the same origin as the active public hostname.

## Validation and current limitations

This is an implementation under integration validation. A frontend build or a
state transition is not proof of a complete physical mission. Consult
`VALIDATION.md` and the JSON evidence under `artifacts/` for the current measured
results and failed attempts.

People and parked vehicles currently use static collision proxies. Buildings are
simple boxes. Ground-plane target localization assumes flat terrain. YOLOX does
not support wildlife species, and its detection quality on the reused synthetic
assets requires live measurement. The initial docking scope keeps the UGV
stationary during recovery. Broad obstacle avoidance, moving traffic, target-loss
tracking and the full one/two/four/eight-camera performance campaign require
further implementation or validation; the current UI must not be interpreted as
proof those gates have passed.

Earlier sliding-tray validation remains historical evidence. The carousel and
relative-image landing controller have their own current validation results in
`VALIDATION.md`; do not treat previous sliding-tray flights as carousel acceptance.

```bash
source scripts/environment.sh
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/validate_mission.py --drones 1
```

The validation script owns its simulator children, records authoritative
telemetry and camera images, and stops only those children when it finishes.
