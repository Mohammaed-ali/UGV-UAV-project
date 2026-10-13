"""Measured-speed damping for the loaded carrier's city approach and turns."""
import math

def city_drive(distance,heading_error,speed,yaw_rate,maximum_speed):
    # Brake before reaching the bay, using measured body speed. A loaded skid-
    # steer carrier takes distance to decelerate; distance alone caused overshoot.
    remaining=max(0.,distance-.35)
    linear=min(maximum_speed,remaining*.5,math.sqrt(2*.45*remaining))*max(0.,math.cos(heading_error))
    braking=abs(speed)*.5+speed*speed/(2*.45)
    if braking>max(0.,distance-.45):linear=min(linear,remaining*.3)
    if abs(heading_error)>.25:linear=0.
    angular=max(-.35,min(.35,heading_error*.7-yaw_rate*.9))
    return linear,angular
