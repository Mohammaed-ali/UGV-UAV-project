"""Pinhole projection using the actual V0.4 Gazebo camera frame."""
import math
from itertools import product
import numpy as np


def quaternion(roll, pitch, yaw):
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return [sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy]


def rotation(q):
    x, y, z, w = np.asarray(q, float) / np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def project_points(points, pose, cam):
    p = (np.asarray(points) - pose['position']) @ rotation(pose['quaternion'])
    valid = p[:, 0] >= cam['near']
    if not np.all(valid):
        return None
    return np.column_stack((cam['cx'] - cam['fx'] * p[:, 1] / p[:, 0],
                            cam['cy'] - cam['fy'] * p[:, 2] / p[:, 0]))


def project_box(bounds, object_pose, camera_pose, cam):
    corners = np.array(list(product(*zip(bounds['min'], bounds['max']))))
    world = corners @ rotation(object_pose['quaternion']).T + object_pose['position']
    uv = project_points(world, camera_pose, cam)
    if uv is None:
        return None
    return [float(uv[:, 0].min()), float(uv[:, 1].min()),
            float(uv[:, 0].max()), float(uv[:, 1].max())]


def ground_ray(u, v, pose, cam, ground_z=0):
    ray = rotation(pose['quaternion']) @ np.array([1, -(u-cam['cx'])/cam['fx'], -(v-cam['cy'])/cam['fy']])
    if ray[2] >= -1e-9:
        raise ValueError('Camera footprint has an upward ground ray')
    t = (ground_z - pose['position'][2]) / ray[2]
    if t <= 0:
        raise ValueError('Ground is behind camera')
    return np.array(pose['position']) + t * ray


def footprint(pose, cam, ground_z=0):
    return np.array([ground_ray(u, v, pose, cam, ground_z)[:2] for u,v in
                     [(0,0),(cam['width'],0),(cam['width'],cam['height']),(0,cam['height'])]])


def cross(a, b):
    return a[0]*b[1]-a[1]*b[0]


def footprint_radius(center, direction, polygon, camera_pose, cam):
    distances = []
    for a,b in zip(polygon, np.roll(polygon,-1,axis=0)):
        edge = b-a
        den = cross(direction,edge)
        if abs(den) > 1e-10:
            t, u = cross(a-center,edge)/den, cross(a-center,direction)/den
            if t > 0 and -1e-8 <= u <= 1+1e-8:
                distances.append(t)
    # Enforce Euclidean far clipping as a conservative usable-footprint bound.
    offset = np.asarray(center)-np.asarray(camera_pose['position'][:2])
    h = camera_pose['position'][2]-camera_pose.get('ground_reference_z',0)
    b = float(np.dot(offset,direction))
    disc = b*b+cam['far']**2-h*h-float(np.dot(offset,offset))
    if disc <= 0 or not distances:
        raise ValueError('Empty usable camera footprint')
    return min(min(distances), -b+math.sqrt(disc))


def clip_box(box, cam):
    if box is None or len(box)!=4 or not all(math.isfinite(v) for v in box):
        return None
    x1,y1,x2,y2=box
    if x2<=x1 or y2<=y1:
        return None
    out=[max(0.,x1),max(0.,y1),min(float(cam['width']),x2),min(float(cam['height']),y2)]
    return out if out[2]>out[0] and out[3]>out[1] else None


def yolo_box(box, cam):
    b = clip_box(box,cam)
    if b is None:
        raise ValueError('Invalid or outside bbox')
    x1,y1,x2,y2=b
    return [(x1+x2)/2/cam['width'],(y1+y2)/2/cam['height'],(x2-x1)/cam['width'],(y2-y1)/cam['height']]


def iou(a,b):
    if a is None or b is None:
        return 0.
    intersect=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersect
    return intersect/union if union>0 else 0.


def distance_category(value,bands):
    for name,(low,high) in bands.items():
        if low<=value<high or value==high==1:
            return name
    return 'outside'
