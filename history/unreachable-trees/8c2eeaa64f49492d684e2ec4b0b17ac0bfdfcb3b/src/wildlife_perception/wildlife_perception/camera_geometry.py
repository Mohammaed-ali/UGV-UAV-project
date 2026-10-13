"""PX4 FRD/NED to Gazebo camera and ROS ENU ground-plane geometry.

The pinned x500_mono_cam_down camera looks along its +X axis. Image +u is
camera -Y and image +v is camera -Z. Its SDF mount is +0.10 m along body Z
with +90 degrees pitch about body Y. PX4 q(w,x,y,z) maps body FRD to earth
NED. The returned point is in the shared ROS ENU map frame.
"""
import math
from typing import NamedTuple


class GroundPoint(NamedTuple):
    x: float
    y: float
    z: float
    distance: float


def _unit(q):
    if len(q) != 4 or not all(math.isfinite(v) for v in q):
        raise ValueError('invalid quaternion')
    norm = math.sqrt(sum(v * v for v in q))
    if norm < 1e-9:
        raise ValueError('zero quaternion')
    return tuple(v / norm for v in q)


def _multiply(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def _rotate(q, v):
    x, y, z, w = _unit(q)
    vx, vy, vz = v
    tx, ty, tz = (2 * (y * vz - z * vy),
                  2 * (z * vx - x * vz),
                  2 * (x * vy - y * vx))
    return (vx + w * tx + y * tz - z * ty,
            vy + w * ty + z * tx - x * tz,
            vz + w * tz + x * ty - y * tx)


def px4_to_map_quaternion(q_wxyz):
    """Return xyzw rotation from ROS body FLU to ROS map ENU."""
    if len(q_wxyz) != 4:
        raise ValueError('PX4 attitude must be wxyz')
    w, x, y, z = q_wxyz
    ned_from_frd = _unit((x, y, z, w))
    s = math.sqrt(.5)
    enu_from_ned = (s, s, 0., 0.)
    frd_from_flu = (1., 0., 0., 0.)
    return _unit(_multiply(_multiply(enu_from_ned, ned_from_frd), frd_from_flu))


def ground_intersection(pixel, intrinsics, uav_position, q_wxyz,
                        mount_xyz=(0., 0., .10), mount_pitch=math.pi / 2,
                        ground_z=0.):
    """Intersect an image pixel's measured-pose ray with z=ground_z.

    intrinsics is (fx, fy, cx, cy). Return None if the ray is horizontal,
    upward, or its intersection is behind the camera.
    """
    values = (*pixel, *intrinsics, *uav_position, *mount_xyz, mount_pitch, ground_z)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('non-finite camera geometry')
    u, v = pixel
    fx, fy, cx, cy = intrinsics
    if fx <= 0 or fy <= 0:
        raise ValueError('camera focal lengths must be positive')
    ray = (1., -(u - cx) / fx, -(v - cy) / fy)
    length = math.sqrt(sum(axis * axis for axis in ray))
    ray = tuple(axis / length for axis in ray)
    body_from_camera = (0., math.sin(mount_pitch / 2), 0.,
                        math.cos(mount_pitch / 2))
    map_from_body = px4_to_map_quaternion(q_wxyz)
    body_ray = _rotate(body_from_camera, ray)
    map_ray = _rotate(map_from_body, body_ray)
    offset = _rotate(map_from_body, mount_xyz)
    camera = tuple(uav_position[i] + offset[i] for i in range(3))
    if map_ray[2] >= -1e-9:
        return None
    distance = (ground_z - camera[2]) / map_ray[2]
    if distance <= 0:
        return None
    return GroundPoint(camera[0] + distance * map_ray[0],
                       camera[1] + distance * map_ray[1],
                       ground_z, distance)
