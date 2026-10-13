from __future__ import annotations
from collections import deque
from threading import RLock
import math,time
import numpy as np

def simstamp(header):return header.stamp.sec+header.stamp.nsec*1e-9

def quaternion_matrix(q):
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def matrix_quaternion(matrix):
    # Stable matrix conversion via OpenCV Rodrigues, including rotations near pi.
    import cv2
    vector=cv2.Rodrigues(matrix)[0].reshape(3);angle=float(np.linalg.norm(vector))
    if angle<1e-8:return [0.,0.,0.,1.]
    axis=vector/angle;return [*map(float,axis*math.sin(angle/2)),math.cos(angle/2)]

def pose_dict(p):
    q=p.orientation
    return {'position':[p.position.x,p.position.y,p.position.z],'quaternion':[q.x,q.y,q.z,q.w],'yaw':math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))}

class GazeboBridge:
    def __init__(self,living_city=False):
        from gz.transport13 import Node
        from gz.msgs10.pose_v_pb2 import Pose_V
        from gz.msgs10.world_stats_pb2 import WorldStatistics
        from gz.msgs10.clock_pb2 import Clock
        from gz.msgs10.odometry_pb2 import Odometry
        from gz.msgs10.model_pb2 import Model
        from gz.msgs10.contacts_pb2 import Contacts
        from gz.msgs10.stringmsg_pb2 import StringMsg
        from gz.msgs10.image_pb2 import Image
        self.node=Node();self.lock=RLock();self.poses={};self.histories={};self.images={};self.camera_packets={};self.joints={};self.contacts={};self.latches={};self.callbacks=[];self.publishers={}
        self.sim_time=0.;self.rtf=0.;self.paused=False;self.received=0.;self.odom=None;self.image_counts={};self.city_contacts=[];self.actor_contacts=[]
        self.sub(Clock,'/world/fieldlab/clock',self.clock_cb,20)
        self.sub(Pose_V,'/world/fieldlab/pose/info',self.pose_cb,30)
        self.sub(WorldStatistics,'/world/fieldlab/stats',self.stats_cb,20)
        self.sub(Odometry,'/fieldlab/carrier/odom',self.odom_cb)
        self.sub(Model,'/fieldlab/carrier/joints',self.joint_cb,30)
        self.sub(Contacts,'/fieldlab/city/contacts',self.city_contact_cb)
        for i in range(1,9):
            did=f'uav{i:02d}'
            self.sub(Contacts,f'/fieldlab/trays/{did}/contact',lambda msg,d=did:self.contact_cb(d,msg))
            self.sub(StringMsg,f'/fieldlab/trays/{did}/'+('latch_measured' if living_city else 'latch'),lambda msg,d=did:self.latch_cb(d,msg))
            # Subscribe only on demand; sensor consumers, not the browser viewport, select cameras.
        self.Image=Image;self.enabled_cameras=set();self.camera_consumers={};self.preview_id=None

    def sub(self,cls,topic,cb,rate=None):
        self.callbacks.append(cb)
        if rate is None:self.node.subscribe(cls,topic,cb)
        else:
            from gz.transport13 import SubscribeOptions
            options=SubscribeOptions();options.msgs_per_sec=rate
            self.node.subscribe(cls,topic,cb,options)

    def camera(self,did,enabled=True,consumer='mission'):
        consumers=self.camera_consumers.setdefault(did,set())
        if enabled:consumers.add(consumer)
        else:consumers.discard(consumer)
        if consumers and did not in self.enabled_cameras:
            self.sub(self.Image,f'/fieldlab/{did}/camera',lambda msg,d=did:self.image_cb(d,msg));self.enabled_cameras.add(did)
        elif not consumers and did in self.enabled_cameras:
            self.node.unsubscribe(f'/fieldlab/{did}/camera');self.enabled_cameras.discard(did)
            with self.lock:self.camera_packets.pop(did,None)

    def preview(self,did):
        if self.preview_id and self.preview_id!=did:self.camera(self.preview_id,False,'preview')
        self.preview_id=did
        if did:self.camera(did,True,'preview')

    def pose_cb(self,msg):
        stamp=simstamp(msg.header)
        with self.lock:
            for p in msg.pose:
                if p.name=='carrier' or p.name.startswith('uav') or p.name.startswith(('person_','vehicle_')):
                    data=pose_dict(p);data['time']=stamp;data['received']=time.monotonic();self.poses[p.name]=data
                    self.histories.setdefault(p.name,deque(maxlen=150)).append(data)
    def clock_cb(self,msg):
        with self.lock:self.sim_time=max(self.sim_time,msg.sim.sec+msg.sim.nsec/1e9);self.received=time.monotonic()
    def stats_cb(self,msg):
        # A delayed statistics message cannot rewind the camera-age clock.
        with self.lock:self.sim_time=max(self.sim_time,msg.sim_time.sec+msg.sim_time.nsec/1e9);self.rtf=msg.real_time_factor;self.paused=msg.paused;self.received=time.monotonic()
    def odom_cb(self,msg):
        with self.lock:self.odom={'speed':msg.twist.linear.x,'yaw_rate':msg.twist.angular.z,'received':time.monotonic()}
    def joint_cb(self,msg):
        with self.lock:
            for j in msg.joint:self.joints[j.name]=j.axis1.position
    def contact_cb(self,did,msg):
        touching=any(did in c.collision1.name.replace('/','::').split('::') or did in c.collision2.name.replace('/','::').split('::') for c in msg.contact)
        with self.lock:self.contacts[did]=(touching,simstamp(msg.header))
    def latch_cb(self,did,msg):
        with self.lock:self.latches[did]=msg.data
    def city_contact_cb(self,msg):
        for c in msg.contact:
            names=sorted([c.collision1.name,c.collision2.name])
            if any('carrier' in n for n in names) and any('person_' in n or 'vehicle_' in n for n in names):
                with self.lock:
                    row={'time':simstamp(msg.header),'collisions':names}
                    if not self.city_contacts or self.city_contacts[-1]['collisions']!=names or row['time']-self.city_contacts[-1]['time']>1:
                        self.city_contacts.append(row);self.city_contacts=self.city_contacts[-100:]
            elif all('person_' in n or 'vehicle_' in n for n in names):
                with self.lock:
                    row={'time':simstamp(msg.header),'collisions':names}
                    if not self.actor_contacts or self.actor_contacts[-1]['collisions']!=names or row['time']-self.actor_contacts[-1]['time']>1:
                        self.actor_contacts.append(row);self.actor_contacts=self.actor_contacts[-100:]
    def image_cb(self,did,msg):
        if not msg.width or not msg.height:return
        import cv2
        stamp=simstamp(msg.header)
        buf=np.frombuffer(msg.data,dtype=np.uint8)
        try:
            rgb=buf.reshape((msg.height,msg.step))[:,:msg.width*3].reshape((msg.height,msg.width,3))
        except ValueError:return
        frame=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
        with self.lock:
            history=list(self.histories.get(did,[]));near=min(history,key=lambda p:abs(p['time']-stamp)) if history else None
            packet={'image':frame,'time':stamp,'pose':near,'sync_error':abs(near['time']-stamp) if near else 1e9,'received':time.monotonic()}
            self.camera_packets[did]=packet;self.image_counts[did]=self.image_counts.get(did,0)+1
    def publish(self,topic,msg):
        if topic not in self.publishers:self.publishers[topic]=self.node.advertise(topic,type(msg))
        self.publishers[topic].publish(msg)
    def drive(self,speed,turn):
        from gz.msgs10.twist_pb2 import Twist
        t=Twist();t.linear.x=float(speed);t.angular.z=float(turn);self.publish('/fieldlab/carrier/cmd_vel',t)
    def actor_velocity(self,name,speed,turn):
        from gz.msgs10.twist_pb2 import Twist
        t=Twist();t.linear.x=float(speed);t.angular.z=float(turn)
        self.publish(f'/fieldlab/city/{name}/cmd_vel',t)
    def actor_route(self,name,points):
        from gz.msgs10.pose_v_pb2 import Pose_V
        from gz.msgs10.stringmsg_pb2 import StringMsg
        if not hasattr(self,'actor_route_versions'):self.actor_route_versions={}
        if name not in self.actor_route_versions:
            self.actor_route_versions[name]=''
            self.sub(StringMsg,f'/fieldlab/city/{name}/route_applied',lambda msg,n=name:self.actor_route_versions.__setitem__(n,msg.data))
        version=time.monotonic_ns();route=Pose_V();route.header.stamp.sec=version
        for x,y in points:
            p=route.pose.add();p.position.x=x;p.position.y=y;p.orientation.w=1.
        deadline=time.monotonic()+2.
        while time.monotonic()<deadline:
            self.publish(f'/fieldlab/city/{name}/route',route)
            time.sleep(.06)
            if self.actor_route_versions.get(name)==str(version):return
        raise ValueError('The native actor path did not acknowledge this change.')
    def place_actor(self,name,x,y,yaw):
        from gz.msgs10.pose_pb2 import Pose
        from gz.msgs10.boolean_pb2 import Boolean
        p=Pose(name=name);p.position.x=x;p.position.y=y;p.position.z=.02;p.orientation.z=math.sin(yaw/2);p.orientation.w=math.cos(yaw/2)
        # Keep transport waits short; success is the measured physical pose,
        # including when the request reply is delayed behind Python callbacks.
        self.node.request('/world/fieldlab/set_pose',p,Pose,Boolean,50)
        deadline=time.monotonic()+1.5
        while time.monotonic()<deadline:
            measured=self.poses.get(name)
            if measured and math.dist(measured['position'][:2],[x,y])<.1 and abs((measured['yaw']-yaw+math.pi)%(2*math.pi)-math.pi)<.1:return
            time.sleep(.03)
        raise ValueError('The physics world did not confirm this placement. Try again.')

    def tray(self,did,extension):
        from gz.msgs10.double_pb2 import Double
        self.publish(f'/fieldlab/trays/{did}/position',Double(data=float(extension)))
    def carousel(self,level,axis,position):
        from gz.msgs10.double_pb2 import Double
        self.publish(f'/fieldlab/carousel/{level}/{axis}',Double(data=float(position)))
    def latch(self,did,attach):
        from gz.msgs10.empty_pb2 import Empty
        self.publish(f'/fieldlab/trays/{did}/{"attach" if attach else "detach"}',Empty())
    def pause(self,value):
        from gz.msgs10.world_control_pb2 import WorldControl
        from gz.msgs10.boolean_pb2 import Boolean
        return self.node.request('/world/fieldlab/control',WorldControl(pause=value),WorldControl,Boolean,2000)
    def close(self):
        for topic in self.node.subscribed_topics():self.node.unsubscribe(topic)
