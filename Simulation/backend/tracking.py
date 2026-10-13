"""Image-derived target registry with two confidence association passes.

ByteTrack-inspired high/low score association in a calibrated ground frame,
with bounded constant-velocity estimates and inexpensive HSV appearance cues.
This is an independent implementation, not the upstream ByteTrack package.
No city, scene, actor names or simulator target poses enter this module.
"""
from __future__ import annotations
import math,threading
from collections import OrderedDict
import numpy as np
import cv2

def appearance(frame,box,foreground=False):
    x,y,w,h=box;height,width=frame.shape[:2]
    # Central object region reduces surrounding asphalt in the descriptor.
    xa,xb=max(0,int(x+w*.15)),min(width,int(x+w*.85))
    ya,yb=max(0,int(y+h*.12)),min(height,int(y+h*.88))
    crop=frame[ya:yb,xa:xb]
    if not crop.size:return None
    hsv=cv2.cvtColor(crop,cv2.COLOR_BGR2HSV)
    mask=None
    if foreground:
        # Nadir person boxes contain much more pavement than clothing. Compare
        # visible saturated foreground instead of blessing a nearby grey shadow
        # through its shared background. Insufficient pixels mean no identity cue.
        mask=((hsv[:,:,1]>=55)&(hsv[:,:,2]>=45)).astype(np.uint8)*255
        if cv2.countNonZero(mask)<8:return None
    hist=cv2.calcHist([hsv],[0,1],mask,[16,8],[0,180,0,256]).ravel()
    return hist/max(1e-6,np.linalg.norm(hist))

def similarity(a,b):
    return float(np.clip(np.dot(a,b),0,1)) if a is not None and b is not None else .5

class Registry:
    def __init__(self):
        self.lock=threading.RLock();self.clear()
    def clear(self):
        with self.lock:
            self.tracks={};self.frames={};self.counter=0;self.crops=OrderedDict();self.selected=None;self.events=[];self.ambiguities={}
    def predicted(self,t,now):
        dt=max(0.,now-t['last_seen']);horizon=min(dt,8.)
        return [t['position'][0]+t['velocity'][0]*horizon,t['position'][1]+t['velocity'][1]*horizon,0.]
    def _event(self,t,kind,time,detail):
        self.events.append({'target_id':t,'kind':kind,'time':round(time,2),'detail':detail});self.events=self.events[-120:]
    def update(self,did,stamp,detections,frame,site,confidence=.4,frame_key=None):
        with self.lock:
            channel=frame_key or did
            if stamp<=self.frames.get(channel,-1):return []
            self.frames[channel]=stamp
            valid=[dict(d) for d in detections if d.get('position') is not None]
            descriptors=[appearance(frame,d['box'],d['class']=='person') for d in valid]
            # A second matching image candidate can challenge identity even if its
            # class score is below the catalogue confirmation threshold.
            for i,a in enumerate(valid):
                for j in range(i+1,len(valid)):
                    b=valid[j]
                    if a['class']!=b['class'] or min(a['confidence'],b['confidence'])<.2:continue
                    ax,ay,aw,ah=a['box'];bx,by,bw,bh=b['box']
                    intersection=max(0.,min(ax+aw,bx+bw)-max(ax,bx))*max(0.,min(ay+ah,by+bh)-max(ay,by))
                    overlap=intersection/max(1.,aw*ah+bw*bh-intersection)
                    gap=math.dist(a['position'][:2],b['position'][:2])
                    if overlap>.1 or not .6<gap<(3. if a['class']=='person' else 4.) or similarity(descriptors[i],descriptors[j])<.85:continue
                    for key,t in self.tracks.items():
                        if not t['confirmed'] or t['class']!=a['class'] or not 0<=stamp-t['last_seen']<2:continue
                        if min(math.dist(self.predicted(t,stamp)[:2],d['position'][:2]) for d in (a,b))>2.5:continue
                        t['identity_confidence']=min(.55,t['identity_confidence'])
                        self.ambiguities[key]=[a['box'],b['box']]
            # Quarantine every disputed identity until explicit confirmation. Old
            # hypotheses must not compete with a confirmed replacement and
            # repeatedly challenge a single observation of the same object.
            used_tracks=set(self.ambiguities)
            used_dets=set();output=[]
            # Low scores can continue a known track, but cannot create one.
            for high_pass in (True,False):
                candidates=[i for i,d in enumerate(valid) if i not in used_dets and (d['confidence']>=confidence)==high_pass]
                pairs=[]
                for i in candidates:
                    det=valid[i];options=[]
                    for key,t in self.tracks.items():
                        if key in used_tracks or t['class']!=det['class']:continue
                        if not high_pass and det['class']=='person' and (descriptors[i] is None or t['_appearance'] is None):continue
                        age=stamp-t['last_seen']
                        if age<-1. or age>90 or (not high_pass and age>2):continue
                        pred=self.predicted(t,stamp);gap=math.dist(pred[:2],det['position'][:2]);app=similarity(t['_appearance'],descriptors[i])
                        gate=min(18.,2.3+max(0,age)*1.4)
                        if gap>gate or app<(.5 if age<3 else .83):continue
                        if age>20:
                            self.ambiguities[key]=[valid[i]['box']];continue
                        cost=.65*gap/gate+.35*(1-app)
                        options.append((cost,key,app,age))
                    # A one-frame tentative hypothesis must not repeatedly
                    # challenge an established continuing identity. Separate
                    # same-frame lookalikes are still checked above.
                    confirmed=[o for o in options if self.tracks[o[1]]['confirmed']]
                    if confirmed:options=confirmed
                    options.sort()
                    if len(options)>1 and options[1][0]-options[0][0]<.12:
                        for _,key,_,_ in options[:2]:
                            self.tracks[key]['identity_confidence']=min(.55,self.tracks[key]['identity_confidence'])
                            self.ambiguities[key]=[valid[i]['box']]
                        used_dets.add(i)  # Do not create a duplicate for an unresolved association.
                        continue
                    if options:
                        cost,key,app,age=options[0]
                        pairs.append((cost,i,key,app,age))
                for cost,i,key,app,age in sorted(pairs):
                    if i in used_dets or key in used_tracks:continue
                    t=self.tracks[key];det=valid[i];used_dets.add(i);used_tracks.add(key)
                    if stamp>t['last_seen']:
                        dt=stamp-t['last_seen'];delta=(np.array(det['position'][:2])-np.array(t['position'][:2]))/max(.08,dt)
                        delta=np.clip(delta,-6.,6.)
                        t['velocity']=(.75*np.array(t['velocity'])+.25*delta).tolist() if dt<3 else [0.,0.]
                        t['position']=[.25*a+.75*b for a,b in zip(self.predicted(t,stamp),det['position'])]
                        t['last_seen']=stamp;t['last_detection']=stamp;t['source']=det.get('source','YOLOX');t['class_provisional']=det.get('class_provisional',False);t['confidence']=det['confidence'];t['box']=det['box'];t['drone']=did
                        t['hits']+=int(high_pass);t['identity_confidence']=min(.98,.65+.2*app+.1*(1-cost))
                        t['uncertainty_m']=.6+min(2.,cost*2)
                        if descriptors[i] is not None:
                            t['_appearance']=descriptors[i] if t['_appearance'] is None else (.85*t['_appearance']+.15*descriptors[i])
                            norm=np.linalg.norm(t['_appearance']);t['_appearance']/=max(1e-6,norm)
                        if not t['confirmed'] and t['hits']>=3:
                            t['confirmed']=True;self._event(key,'confirmed',stamp,'Repeated camera observations')
                        if age>2:self._event(key,'reacquired',stamp,'Visual appearance and movement association')
                        self.ambiguities.pop(key,None)
                        self._observe(t,did,site,stamp,frame,det)
                    output.append({**det,'track_id':key})
            for i,det in enumerate(valid):
                if i in used_dets or det['confidence']<confidence:continue
                self.counter+=1;key=('Person' if det['class']=='person' else 'Vehicle')+f'-{self.counter:03d}'
                t={'id':key,'class':det['class'],'confidence':det['confidence'],'identity_confidence':.55,'position':det['position'],
                   'velocity':[0.,0.],'first_seen':stamp,'last_seen':stamp,'last_detection':stamp,'source':det.get('source','YOLOX'),'class_provisional':det.get('class_provisional',False),'drone':did,'site':site,'sites':[site],
                   'box':det['box'],'hits':1,'confirmed':False,'uncertainty_m':1.,'history':[],'_appearance':descriptors[i]}
                self.tracks[key]=t;self._observe(t,did,site,stamp,frame,det);output.append({**det,'track_id':key})
            # Hard bounds on metadata and JPEG memory, independent of mission duration.
            while len(self.tracks)>250:
                key=next((k for k,t in self.tracks.items() if k!=self.selected and stamp-t['last_seen']>30),None)
                if key is None:key=next((k for k in self.tracks if k!=self.selected),None)
                if key is None:break
                self.tracks.pop(key);self.crops.pop(key,None)
            return output
    def _observe(self,t,did,site,stamp,frame,det):
        t['site']=site
        if site not in t['sites']:t['sites'].append(site)
        t['history'].append({'time':round(stamp,2),'drone':did,'site':site,'position':det['position'],'confidence':round(det['confidence'],3)})
        t['history']=t['history'][-12:]
        x,y,w,h=map(int,det['box']);crop=frame[max(0,y):max(0,y+h),max(0,x):max(0,x+w)]
        if crop.size:
            scale=min(1.,120/max(crop.shape[:2]));crop=cv2.resize(crop,(max(1,int(crop.shape[1]*scale)),max(1,int(crop.shape[0]*scale))))
            self.crops[t['id']]=cv2.imencode('.jpg',crop,[cv2.IMWRITE_JPEG_QUALITY,65])[1].tobytes();self.crops.move_to_end(t['id'])
            while len(self.crops)>128:self.crops.popitem(last=False)
    def snapshot(self,now):
        with self.lock:
            rows=[]
            for key,t in self.tracks.items():
                if not t['confirmed']:continue
                age=max(0.,now-t['last_seen']);state='visible' if age<1 else 'occluded' if age<3 else 'stale' if age<30 else 'lost' if age<180 else 'archived'
                row={k:v for k,v in t.items() if not k.startswith('_') and k not in ('hits','confirmed')}
                row.update(state=state,age=round(age,2),speed=round(math.hypot(*t['velocity']),2),heading=math.atan2(t['velocity'][1],t['velocity'][0]),
                           predicted_position=self.predicted(t,now),uncertainty_m=round(min(25.,t['uncertainty_m']+age*.7),2),
                           ambiguous=key in self.ambiguities,thumbnail=key in self.crops,selected=key==self.selected)
                rows.append(row)
            return rows
    def get(self,key,now):return next((t for t in self.snapshot(now) if t['id']==key),None)
    def select(self,key,now):
        with self.lock:
            if self.get(key,now) is None:raise ValueError('Choose a confirmed camera target from the catalogue.')
            self.selected=key;self._event(key,'selected',now,'Operator selected this camera track')
    def confirm(self,new_key,now):
        with self.lock:
            if self.get(new_key,now) is None:raise ValueError('Choose a confirmed candidate.')
            old=self.selected;self.selected=new_key
            self.tracks[new_key]['identity_confidence']=max(.9,self.tracks[new_key]['identity_confidence']);self.ambiguities.pop(new_key,None)
            self._event(new_key,'operator-confirmed',now,f'Operator confirmed candidate after {old} became uncertain')
    def thumbnail(self,key):
        with self.lock:return self.crops.get(key)
    def refresh_visual(self,key,did,stamp,box,position,frame,quality,site,method="visual-tracker"):
        with self.lock:
            t=self.tracks.get(key)
            if t is None or not t['confirmed'] or stamp<=t['last_seen'] or key in self.ambiguities:return None
            dt=stamp-t['last_seen'];old=self.predicted(t,stamp)
            # Geometry and image continuity both have to agree; no prediction-only sightings.
            if math.dist(position[:2],old[:2])>3.:return None
            delta=(np.array(position[:2])-np.array(t['position'][:2]))/max(.08,dt)
            t['velocity']=(.85*np.array(t['velocity'])+.15*np.clip(delta,-6,6)).tolist()
            t['position']=[.2*a+.8*b for a,b in zip(old,position)];t['last_seen']=stamp;t['box']=list(map(float,box));t['drone']=did
            t['identity_confidence']=quality;t['source']=method;t['uncertainty_m']=1.2
            self._observe(t,did,site,stamp,frame,{'box':box,'position':position,'confidence':t['confidence']})
            return {'class':t['class'],'confidence':t['confidence'],'box':t['box'],'position':t['position'],'track_id':key,'source':method,'visual_quality':quality}
