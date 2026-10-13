from __future__ import annotations
from collections import deque
from threading import RLock
import math,time
import numpy as np

def simstamp(header):return header.stamp.sec+header.stamp.nsec*1e-9

def quaternion_matrix(q):
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def pose_dict(p):
    q=p.orientation
    return {'position':[p.position.x,p.position.y,p.position.z],'quaternion':[q.x,q.y,q.z,q.w],'yaw':math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))}

class GazeboBridge:
    def __init__(self):
        from gz.transport13 import Node
        from gz.msgs10.pose_v_pb2 import Pose_V
        from gz.msgs10.world_stats_pb2 import WorldStatistics
        from gz.msgs10.odometry_pb2 import Odometry
        from gz.msgs10.model_pb2 import Model
        from gz.msgs10.contacts_pb2 import Contacts
        from gz.msgs10.stringmsg_pb2 import StringMsg
        from gz.msgs10.image_pb2 import Image
        self.node=Node();self.lock=RLock();self.poses={};self.histories={};self.images={};self.camera_packets={};self.joints={};self.contacts={};self.latches={};self.callbacks=[];self.publishers={}
        self.sim_time=0.;self.rtf=0.;self.paused=False;self.received=0.;self.odom=None;self.image_counts={}
        self.sub(Pose_V,'/world/fieldlab/pose/info',self.pose_cb)
        self.sub(WorldStatistics,'/world/fieldlab/stats',self.stats_cb)
        self.sub(Odometry,'/fieldlab/carrier/odom',self.odom_cb)
        self.sub(Model,'/fieldlab/carrier/joints',self.joint_cb)
        for i in range(1,9):
            did=f'uav{i:02d}'
            self.sub(Contacts,f'/fieldlab/trays/{did}/contact',lambda msg,d=did:self.contact_cb(d,msg))
            self.sub(StringMsg,f'/fieldlab/trays/{did}/latch',lambda msg,d=did:self.latch_cb(d,msg))
            # Subscribe only on demand; sensor consumers, not the browser viewport, select cameras.
        self.Image=Image;self.enabled_cameras=set();self.camera_consumers={};self.preview_id=None

    def sub(self,cls,topic,cb):self.callbacks.append(cb);self.node.subscribe(cls,topic,cb)
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
    def stats_cb(self,msg):
        with self.lock:self.sim_time=msg.sim_time.sec+msg.sim_time.nsec/1e9;self.rtf=msg.real_time_factor;self.paused=msg.paused;self.received=time.monotonic()
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
    def image_cb(self,did,msg):
        if not msg.width or not msg.height:return
        import cv2
        stamp=simstamp(msg.header)
        buf=np.frombuffer(msg.data,dtype=np.uint8)
        try:
            rgb=buf.reshape((msg.height,msg.step))[:,:msg.width*3].reshape((msg.height,msg.width,3))
        except ValueError:return
        with self.lock:
            history=list(self.histories.get(did,[]));near=min(history,key=lambda p:abs(p['time']-stamp)) if history else None
            packet={'image':cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),'time':stamp,'pose':near,'sync_error':abs(near['time']-stamp) if near else 1e9,'received':time.monotonic()}
            self.camera_packets[did]=packet;self.image_counts[did]=self.image_counts.get(did,0)+1
    def publish(self,topic,msg):
        if topic not in self.publishers:self.publishers[topic]=self.node.advertise(topic,type(msg))
        self.publishers[topic].publish(msg)
    def drive(self,speed,turn):
        from gz.msgs10.twist_pb2 import Twist
        t=Twist();t.linear.x=float(speed);t.angular.z=float(turn);self.publish('/fieldlab/carrier/cmd_vel',t)
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
