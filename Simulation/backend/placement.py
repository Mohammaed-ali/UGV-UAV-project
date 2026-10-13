"""Physical footprint clearance for deterministic static city placement."""
import math
from .rack import WHEEL_X,WHEEL_Y,RADIUS

# Include the reused visual meshes, which exceed the simple collision proxies.
ACTOR_RADIUS={'person':.8,'car':2.5,'truck':4.,'bus':4.5}
TRAVEL_CLEARANCE=math.hypot(WHEEL_X+.38,WHEEL_Y+.15)+1.
STOP_CLEARANCE=math.hypot(1.325,RADIUS+1.325)+.8

def segment_distance(x,y,a,b):
    dx,dy=b.x-a.x,b.y-a.y;length=dx*dx+dy*dy
    t=max(0.,min(1.,((x-a.x)*dx+(y-a.y)*dy)/length)) if length else 0.
    return math.hypot(x-a.x-t*dx,y-a.y-t*dy)

def route_clear(x,y,radius,mission):
    points=[mission.start,*mission.stops]
    return (all(segment_distance(x,y,a,b)>TRAVEL_CLEARANCE+radius for a,b in zip(points,points[1:]))
            and all(math.hypot(x-p.x,y-p.y)>STOP_CLEARANCE+radius for p in points))

def placement_clear(x,y,kind,mission,objects,roads):
    radius=ACTOR_RADIUS[kind]
    if abs(x)+radius>115 or abs(y)+radius>115 or not route_clear(x,y,radius,mission):return False
    for obj in objects:
        if obj['kind']=='building':
            dx=max(0,abs(x-obj['x'])-obj['sx']/2);dy=max(0,abs(y-obj['y'])-obj['sy']/2)
            if math.hypot(dx,dy)<radius+.6:return False
        elif math.hypot(x-obj['x'],y-obj['y'])<radius+ACTOR_RADIUS[obj['kind']]+.4:return False
    # People stand on the verge/sidewalk, including at street intersections.
    if kind=='person' and any(abs(x-r['x'])<r['sx']/2+radius+.2 and abs(y-r['y'])<r['sy']/2+radius+.2 for r in roads):return False
    return True
