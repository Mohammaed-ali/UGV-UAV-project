"""Deterministic closed-loop waypoint interpolation for a visual dummy target."""
import math


def waypoint_position(waypoints, speed_mps, elapsed_s):
    if len(waypoints) < 2 or speed_mps <= 0 or elapsed_s < 0:
        raise ValueError('motion needs two waypoints, positive speed and nonnegative time')
    points = [tuple(map(float, point)) for point in waypoints]
    if any(len(point) != 2 or not all(math.isfinite(v) for v in point) for point in points):
        raise ValueError('invalid waypoint')
    segments = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        length = math.dist(start, end)
        if length > 0:
            segments.append((start, end, length))
    total = sum(length for _, _, length in segments)
    if total <= 0:
        raise ValueError('all waypoints are the same')
    along = elapsed_s * speed_mps % total
    for start, end, length in segments:
        if along <= length:
            ratio = along / length
            return (start[0] + ratio * (end[0] - start[0]),
                    start[1] + ratio * (end[1] - start[1]))
        along -= length
    return segments[-1][1]
