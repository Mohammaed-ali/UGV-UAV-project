"""Isolated ROS 2 connection to the pinned PX4 fleet; no original-workspace imports."""
import math,time,threading,socket,struct
from .config import enu_to_ned,ned_to_enu

def topic(did,direction,name,cls):
    version=getattr(cls,'MESSAGE_VERSION',0)
    return f'/{did}/fmu/{direction}/{name}'+(f'_v{version}' if version else '')

def gcs_heartbeat(sequence):
    payload=struct.pack('<IBBBBB',0,6,8,0,4,3)
    header=bytes([9,sequence%256,255,190,0]);crc=0xffff
    for b in header+payload+bytes([50]):
        tmp=b^(crc&255);tmp=(tmp^(tmp<<4))&255;crc=((crc>>8)^(tmp<<8)^(tmp<<3)^(tmp>>4))&65535
    return b'\xfe'+header+payload+struct.pack('<H',crc)

class Fleet:
    def __init__(self,ids,gazebo):
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data
        from px4_msgs.msg import VehicleLocalPosition,VehicleStatus,VehicleLandDetected,BatteryStatus,VehicleCommandAck,OffboardControlMode,TrajectorySetpoint,VehicleCommand
        if not rclpy.ok():rclpy.init()
        self.rclpy=rclpy;self.node=Node('fieldlab_fleet');self.gazebo=gazebo;self.ids=ids;self.data={d:{} for d in ids};self.goals={};self.origins={};self.pubs={};self.last_command={};self.commands=[];self.running=True
        self.OffboardControlMode=OffboardControlMode;self.TrajectorySetpoint=TrajectorySetpoint;self.VehicleCommand=VehicleCommand
        for did in ids:
            self.pubs[did]={}
            for n,c in [('offboard_control_mode',OffboardControlMode),('trajectory_setpoint',TrajectorySetpoint),('vehicle_command',VehicleCommand)]:self.pubs[did][n]=self.node.create_publisher(c,topic(did,'in',n,c),10)
            for n,c in [('vehicle_local_position',VehicleLocalPosition),('vehicle_status',VehicleStatus),('vehicle_land_detected',VehicleLandDetected),('battery_status',BatteryStatus),('vehicle_command_ack',VehicleCommandAck)]:self.node.create_subscription(c,topic(did,'out',n,c),lambda m,d=did,k=n:self.receive(d,k,m),qos_profile_sensor_data)
        self.node.create_timer(.05,self.stream);self.thread=threading.Thread(target=self.spin,daemon=True);self.thread.start()
        self.socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.sequence=0;self.last_gcs=0
    def receive(self,did,kind,msg):
        d=self.data[did];d[kind]=msg;d[kind+'_at']=time.monotonic()
        if kind=='vehicle_command_ack':
            for command in reversed(self.commands):
                if command['drone']==did and command['command']==msg.command and command.get('result') is None:
                    command['result']=int(msg.result);command['ack_at']=time.monotonic();break
        if kind=='vehicle_local_position' and msg.xy_valid and msg.z_valid and did not in self.origins:
            p=self.gazebo.poses.get(did)
            if p:self.origins[did]=[a-b for a,b in zip(p['position'],ned_to_enu([msg.x,msg.y,msg.z]))]
    def spin(self):
        while self.running:
            self.rclpy.spin_once(self.node,timeout_sec=.05)
    def status(self,did):
        d=self.data.get(did,{});v=d.get('vehicle_status');p=d.get('vehicle_local_position');l=d.get('vehicle_land_detected');b=d.get('battery_status')
        fresh=time.monotonic()-d.get('vehicle_local_position_at',0)<2.5 and time.monotonic()-d.get('vehicle_status_at',0)<5
        position=[a+b for a,b in zip(ned_to_enu([p.x,p.y,p.z]),self.origins[did])] if p is not None and did in self.origins else None
        return {'ready':bool(fresh and v and v.pre_flight_checks_pass and p.xy_valid and p.z_valid and did in self.origins),'fresh':fresh,'armed':bool(v and v.arming_state==2),'offboard':bool(v and v.nav_state==14),'landed':bool(l and l.landed),'position':position,'velocity':ned_to_enu([p.vx,p.vy,p.vz]) if p else [0,0,0],'battery':round(b.remaining*100,1) if b and b.remaining>=0 else None,'mode':v.nav_state if v else None,'age':round(time.monotonic()-d.get('vehicle_local_position_at',time.monotonic()),2),'last_ack':{'command':int(d['vehicle_command_ack'].command),'result':int(d['vehicle_command_ack'].result)} if 'vehicle_command_ack' in d else None}
    def command(self,did,command,p1=0.,p2=0.):
        key=(did,command,p1,p2);now=time.monotonic()
        if now-self.last_command.get(key,0)<1:return
        msg=self.VehicleCommand();msg.timestamp=self.node.get_clock().now().nanoseconds//1000;msg.command=command;msg.param1=float(p1);msg.param2=float(p2);msg.target_system=int(did[-2:]);msg.target_component=1;msg.source_system=255;msg.source_component=1;msg.from_external=True
        self.commands.append({'drone':did,'command':command,'param1':p1,'param2':p2,'sent_at':now,'result':None})
        if len(self.commands)>1000:self.commands=self.commands[-1000:]
        self.pubs[did]['vehicle_command'].publish(msg);self.last_command[key]=now
    def goal(self,did,position,yaw=0.):
        if did not in self.ids:return
        previous=self.goals.get(did)
        self.goals[did]={'position':list(position),'yaw':yaw,'since':previous['since'] if previous else time.monotonic()}
    def launch(self,did):
        g=self.goals.get(did)
        if g and time.monotonic()-g['since']>1.2:
            self.command(did,176,1,6)
            self.command(did,400,1)
    def disarm(self,did):self.command(did,400,0)
    def stop_control(self,did):self.goals.pop(did,None)
    def stream(self):
        if not hasattr(self,'socket'):return
        if time.monotonic()-self.last_gcs>1:
            heartbeat=gcs_heartbeat(self.sequence);self.sequence+=1;self.last_gcs=time.monotonic()
            for did in self.ids:self.socket.sendto(heartbeat,('127.0.0.1',18570+int(did[-2:])-1))
        for did,g in list(self.goals.items()):
            if did not in self.origins:continue
            if not self.status(did)['fresh']:continue
            stamp=self.node.get_clock().now().nanoseconds//1000
            h=self.OffboardControlMode();h.timestamp=stamp;h.position=True;self.pubs[did]['offboard_control_mode'].publish(h)
            p=self.TrajectorySetpoint();p.timestamp=stamp;p.position=enu_to_ned([a-b for a,b in zip(g['position'],self.origins[did])]);p.velocity=[math.nan]*3;p.acceleration=[math.nan]*3;p.jerk=[math.nan]*3;p.yaw=math.pi/2-g['yaw'];p.yawspeed=math.nan;self.pubs[did]['trajectory_setpoint'].publish(p)
    def close(self):
        self.running=False;self.thread.join(timeout=2);self.node.destroy_node();self.socket.close()
