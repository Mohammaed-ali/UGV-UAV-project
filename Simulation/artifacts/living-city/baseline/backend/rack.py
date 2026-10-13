"""Two level, four-place carousel. Goals actuate Gazebo joints; telemetry gates access."""
import math

UPPER_Z=2.25
LOWER_Z=.78
CENTER_Z=(UPPER_Z+LOWER_Z)/2
HALF_HEIGHT=(UPPER_Z-LOWER_Z)/2
RADIUS=2.15
PAD_Z=.075
BASE_Z=.74
PITCH=.68
CHASSIS_SIZE=3.05
DECK_SIZE=3.22
WHEEL_X=1.10
WHEEL_Y=1.66

def initial_height(level):
    return UPPER_Z if level=='upper' else LOWER_Z

def destinations(angle):
    return {level:{'y':sign*RADIUS*math.sin(angle),
                   'z':CENTER_Z+sign*HALF_HEIGHT*math.cos(angle)-initial_height(level)}
            for level,sign in [('upper',1),('lower',-1)]}

class Carousel:
    def __init__(self):
        self.angle=0.;self.target_angle=0.;self.active='upper';self.requested='upper'
        self.moving=False;self.settled=0.;self.elapsed=0.;self.error=None

    def measured(self,gz,level):
        joints=gz.joints if gz else {}
        return {'y':joints.get(f'carousel_{level}_y_joint',0.),
                'z':initial_height(level)+joints.get(f'carousel_{level}_z_joint',0.)}

    def ready(self,gz,level):
        if not gz or self.moving or self.error or self.active!=level:return False
        desired=destinations(self.target_angle)
        return all(f'carousel_{tray}_{axis}_joint' in gz.joints and abs(gz.joints[f'carousel_{tray}_{axis}_joint']-value)<.045
                   for tray,values in desired.items() for axis,value in values.items())

    def request(self,level,can_move):
        if level==self.active or self.moving or self.error or not can_move:return False
        self.requested=level;self.target_angle=self.angle+math.pi
        self.moving=True;self.settled=0.;self.elapsed=0.
        return True

    def tick(self,gz,dt):
        if self.error:return
        if self.moving:
            self.elapsed+=dt
            if self.elapsed>80:
                self.error='Carousel could not reach its indexed position';return
            expected=destinations(self.angle)
            following=max(abs(gz.joints.get(f'carousel_{level}_{axis}_joint',0.)-value)
                          for level,values in expected.items() for axis,value in values.items())
            # Stop advancing the carriage path if the physical joints lag.
            if following<.12:self.angle=min(self.target_angle,self.angle+.16*dt)
        goals=destinations(self.angle)
        for level,values in goals.items():
            for axis,value in values.items():gz.carousel(level,axis,value)
        if self.moving and abs(self.angle-self.target_angle)<1e-6:
            at_end=all(abs(gz.joints.get(f'carousel_{level}_{axis}_joint',0.)-value)<.035
                       for level,values in goals.items() for axis,value in values.items())
            self.settled=self.settled+dt if at_end else 0.
            if self.settled>.8:self.moving=False;self.active=self.requested

    def snapshot(self,gz):
        return {'active_level':self.active,'requested_level':self.requested,'moving':self.moving,
                'phase':'indexing' if self.moving else 'locked','angle':self.angle,'error':self.error,
                'trays':{level:self.measured(gz,level) for level in ('upper','lower')}}
