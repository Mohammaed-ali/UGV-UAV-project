import pytest

from wildlife_simulation.target_motion import waypoint_position


WAYPOINTS = [(0., 0.), (2., 0.), (2., 2.), (0., 2.)]


def test_closed_loop_movement_is_repeatable():
    assert waypoint_position(WAYPOINTS, 1., 0.) == (0., 0.)
    assert waypoint_position(WAYPOINTS, 1., 1.) == (1., 0.)
    assert waypoint_position(WAYPOINTS, 1., 3.) == (2., 1.)
    assert waypoint_position(WAYPOINTS, 1., 8.) == (0., 0.)
    assert waypoint_position(WAYPOINTS, 1., 11.) == (2., 1.)


def test_invalid_motion_rejected():
    with pytest.raises(ValueError):
        waypoint_position([(0., 0.)], 1., 0.)
    with pytest.raises(ValueError):
        waypoint_position(WAYPOINTS, 0., 0.)
