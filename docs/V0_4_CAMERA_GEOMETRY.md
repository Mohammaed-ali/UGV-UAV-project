# PX4 down-camera map localization

The camera profile uses the **pinned** PX4 `x500_mono_cam_down` Gazebo model.
The SDF mounts `mono_cam/camera_link` approximately 0.10 m above `base_link`
with +90° pitch about body Y. The Gazebo camera looks along its local +X axis;
image right is camera -Y and image down is camera -Z. Its actual live
CameraInfo is 1280×960 with `fx≈fy≈539.94`, `cx=640`, `cy=480`.

The ROS shared map uses ENU (X east, Y north, Z up). The PX4 attitude message
uses a Hamilton quaternion in `(w,x,y,z)` order rotating body FRD to earth NED.
The conversion to ROS body FLU in map ENU is:

```text
q(ENU <- FLU) = q(ENU <- NED) * q(NED <- FRD) * q(FRD <- FLU)
```

`camera_geometry.py` computes a pixel ray from CameraInfo, rotates it through
the SDF camera mount and the measured PX4 attitude, translates it by the
current DroneState map position, and intersects the ray with a configured
ground plane (`z=0` by default). Horizontal/upward rays and intersections
behind the camera are rejected. The output `Detection.position_world` is map
ENU, with its header stamped from the actual image and `frame_id=map`.

The detector accepts position, attitude and CameraInfo only while freshly
received (default receipt age limits 0.5/0.5/5 s). ROS image stamps use Gazebo
simulation time, while PX4 attitude stamps are boot-relative and the existing
DroneState uses the ROS node clock. These clocks have not been synchronized for
exact pose interpolation. Receipt-age limits and a conservative configurable
2 m localization sigma bound the demo's interpretation; they are not a claim
of exact sensor-time alignment. The current camera path is validated for one
PX4 vehicle and the flat ground in `wildlife_px4.sdf`.

Unit checks cover center/side pixels, yaw, vehicle and camera pitch, altitude,
invalid rays and PX4/ROS frame conversion. A live image-to-mission run is
recorded in `docs/validation/px4_real_camera_mission.json`.
