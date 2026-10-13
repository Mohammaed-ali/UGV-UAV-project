"""Image-only perception. This module does not receive the scene's object list."""
import math,time,threading
from pathlib import Path
import cv2
import numpy as np
from .transport import quaternion_matrix

CLASSES={0:'person',2:'car',5:'bus',7:'truck'}

def camera_to_world(vector,pose):
    # Gazebo +X-forward camera pitched down 90 degrees; optical axes right/down/forward.
    x,y,z=vector
    return np.asarray(pose['position'])+quaternion_matrix(pose['quaternion'])@np.array([-y,-x,-z-.08])

def ground_point(u,v,pose,width=640,height=480):
    focal=width/(2*math.tan(1.22/2));origin=camera_to_world([0,0,0],pose)
    endpoint=camera_to_world([(u-width/2)/focal,(v-height/2)/focal,1],pose)
    ray=endpoint-origin
    if ray[2]>=-.1:return None
    return (origin-ray*origin[2]/ray[2]).tolist()

class Vision:
    def __init__(self,root,runtime):
        self.root=root;self.runtime=runtime;self.running=True;self.latest={};self.processed={};self.raw={};self.annotated={};self.targets=[];self.error=None;self.detector_ready=False;self.tag_ready=False;self.confidence=.4;self.landing=set();self.track_counter=0;self.tag_latest={};self.object_latest={};self.tag_processed={};self.lock=threading.RLock();self.generation=0
        cv2.setNumThreads(2)
        self.tag_thread=threading.Thread(target=self.run_tags,daemon=True);self.tag_thread.start()
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def run(self):
        try:
            model=self.root/'assets/detector/yolox.onnx'
            net=cv2.dnn.readNet(str(model)) if model.is_file() else None
            self.detector_ready=net is not None
            cv2.setNumThreads(2)
            grid=[];strides=[]
            for s in (8,16,32):
                yy,xx=np.meshgrid(np.arange(640//s),np.arange(640//s),indexing='ij');grid.append(np.stack((xx,yy),-1).reshape(-1,2));strides.append(np.full(((640//s)**2,1),s))
            grid=np.concatenate(grid);strides=np.concatenate(strides)
        except Exception as e:self.error=str(e);return
        while self.running:
            gz=self.runtime.gz
            if gz is None:time.sleep(.1);continue
            with gz.lock:packets=list(gz.camera_packets.items())
            packets=[(did,p) for did,p in packets if did not in self.landing]
            for did,_ in packets:
                if not self.running:break
                with gz.lock:p=gz.camera_packets.get(did)
                if p is None:continue
                if self.processed.get(did)==p['time']:continue
                self.processed[did]=p['time'];generation=self.generation;start=time.monotonic();frame=p['image'];canvas=frame.copy();height,width=frame.shape[:2];focal=width/(2*math.tan(1.22/2))
                result={'time':p['time'],'sync_error':p['sync_error'],'detections':[],'tags':[],'width':width,'height':height}
                try:
                    if net is not None and did not in self.landing:
                        ratio=min(640/width,640/height);resized=cv2.resize(frame,(int(width*ratio),int(height*ratio)));padded=np.full((640,640,3),114,dtype=np.uint8);padded[:resized.shape[0],:resized.shape[1]]=resized
                        blob=cv2.dnn.blobFromImage(padded,1.,(640,640),swapRB=True)
                        net.setInput(blob);rows=net.forward()[0]
                        rows[:,:2]=(rows[:,:2]+grid)*strides;rows[:,2:4]=np.exp(np.minimum(rows[:,2:4],10))*strides
                        scores=rows[:,4,None]*rows[:,5:];classes=np.argmax(scores,axis=1);conf=np.max(scores,axis=1)
                        indices=np.where((conf>=self.confidence)&np.isin(classes,list(CLASSES)))[0]
                        xywh=rows[indices,:4].copy();xywh[:,:2]-=xywh[:,2:]/2
                        # Run NMS per class to avoid suppressing overlapping objects of different classes.
                        keep=[]
                        for cls in CLASSES:
                            members=np.where(classes[indices]==cls)[0]
                            if len(members):
                                found=cv2.dnn.NMSBoxes(xywh[members].tolist(),conf[indices[members]].tolist(),self.confidence,.45)
                                keep.extend(members[np.asarray(found).reshape(-1)].tolist())
                        for k in keep:
                            ix=indices[k];x,y,w,h=(xywh[k]/ratio).tolist();x=max(0,x);y=max(0,y);w=min(w,width-x);h=min(h,height-y)
                            position=ground_point(x+w/2,y+h/2,p['pose']) if p['pose'] and p['sync_error']<=.25 else None
                            det={'class':CLASSES[int(classes[ix])],'confidence':float(conf[ix]),'box':[x,y,w,h],'position':position}
                            result['detections'].append(det);cv2.rectangle(canvas,(int(x),int(y)),(int(x+w),int(y+h)),(112,237,214),2);cv2.putText(canvas,f'{det["class"]} {det["confidence"]:.0%}',(int(x),max(16,int(y)-6)),cv2.FONT_HERSHEY_SIMPLEX,.5,(112,237,214),1)
                    if did in self.landing:continue
                    raw=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,75])[1].tobytes();annotated=cv2.imencode('.jpg',canvas,[cv2.IMWRITE_JPEG_QUALITY,80])[1].tobytes()
                    result['latency_ms']=round((time.monotonic()-start)*1000,1);result['received']=time.monotonic()
                    with self.lock:
                        if generation!=self.generation or self.runtime.gz is not gz:continue
                        self.object_latest[did]=result;tag_result=self.tag_latest.get(did,{})
                        self.latest[did]={**result,'tags':tag_result.get('tags',[]),'tag_time':tag_result.get('time'),'tag_latency_ms':tag_result.get('latency_ms')}
                        self.raw[did]=raw;self.annotated[did]=annotated
                except Exception as e:self.error=str(e)
            time.sleep(.01)
    def run_tags(self):
        try:
            from pupil_apriltags import Detector
            detector=Detector(families='tag36h11',nthreads=2,quad_decimate=1.0);self.tag_ready=True
        except Exception as e:self.error=str(e);return
        preview_after={};cursor=0
        while self.running:
            gz=self.runtime.gz
            if gz is None:time.sleep(.05);continue
            with gz.lock:ids=list(gz.camera_packets)
            primary=[did for did in ids if did in self.landing]
            previews=[did for did in ids if did not in self.landing]
            if previews:
                did=previews[cursor%len(previews)];cursor+=1
                if time.monotonic()-preview_after.get(did,0)>.5:primary.append(did);preview_after[did]=time.monotonic()
            for did in primary:
                if not self.running:break
                # Fetch a current frame immediately before inference, avoiding an
                # old packet captured before other cameras were processed.
                with gz.lock:p=gz.camera_packets.get(did)
                if not p or self.tag_processed.get(did)==p['time']:continue
                self.tag_processed[did]=p['time'];generation=self.generation;start=time.monotonic()
                frame=p['image'];canvas=frame.copy();height,width=frame.shape[:2];focal=width/(2*math.tan(1.22/2))
                result={'time':p['time'],'sync_error':p['sync_error'],'tags':[],'width':width,'height':height}
                try:
                    detected=detector.detect(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),estimate_tag_pose=True,camera_params=(focal,focal,width/2,height/2),tag_size=.304)
                    for tag in detected:
                        if tag.hamming or tag.decision_margin<20:continue
                        center=camera_to_world(tag.pose_t.reshape(3),p['pose']).tolist() if p['pose'] and p['sync_error']<=.25 else None
                        result['tags'].append({'id':int(tag.tag_id),'margin':float(tag.decision_margin),'pose_error':float(tag.pose_err),'position':center,'camera_position':tag.pose_t.reshape(3).tolist()})
                        corners=np.int32(tag.corners);cv2.polylines(canvas,[corners],True,(70,225,170),2);cv2.putText(canvas,f'TAG {tag.tag_id}',tuple(corners[0]),cv2.FONT_HERSHEY_SIMPLEX,.5,(70,225,170),1)
                    result['latency_ms']=round((time.monotonic()-start)*1000,1);result['received']=time.monotonic()
                    raw=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,75])[1].tobytes();annotated=cv2.imencode('.jpg',canvas,[cv2.IMWRITE_JPEG_QUALITY,80])[1].tobytes()
                    with self.lock:
                        if generation!=self.generation or self.runtime.gz is not gz:continue
                        self.tag_latest[did]=result
                        if did in self.landing or did not in self.object_latest:
                            self.latest[did]={**result,'detections':[],'tag_time':result['time'],'tag_latency_ms':result['latency_ms']}
                            self.raw[did]=raw;self.annotated[did]=annotated
                        else:self.latest[did]={**self.latest.get(did,{}),'tags':result['tags'],'tag_time':result['time'],'tag_latency_ms':result['latency_ms']}
                except Exception as e:self.error=str(e)
            time.sleep(.01)
    def clear(self):
        with self.lock:
            self.generation+=1
            for mapping in (self.latest,self.object_latest,self.tag_latest,self.processed,self.tag_processed,self.raw,self.annotated):mapping.clear()
            self.landing.clear()
    def close(self):
        self.running=False;self.thread.join(timeout=3);self.tag_thread.join(timeout=3)
