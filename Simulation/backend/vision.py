"""Image-only perception. This module does not receive the scene's object list."""
import math,time,threading
from pathlib import Path
import cv2
import numpy as np
from .transport import quaternion_matrix
from .tracking import Registry

CLASSES={0:'person',2:'car',5:'bus',7:'truck'}

def make_tag_detector():
    from pupil_apriltags import Detector
    class ManagedDetector(Detector):
        def __del__(self):
            # This binding frees families before destroying its detector. Clear
            # the detector's family references first to avoid a native use-after-free.
            if getattr(self,'tag_detector_ptr',None):
                self.libc.apriltag_detector_clear_families(self.tag_detector_ptr)
                super().__del__()
                self.tag_detector_ptr=None
    return ManagedDetector(families='tag36h11',nthreads=2,quad_decimate=1.0)

def camera_relative(vector,pose):
    # Gazebo +X-forward camera pitched down 90 degrees; optical axes right/down/forward.
    x,y,z=vector
    return quaternion_matrix(pose['quaternion'])@np.array([-y,-x,-z-.08])

def camera_to_world(vector,pose):
    return np.asarray(pose['position'])+camera_relative(vector,pose)

def ground_point(u,v,pose,width=640,height=480,plane_height=0.):
    focal=width/(2*math.tan(1.22/2));origin=camera_to_world([0,0,0],pose)
    endpoint=camera_to_world([(u-width/2)/focal,(v-height/2)/focal,1],pose)
    ray=endpoint-origin
    if ray[2]>=-.1:return None
    return (origin+ray*(plane_height-origin[2])/ray[2]).tolist()

class Vision:
    def __init__(self,root,runtime):
        self.root=root;self.runtime=runtime;self.running=True;self.latest={};self.processed={};self.raw={};self.annotated={};self.targets=[];self.error=None;self.detector_ready=False;self.tag_ready=False;self.confidence=.4;self.landing=set();self.track_counter=0;self.tag_latest={};self.object_latest={};self.tag_processed={};self.lock=threading.RLock();self.generation=0
        self.searching=set();self.inflight=set()
        self.performance={'detector_frames':0,'detector_total_ms':0.,'visual_frames':0};self.registry=Registry();self.observer_keys={};self.sites={};self.aerial_ready=False;self.aerial_error=None
        self.anchors={};self.optical_states={};self.optical_debug={};self.close_observations={};self.depth_targets={}
        cv2.setNumThreads(2)
        self.tag_thread=threading.Thread(target=self.run_tags,daemon=True);self.tag_thread.start()
        self.threads=[threading.Thread(target=self.run,daemon=True) for _ in range(2)]
        self.thread=self.threads[0]
        for thread in self.threads:thread.start()
        self.optical_thread=threading.Thread(target=self.run_optical,daemon=True);self.optical_thread.start()
        self.aerial_thread=threading.Thread(target=self.run_aerial_vehicles,daemon=True);self.aerial_thread.start()
    def metric_detections(self,did,stamp,frame,pose,detections):
        if did not in getattr(self,'depth_targets',{}) or pose is None:return detections
        from .depth_visual import surface_candidates,localize_detections
        gz=self.runtime.gz
        history=list(getattr(gz,'depth_history',{}).get(did,[]))
        packet=min(history,key=lambda p:abs(p['time']-stamp)) if history else None
        return localize_detections(detections,surface_candidates(frame,packet,pose,stamp))
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
            # Spend inference on aircraft currently searching. Two independent
            # networks process the oldest available, distinct camera packets.
            with self.lock:
                packets=sorted([(did,p) for did,p in packets if did in self.searching and did not in self.landing and did not in self.inflight and self.processed.get(did)!=p['time']],key=lambda row:self.processed.get(row[0],-1))[:1]
                for did,_ in packets:self.inflight.add(did)
            for did,_ in packets:
                if not self.running:break
                with gz.lock:p=gz.camera_packets.get(did)
                if p is None:
                    self.inflight.discard(did);continue
                if self.processed.get(did)==p['time']:
                    self.inflight.discard(did);continue
                self.processed[did]=p['time'];generation=self.generation;start=time.monotonic();frame=p['image'];canvas=frame.copy();height,width=frame.shape[:2];focal=width/(2*math.tan(1.22/2))
                object_pose=p['pose'];object_sync=p['sync_error'];pose_source='calibrated simulation aircraft pose'
                if getattr(getattr(self.runtime,'mission',None),'living_city',False):
                    object_pose,object_sync=self.runtime.fleet.perception_pose(did,p['time']) if self.runtime.fleet else (None,999.)
                    pose_source='PX4 estimated position and attitude, known launch origin'
                result={'time':p['time'],'sync_error':object_sync,'pose_source':pose_source,'detections':[],'tags':[],'width':width,'height':height}
                try:
                    if net is not None and did not in self.landing:
                        ratio=min(640/width,640/height);resized=cv2.resize(frame,(int(width*ratio),int(height*ratio)));padded=np.full((640,640,3),114,dtype=np.uint8);padded[:resized.shape[0],:resized.shape[1]]=resized
                        blob=cv2.dnn.blobFromImage(padded,1.,(640,640),swapRB=True)
                        net.setInput(blob);rows=net.forward()[0]
                        rows[:,:2]=(rows[:,:2]+grid)*strides;rows[:,2:4]=np.exp(np.minimum(rows[:,2:4],10))*strides
                        scores=rows[:,4,None]*rows[:,5:];classes=np.argmax(scores,axis=1);conf=np.max(scores,axis=1)
                        low_threshold=.12 if getattr(getattr(self.runtime,'mission',None),'living_city',False) else self.confidence
                        indices=np.where((conf>=low_threshold)&np.isin(classes,list(CLASSES)))[0]
                        xywh=rows[indices,:4].copy();xywh[:,:2]-=xywh[:,2:]/2
                        # Run NMS per class to avoid suppressing overlapping objects of different classes.
                        keep=[]
                        for cls in CLASSES:
                            members=np.where(classes[indices]==cls)[0]
                            if len(members):
                                found=cv2.dnn.NMSBoxes(xywh[members].tolist(),conf[indices[members]].tolist(),low_threshold,.45)
                                keep.extend(members[np.asarray(found).reshape(-1)].tolist())
                        for k in keep:
                            ix=indices[k];x,y,w,h=(xywh[k]/ratio).tolist();x=max(0,x);y=max(0,y);w=min(w,width-x);h=min(h,height-y)
                            position=ground_point(x+w/2,y+h*(.94 if int(classes[ix])==0 else .5),object_pose) if object_pose and object_sync<=.25 else None
                            det={'class':CLASSES[int(classes[ix])],'confidence':float(conf[ix]),'box':[x,y,w,h],'position':position}
                            result['detections'].append(det);cv2.rectangle(canvas,(int(x),int(y)),(int(x+w),int(y+h)),(112,237,214),2);cv2.putText(canvas,f'{det["class"]} {det["confidence"]:.0%}',(int(x),max(16,int(y)-6)),cv2.FONT_HERSHEY_SIMPLEX,.5,(112,237,214),1)
                    if did in self.landing:continue
                    if getattr(getattr(self.runtime,'mission',None),'living_city',False):
                        with self.lock:
                            if generation!=self.generation or self.runtime.gz is not gz:continue
                            localized=self.metric_detections(did,p['time'],frame,object_pose,result['detections'])
                            result['detections']=self.registry.update(did,p['time'],localized,frame,self.sites.get(did,'survey'),self.confidence)
                            if any(d['confidence']>=self.confidence for d in result['detections']):self.anchors[did]={'frame':frame.copy(),'time':p['time'],'detections':result['detections'],'pose':object_pose}
                        for det in result['detections']:
                            x,y,_,_=det['box'];cv2.putText(canvas,det['track_id'],(int(x),max(32,int(y)-18)),cv2.FONT_HERSHEY_SIMPLEX,.45,(112,237,214),1)
                    raw=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,75])[1].tobytes();annotated=cv2.imencode('.jpg',canvas,[cv2.IMWRITE_JPEG_QUALITY,80])[1].tobytes()
                    result['latency_ms']=round((time.monotonic()-start)*1000,1);result['received']=time.monotonic()
                    with self.lock:
                        if generation!=self.generation or self.runtime.gz is not gz:continue
                        self.performance['detector_frames']+=1;self.performance['detector_total_ms']+=result['latency_ms']
                        if result['time']<self.object_latest.get(did,{}).get('time',-1):continue
                        self.object_latest[did]=result;tag_result=self.tag_latest.get(did,{})
                        self.latest[did]={**result,'tags':tag_result.get('tags',[]),'tag_time':tag_result.get('time'),'tag_latency_ms':tag_result.get('latency_ms')}
                        self.raw[did]=raw;self.annotated[did]=annotated
                except Exception as e:self.error=str(e)
                finally:
                    with self.lock:self.inflight.discard(did)
            time.sleep(.01)
    def run_aerial_vehicles(self):
        # One extra worker at <=0.5 Hz globally. It adds actual vehicle pixel
        # evidence where COCO YOLOX was measured to miss nadir synthetic cars.
        try:
            model=self.root/'assets/detector/aerial-vehicles.onnx'
            if not model.is_file():return
            net=None;self.aerial_ready=True
        except Exception as error:self.aerial_error=str(error);return
        seen={};last_wall=0.
        while self.running:
            gz=self.runtime.gz;m=getattr(self.runtime,'mission',None)
            if gz is None or not getattr(m,'aerial_vehicles',False):net=None
            if gz is None or not getattr(m,'living_city',False) or not getattr(m,'aerial_vehicles',False) or m.traffic==0 or time.monotonic()-last_wall<2.:
                time.sleep(.05);continue
            with gz.lock:packets=[(did,p) for did,p in gz.camera_packets.items() if did in self.searching and did not in self.landing and seen.get(did)!=p['time']]
            if not packets:time.sleep(.05);continue
            did,p=min(packets,key=lambda row:seen.get(row[0],-1));seen[did]=p['time'];generation=self.generation;last_wall=time.monotonic()
            frame=p['image'];pose,sync=self.runtime.fleet.perception_pose(did,p['time']) if self.runtime.fleet else (None,999.)
            if pose is None or sync>.25:continue
            try:
                start=time.monotonic()
                if net is None:net=cv2.dnn.readNet(str(model))
                canvas=np.full((640,640,3),114,np.uint8);canvas[:480]=frame
                net.setInput(cv2.dnn.blobFromImage(canvas,1/255.,(640,640),swapRB=True));rows=net.forward()[0].T
                conf=rows[:,4:].max(1);classes=rows[:,4:].argmax(1);dets=[]
                for cls,name in [(3,'car'),(5,'truck'),(8,'bus')]:
                    indices=np.where((classes==cls)&(conf>=self.confidence))[0]
                    boxes=rows[indices,:4].copy();boxes[:,:2]-=boxes[:,2:]/2
                    keep=cv2.dnn.NMSBoxes(boxes.tolist(),conf[indices].tolist(),self.confidence,.45)
                    for k in np.asarray(keep).reshape(-1):
                        x,y,w,h=boxes[k].tolist();x=max(0.,x);y=max(0.,y);w=min(w,640-x);h=min(h,480-y)
                        if w<8 or h<8:continue
                        position=ground_point(x+w/2,y+h/2,pose)
                        if position is not None:dets.append({'class':name,'confidence':float(conf[indices[k]]),'box':[x,y,w,h],'position':position,'source':'Aerial vehicle detector','class_provisional':True})
                with self.lock:
                    if generation!=self.generation or self.runtime.gz is not gz:continue
                    dets=self.metric_detections(did,p['time'],frame,pose,dets)
                    detections=self.registry.update(did,p['time'],dets,frame,self.sites.get(did,'survey'),self.confidence,frame_key=did+'-aerial')
                    for det in detections:
                        key=det['track_id']
                        if key in self.registry.tracks:self.registry.tracks[key]['drone']=did
                    self.performance['aerial_last_scores']={str(c):round(float(rows[:,4+c].max()),3) for c in (3,5,8)}
                    self.performance['aerial_frames']=self.performance.get('aerial_frames',0)+1
                    self.performance['aerial_total_ms']=self.performance.get('aerial_total_ms',0.)+(time.monotonic()-start)*1000
                    if detections:
                        self.anchors[did]={'frame':frame.copy(),'time':p['time'],'detections':detections,'pose':pose}
                        # The primary/optical worker may already have a newer frame.
                        if p['time']>=self.object_latest.get(did,{}).get('time',-1):
                            preview=frame.copy()
                            for det in detections:
                                x,y,w,h=det['box'];cv2.rectangle(preview,(int(x),int(y)),(int(x+w),int(y+h)),(112,237,214),2);cv2.putText(preview,det['track_id']+' vehicle',(int(x),max(18,int(y)-6)),cv2.FONT_HERSHEY_SIMPLEX,.5,(112,237,214),1)
                            obs={'time':p['time'],'sync_error':sync,'pose_source':'PX4 estimated position and attitude, known launch origin','detections':detections,'tags':[],'width':640,'height':480,'latency_ms':round((time.monotonic()-start)*1000,1),'source':'Aerial vehicle detector'}
                            self.object_latest[did]=obs;self.latest[did]=obs;self.raw[did]=cv2.imencode('.jpg',frame)[1].tobytes();self.annotated[did]=cv2.imencode('.jpg',preview)[1].tobytes()
            except Exception as error:self.aerial_error=str(error)

    def run_optical(self):
        from .optical import Optical,compensated_seed,interior_patch
        from .depth_visual import DepthVisual,paired_rgb
        seen={}
        while self.running:
            gz=self.runtime.gz;selected=self.registry.selected
            if gz is None or not (selected or self.observer_keys):time.sleep(.03);continue
            with gz.lock:packets=list(gz.camera_packets.items())
            for did,p in packets:
                key=selected or self.observer_keys.get(did)
                if not key:continue
                if getattr(self,'depth_targets',{}).get(did)==key:
                    p=paired_rgb(p,getattr(gz,'rgb_history',{}).get(did,[]),getattr(gz,'depth_history',{}).get(did,[]),seen.get(did,-1.))
                    if p is None:continue
                if did not in self.searching or did in self.landing or seen.get(did)==p['time']:continue
                seen[did]=p['time'];generation=self.generation
                pose,sync=self.runtime.fleet.perception_pose(did,p['time']) if self.runtime.fleet else (None,999.)
                if pose is None or sync>.25:continue
                anchor=self.anchors.get(did);tracker=self.optical_states.get(did)
                close=self.close_observations.get(did)
                close_mode=bool(close and close['target_id']==key and abs(p['time']-close['time'])<1.)
                depth_selected=getattr(self,'depth_targets',{}).get(did)==key or close_mode
                plane=close['surface_point'][2] if close_mode else None
                def depth_packet(stamp,drone=did,bridge=gz):
                    history=list(getattr(bridge,'depth_history',{}).get(drone,[]))
                    return min(history,key=lambda d:abs(d['time']-stamp)) if history else None
                if depth_selected and (tracker is None or not isinstance(tracker[1],DepthVisual)):
                    row=self.registry.get(key,p['time'])
                    debug={'time':p['time']}
                    depth_tracker=DepthVisual.seed(row,p['image'],depth_packet(p['time']),pose,p['time'],depth_packet,debug)
                    self.performance.setdefault('depth_continuity',{})[did]=debug
                    if depth_tracker:
                        tracker=(key,depth_tracker);self.optical_states[did]=tracker
                if not depth_selected and tracker and isinstance(tracker[1],DepthVisual):
                    self.optical_states.pop(did,None);tracker=None
                if tracker:
                    # Keep the current image identity when entering close view.
                    # Requiring a new detector seed here discards a good live lock.
                    tracker[1].close_mode=close_mode
                    if close_mode:tracker[1].plane_height=plane
                if tracker is None or tracker[0]!=key:
                    det=next((d for d in (anchor or {}).get('detections',[]) if d.get('track_id')==key and d['confidence']>=self.confidence),None)
                    if det is None or p['time']-anchor['time']>1.5:continue
                    seed_frame,seed_box=anchor['frame'],det['box']
                    if close_mode:seed_box=interior_patch(seed_box,.35,80.)
                    plane_height=plane if close_mode else (.8 if det['class']!='person' else .6)
                    current_pose=pose
                    if anchor.get('pose') is not None and current_pose is not None and sync<=.25:
                        corrected=compensated_seed(seed_frame,seed_box,anchor['pose'],current_pose,plane_height)
                        if corrected is None:continue
                        seed_frame,seed_box=corrected
                    tracker=(key,Optical(seed_frame,seed_box,anchor['time'],pose=pose,plane_height=plane_height,person_guard=det['class']=='person',close_mode=close_mode));self.optical_states[did]=tracker
                    self.optical_debug[did]={'seed_time':anchor['time'],'method':tracker[1].method,'successes':0,'state':'seeded'}
                try:
                    result=tracker[1].update(p['image'],p['time'],pose)
                    if result is None:
                        if tracker[1].rivals:
                            with self.registry.lock:
                                row=self.registry.tracks.get(key)
                                if row is not None:
                                    if key not in self.registry.ambiguities:self.registry._event(key,'identity-uncertain',p['time'],'Nearby image candidates have similar visual appearance')
                                    row['identity_confidence']=min(.55,row['identity_confidence']);self.registry.ambiguities[key]=tracker[1].rivals
                        self.optical_debug[did]={**self.optical_debug.get(did,{}),'state':'image lock lost','last_frame':p['time']}
                        self.optical_states.pop(did,None);continue
                    box,quality=result;x,y,w,h=box
                    row=self.registry.get(key,p['time'])
                    if row is None:continue
                    position=list(tracker[1].last_position) if isinstance(tracker[1],DepthVisual) else ground_point(x+w/2,y+h*(.5 if close_mode else .94 if row['class']=='person' else .5),pose,plane_height=plane if close_mode else 0.)
                    if position is not None and close_mode:position[2]=0.  # Registry remains a horizontal map track.
                    if position is None:continue
                    with self.lock:
                        if generation!=self.generation or self.runtime.gz is not gz:continue
                        det=self.registry.refresh_visual(key,did,p['time'],box,position,p['image'],quality,self.sites.get(did,'tracking'),tracker[1].method)
                        if det is None:continue
                        self.performance['visual_frames']+=1
                        self.optical_debug[did]={**self.optical_debug.get(did,{}),'state':'visual lock','quality':quality,'last_frame':p['time'],'successes':self.optical_debug.get(did,{}).get('successes',0)+1}
                        det['source']=tracker[1].method
                        canvas=p['image'].copy();cv2.rectangle(canvas,(int(x),int(y)),(int(x+w),int(y+h)),(112,237,214),2)
                        cv2.putText(canvas,key+' visual track',(int(x),max(18,int(y)-6)),cv2.FONT_HERSHEY_SIMPLEX,.45,(112,237,214),1)
                        observation={'time':p['time'],'sync_error':sync,'pose_source':'PX4 estimated position and attitude, known launch origin',
                                     'detections':[det],'tags':[],'width':640,'height':480,'latency_ms':0.,'source':tracker[1].method,'received':time.monotonic()}
                        self.object_latest[did]=observation;self.latest[did]=observation
                        self.raw[did]=cv2.imencode('.jpg',p['image'],[cv2.IMWRITE_JPEG_QUALITY,75])[1].tobytes()
                        self.annotated[did]=cv2.imencode('.jpg',canvas,[cv2.IMWRITE_JPEG_QUALITY,80])[1].tobytes()
                except Exception as error:self.error='Optical tracking: '+str(error);self.optical_states.pop(did,None)
            time.sleep(.01)
    def run_tags(self):
        try:
            detector=make_tag_detector();self.tag_ready=True
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
                        relative=camera_relative(tag.pose_t.reshape(3),p['pose']).tolist() if center is not None else None
                        result['tags'].append({'id':int(tag.tag_id),'margin':float(tag.decision_margin),'pose_error':float(tag.pose_err),'position':center,'relative_position':relative,'camera_position':tag.pose_t.reshape(3).tolist()})
                        corners=np.int32(tag.corners);cv2.polylines(canvas,[corners],True,(70,225,170),2);cv2.putText(canvas,f'TAG {tag.tag_id}',tuple(corners[0]),cv2.FONT_HERSHEY_SIMPLEX,.5,(70,225,170),1)
                    result['latency_ms']=round((time.monotonic()-start)*1000,1);result['received']=time.monotonic()
                    raw=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,75])[1].tobytes();annotated=cv2.imencode('.jpg',canvas,[cv2.IMWRITE_JPEG_QUALITY,80])[1].tobytes()
                    with self.lock:
                        if generation!=self.generation or self.runtime.gz is not gz:continue
                        self.tag_latest[did]=result
                        if did in self.landing or did not in self.object_latest or did not in self.searching and gz.preview_id==did:
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
            self.searching.clear();self.inflight.clear()
            self.registry.clear();self.sites.clear();self.observer_keys.clear()
            self.anchors.clear();self.optical_states.clear()
            self.optical_debug.clear();self.performance={'detector_frames':0,'detector_total_ms':0.,'visual_frames':0}
    def close(self):
        self.running=False
        for thread in self.threads:thread.join(timeout=3)
        self.tag_thread.join(timeout=3)
        self.optical_thread.join(timeout=3)
        self.aerial_thread.join(timeout=3)
