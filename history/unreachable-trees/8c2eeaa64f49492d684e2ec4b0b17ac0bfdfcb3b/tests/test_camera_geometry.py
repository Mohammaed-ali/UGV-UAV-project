import math

import pytest

from wildlife_perception.camera_geometry import ground_intersection, px4_to_map_quaternion


INTRINSICS = (500., 500., 640., 480.)
LEVEL_NORTH = (1., 0., 0., 0.)  # PX4 FRD -> NED identity


def test_center_pixel_uses_measured_altitude_and_map_position():
    point = ground_intersection((640., 480.), INTRINSICS, (4., -3., 10.), LEVEL_NORTH)
    assert point.x == pytest.approx(4.)
    assert point.y == pytest.approx(-3.)
    assert point.z == 0.
    assert point.distance == pytest.approx(10.1)


def test_left_and_right_pixels_follow_camera_and_map_axes():
    right = ground_intersection((1140., 480.), INTRINSICS, (0., 0., 10.), LEVEL_NORTH)
    left = ground_intersection((140., 480.), INTRINSICS, (0., 0., 10.), LEVEL_NORTH)
    assert right.x == pytest.approx(10.1)
    assert left.x == pytest.approx(-10.1)
    assert right.y == pytest.approx(0.)


def test_px4_yaw_rotates_world_ray():
    yaw_east = (math.sqrt(.5), 0., 0., math.sqrt(.5))
    right = ground_intersection((1140., 480.), INTRINSICS, (0., 0., 10.), yaw_east)
    assert right.x == pytest.approx(0., abs=1e-6)
    assert right.y == pytest.approx(-10.1)


def test_camera_pitch_and_altitude_change_intersection():
    point = ground_intersection((640., 480.), INTRINSICS, (0., 0., 10.),
                                LEVEL_NORTH, mount_pitch=math.pi / 4)
    high = ground_intersection((640., 480.), INTRINSICS, (0., 0., 20.),
                               LEVEL_NORTH, mount_pitch=math.pi / 4)
    assert point.y == pytest.approx(10.1)
    assert high.y == pytest.approx(20.1)


def test_vehicle_pitch_affects_world_intersection():
    pitch = (math.cos(.1), 0., math.sin(.1), 0.)
    tilted = ground_intersection((640., 480.), INTRINSICS, (0., 0., 10.), pitch)
    level = ground_intersection((640., 480.), INTRINSICS, (0., 0., 10.), LEVEL_NORTH)
    assert abs(tilted.y - level.y) > 1.


def test_upward_and_horizontal_rays_have_no_ground_intersection():
    assert ground_intersection((640., 480.), INTRINSICS, (0., 0., 10.),
                               LEVEL_NORTH, mount_pitch=-math.pi / 2) is None
    assert ground_intersection((640., 480.), INTRINSICS, (0., 0., 10.),
                               LEVEL_NORTH, mount_pitch=0.) is None


def test_frame_conversion_and_invalid_inputs():
    q = px4_to_map_quaternion(LEVEL_NORTH)
    assert abs(q[0]) < 1e-6 and abs(q[1]) < 1e-6
    assert abs(abs(q[2]) - math.sqrt(.5)) < 1e-6
    with pytest.raises(ValueError):
        px4_to_map_quaternion((0., 0., 0., 0.))
    with pytest.raises(ValueError):
        ground_intersection((640., 480.), (0., 500., 640., 480.),
                            (0., 0., 10.), LEVEL_NORTH)
