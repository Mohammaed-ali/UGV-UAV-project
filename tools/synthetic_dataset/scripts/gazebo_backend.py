"""Owned, isolated Gazebo process and timestamp checked native sensor capture."""
from collections import OrderedDict
import base64
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
import uuid
import sys

import cv2
import numpy as np
from common import utc_now, write_json
from geometry import clip_box, iou, yolo_box
from sampling import projected_geometry
from world import write_world


def stamp(msg):
    return msg.header.stamp.sec+msg.header.stamp.nsec/1e9


def pose_dict(p):
    return {'position':[p.position.x,p.position.y,p.position.z],
            'quaternion':[p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w]}


class Gazebo:
    def __init__(self,cfg,run_dir,headless=True):
        self.cfg,self.run_dir=cfg,Path(run_dir)
        self.run_dir.mkdir(parents=True,exist_ok=True)
        # Set before constructing transport. Never change HOME or ROS settings.
        os.environ['GZ_PARTITION']='wildlife-dataset-'+uuid.uuid4().hex
        os.environ.setdefault('GZ_IP','127.0.0.1')
        os.environ['GZ_HOMEDIR']=str(self.run_dir/'gz_home')
        from gz.transport13 import Node
        from gz.msgs10.image_pb2 import Image
        from gz.msgs10.annotated_axis_aligned_2d_box_v_pb2 import AnnotatedAxisAligned2DBox_V
        from gz.msgs10.pose_v_pb2 import Pose_V
        from gz.msgs10.camera_info_pb2 import CameraInfo
        self.node=Node();self.buffers={'rgb':OrderedDict(),'boxes':OrderedDict()}
        self.worker=subprocess.Popen([sys.executable,str(Path(__file__).with_name('transport_worker.py'))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
        self.lock=threading.Lock();self.poses={};self.entity_ids={};self.pose_stamp=-1.;self.info=None;self.active=set()
        self.callbacks=[]
        def sensor_callback(key):
            def cb(msg):
                with self.lock:
                    self.buffers[key][stamp(msg)]=msg
                    while len(self.buffers[key])>32: self.buffers[key].popitem(last=False)
            return cb
        def poses(msg):
            with self.lock:
                self.poses.update({p.name:pose_dict(p) for p in msg.pose})
                self.entity_ids.update({p.name:p.id for p in msg.pose})
                self.pose_stamp=stamp(msg)
        def info(msg): self.info=msg
        for cls,topic,cb in [(Image,'/dataset/rgb',sensor_callback('rgb')),
                              (AnnotatedAxisAligned2DBox_V,'/dataset/visible',sensor_callback('boxes')),
                              (Pose_V,f"/world/{cfg['world']['name']}/pose/info",poses),
                              (CameraInfo,'/dataset/rgb/camera_info',info)]:
            self.callbacks.append(cb);self.node.subscribe(cls,topic,cb)
        world_path=self.run_dir/'world.sdf';write_world(cfg,world_path)
        command=['gz','sim','-s','-r','-v','2',str(world_path)]
        if headless: command.insert(4,'--headless-rendering')
        self.log=(self.run_dir/'gazebo.log').open('w')
        self.process=subprocess.Popen(command,stdout=self.log,stderr=self.log,start_new_session=True)
        write_json(self.run_dir/'owned_processes.json',{'generator_pid':os.getpid(),'gazebo_pgid':self.process.pid,'service_worker_pid':self.worker.pid,'partition':os.environ['GZ_PARTITION']})
        try:
            self.wait(lambda:bool(self.buffers['rgb']) and bool(self.buffers['boxes']) and 'dataset_rig' in self.poses and self.info is not None,'sensor startup')
            self.wait(lambda:all(f"/world/{cfg['world']['name']}/{name}" in self.node.service_list() for name in ('set_pose_vector','light_config')),'service discovery')
            cam=cfg['camera'];intrinsics=list(self.info.intrinsics.k)
            if self.info.width!=cam['width'] or self.info.height!=cam['height'] or len(intrinsics)!=9 or not np.allclose([intrinsics[0],intrinsics[4],intrinsics[2],intrinsics[5]],[cam['fx'],cam['fy'],cam['cx'],cam['cy']],atol=.01):
                raise RuntimeError('Live CameraInfo disagrees with fixed V0.4 camera model')
            self.camera_info={'width':self.info.width,'height':self.info.height,'K':intrinsics}
        except BaseException:
            self.close();raise

    def wait(self,predicate,description):
        deadline=time.monotonic()+self.cfg['capture']['timeout_s']
        while time.monotonic()<deadline:
            if self.process.poll() is not None: raise RuntimeError('Gazebo exited during '+description+'; see '+str(self.run_dir/'gazebo.log'))
            value=predicate()
            if value: return value
            time.sleep(.01)
        raise TimeoutError('Timed out waiting for '+description+'; see '+str(self.run_dir/'gazebo.log'))

    def request(self,suffix,request,response_type):
        r={'service':f"/world/{self.cfg['world']['name']}/{suffix}",
           'request':base64.b64encode(request.SerializeToString()).decode(),
           'request_type':request.DESCRIPTOR.full_name,'response_type':response_type.DESCRIPTOR.full_name,'timeout':5000}
        self.worker.stdin.write(json.dumps(r)+'\n');self.worker.stdin.flush()
        line=self.worker.stdout.readline()
        if not line: raise RuntimeError('Gazebo service worker exited')
        data=json.loads(line)
        if 'error' in data: raise RuntimeError(data['error'])
        ok=data['ok'];response=response_type();response.ParseFromString(base64.b64decode(data['response']))
        if not ok or hasattr(response,'data') and not response.data:
            raise RuntimeError(f'Gazebo service failed: {suffix}; transport_ok={ok}; response={response}')
        return response

    def capture(self,scene):
        from gz.msgs10.pose_v_pb2 import Pose_V
        from gz.msgs10.boolean_pb2 import Boolean
        from gz.msgs10.light_pb2 import Light
        cfg=self.cfg;cam=cfg['camera'];commanded={'dataset_rig':scene['camera']}
        for o in scene['objects']+scene['distractors']: commanded[o['instance_id']]=o['pose']
        current=set(commanded)-{'dataset_rig'}
        for name in self.active-current:
            commanded[name]={'position':[cfg['world']['staging_x_m'],0,-50],'quaternion':[0,0,0,1]}
        req=Pose_V()
        for name,value in commanded.items():
            p=req.pose.add();p.name=name
            p.position.x,p.position.y,p.position.z=value['position']
            p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w=value['quaternion']
        before=max(self.buffers['rgb'],default=-1)
        self.request('set_pose_vector',req,Boolean)
        light=Light(name='sun',id=self.entity_ids['sun'],type=Light.DIRECTIONAL,cast_shadows=True,intensity=scene['lighting']['intensity'])
        light.direction.x,light.direction.y,light.direction.z=scene['lighting']['direction']
        light.diffuse.r,light.diffuse.g,light.diffuse.b=scene['lighting']['color'];light.diffuse.a=1
        light.specular.r=0;light.specular.g=0;light.specular.b=0;light.specular.a=1
        self.request('light_config',light,Boolean)
        self.active=current
        def realized():
            with self.lock:
                if self.pose_stamp<=before: return None
                for name,value in commanded.items():
                    p=self.poses.get(name)
                    if p is None or np.linalg.norm(np.asarray(p['position'])-value['position'])>cfg['capture']['pose_tolerance_m']: return None
                    if min(np.linalg.norm(np.asarray(p['quaternion'])-value['quaternion']),np.linalg.norm(np.asarray(p['quaternion'])+value['quaternion']))>cfg['capture']['orientation_tolerance']: return None
                return self.pose_stamp,{name:self.poses[name] for name in commanded}
        change_stamp,actual=self.wait(realized,'actual simulator pose readback')
        after=change_stamp+cfg['capture']['settling_frames']/cam['update_rate_hz']
        def synchronized():
            with self.lock:
                for t in reversed(self.buffers['rgb']):
                    if t<after: continue
                    box_t=min(self.buffers['boxes'],key=lambda b:abs(t-b),default=-100)
                    if abs(t-box_t)<=cfg['capture']['sync_tolerance_s']:
                        return self.buffers['rgb'][t],self.buffers['boxes'][box_t]
            return None
        rgb,boxes=self.wait(synchronized,'fresh synchronized RGB and native boxes')
        if rgb.width!=cam['width'] or rgb.height!=cam['height'] or rgb.pixel_format_type!=3 or rgb.step!=cam['width']*3:
            raise RuntimeError('Unexpected Gazebo RGB layout')
        array=np.frombuffer(rgb.data,np.uint8).reshape(cam['height'],cam['width'],3)
        image=cv2.cvtColor(array,cv2.COLOR_RGB2BGR)
        objects=[]
        for o in scene['objects']:
            record=dict(o);record['commanded_pose']=record.pop('pose');record['pose']=actual[o['instance_id']]
            asset=next(a for a in cfg['assets'] if a['asset_id']==o['asset_id'])
            record['secondary_bbox_px']=projected_geometry(asset,record['pose'],actual['dataset_rig'],cam)
            objects.append(record)
        candidates=[]
        labels={c['gazebo_label']:c['yolo_id'] for c in cfg['classes']}
        for entry in boxes.annotated_box:
            if entry.label not in labels: raise RuntimeError('Unexpected native semantic class label')
            extra=1 if cfg['annotation']['bbox_max_is_inclusive'] else 0
            b=[entry.box.min_corner.x,entry.box.min_corner.y,entry.box.max_corner.x+extra,entry.box.max_corner.y+extra]
            if clip_box(b,cam) is None: raise RuntimeError('Invalid native box')
            candidates.append((entry.label,b))
        matches={};remaining=set(range(len(objects)))
        # Native messages expose class labels, not stable instance IDs. Match by
        # independent realized geometry and reject ambiguous or unexplained boxes.
        scores=sorted([(iou(clip_box(o['secondary_bbox_px'],cam),b),j,k) for j,o in enumerate(objects)
                       for k,(label,b) in enumerate(candidates) if label==o['gazebo_label']],reverse=True)
        used=set()
        for score,j,k in scores:
            if j in remaining and k not in used and score>=cfg['annotation']['association_min_iou']:
                matches[j]=candidates[k][1];remaining.remove(j);used.add(k)
        if len(used)!=len(candidates): raise RuntimeError('Native boxes cannot be associated with realized target instances')
        lines=[]
        for j,o in enumerate(objects):
            projected=clip_box(o['secondary_bbox_px'],cam);native=matches.get(j);clipped=clip_box(native,cam)
            o.update(bbox_px=clipped,yolo_bbox=None,visible_fraction=None,
                     visibility_method='not measured; projected/native box IoU is not a pixel visibility fraction',
                     truncated=o['secondary_bbox_px']!=projected,occlusion_requested=scene['occlusion_requested'],
                     annotation_iou=iou(projected,clipped),label_state='labelled',ignored_reason=None)
            if native is None:
                o['label_state']='ignored_outside' if projected is None else 'ignored_occluded'
                o['ignored_reason']='No native visible box; '+('outside projected image' if projected is None else 'no visible simulator pixels')
            elif min(clipped[2]-clipped[0],clipped[3]-clipped[1])<cfg['annotation']['min_box_px'] or (clipped[2]-clipped[0])*(clipped[3]-clipped[1])<cfg['annotation']['min_box_area_px']:
                o['label_state']='ignored_tiny';o['ignored_reason']='Below configured pixel threshold'
            else:
                o['yolo_bbox']=yolo_box(clipped,cam)
                lines.append(str(o['class_id'])+' '+' '.join(f'{v:.9f}' for v in o['yolo_bbox']))
        # "positive" describes the intended target-bearing scene. A fully
        # occluded/tiny scene legitimately has empty visible YOLO labels;
        # retain every target and its explicit ignored reason instead of
        # retrying an unchanged scene forever or inventing a visible box.
        meta=dict(scene);meta['camera']=dict(scene['camera']);meta['camera']['commanded_pose']=scene['camera']
        meta['camera'].update(actual['dataset_rig']);meta['camera']['model']=cam;meta['camera']['live_camera_info']=self.camera_info
        meta['objects']=objects
        meta['distractors']=[dict(d,pose=actual[d['instance_id']]) for d in scene['distractors']]
        meta.update(simulation_timestamp=stamp(rgb),annotation_timestamp=stamp(boxes),
                    timestamp_delta_s=abs(stamp(rgb)-stamp(boxes)),scene_readback_timestamp=change_stamp,
                    settling_sim_seconds=stamp(rgb)-change_stamp,generation_timestamp=utc_now(),
                    annotation_method='native_visible_2d',native_box_count=len(candidates))
        return image,('\n'.join(lines)+'\n' if lines else ''),meta

    def close(self):
        if hasattr(self,'process') and self.process.poll() is None:
            os.killpg(self.process.pid,signal.SIGINT)
            try: self.process.wait(8)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid,signal.SIGKILL);self.process.wait()
        for topic in self.node.subscribed_topics(): self.node.unsubscribe(topic)
        if hasattr(self,'worker'):
            self.worker.stdin.close()
            try: self.worker.wait(5)
            except subprocess.TimeoutExpired: self.worker.kill();self.worker.wait()
        if hasattr(self,'log'): self.log.close()

    def __enter__(self): return self
    def __exit__(self,*args): self.close()
