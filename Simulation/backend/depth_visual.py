"""Continue an already camera-confirmed identity using RGB and measured depth."""
import math
import cv2
import numpy as np
from .transport import quaternion_matrix
from .tracking import appearance,similarity


def paired_rgb(latest,rgb_history,depth_history,after=-1.):
    """Use a captured RGB/depth pair; never label a newer unpaired RGB frame."""
    for rgb in reversed(list(rgb_history)):
        if rgb['time']<=after or latest['time']-rgb['time']>.4:continue
        if any(abs(d['time']-rgb['time'])<=.04 for d in depth_history):return rgb
    return None

def surface_candidates(frame,packet,pose,stamp):
    if packet is None or abs(packet['time']-stamp)>.08:return []
    image=packet['image'];h,w=image.shape
    valid=np.isfinite(image)&(image>.05)&(image<100.)
    depth=np.where(valid,image,0.)
    yy,xx=np.indices(image.shape);f=w/(2*math.tan(1.22/2))
    body=np.stack((-(yy-h/2)/f*depth,-(xx-w/2)/f*depth,-depth-.08),axis=-1)
    world=body@quaternion_matrix(pose['quaternion']).T+np.asarray(pose['position'])
    mask=(valid&(world[:,:,2]>.35)&(world[:,:,2]<6.)).astype(np.uint8)
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    small=cv2.resize(frame,(w,h));hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV)
    result=[]
    for i in range(1,count):
        x,y,bw,bh,area=stats[i]
        if area<8:continue
        foreground=(labels==i).astype(np.uint8)*255
        hist=cv2.calcHist([hsv],[0,1],foreground,[16,8],[0,180,0,256]).ravel()
        hist/=max(1e-6,np.linalg.norm(hist))
        points=world[labels==i]
        top=points[points[:,2]>=np.percentile(points[:,2],65)]
        centre=np.median(top,axis=0).tolist()
        result.append({'box':[x/w*640,y/h*480,bw/w*640,bh/h*480],
                       'position':[centre[0],centre[1],0.],'surface_height':centre[2],
                       'appearance':hist})
    return result

def overlap(a,b):
    x,y,w,h=a;xx,yy,ww,hh=b
    shared=max(0.,min(x+w,xx+ww)-max(x,xx))*max(0.,min(y+h,yy+hh)-max(y,yy))
    return shared/max(1.,min(w*h,ww*hh))


class DepthVisual:
    """RGB appearance plus bounded 3D association, without actor/scene metadata."""
    method='RGB-depth continuity'
    close_mode=True
    def __init__(self,candidate,stamp,provider):
        self.signature=candidate['appearance'];self.last_position=candidate['position']
        self.box=candidate['box'];self.plane_height=candidate['surface_height']
        self.velocity=[0.,0.];self.stamp=stamp-1e-6;self.provider=provider;self.rivals=[]

    @classmethod
    def seed(cls,row,frame,packet,pose,stamp,provider,debug=None):
        if debug is not None:debug.update(age=row.get('age') if row else None,depth_skew=abs(packet['time']-stamp) if packet else None,identity=row.get('identity_confidence') if row else None)
        if row is None or row['age']>.5 or row['ambiguous'] or row.get('identity_confidence',1.)<.8:return None
        candidates=surface_candidates(frame,packet,pose,stamp)
        signature=appearance(frame,row['box'],row['class']=='person')
        if debug is not None:debug['candidates']=[{'box':c['box'],'overlap':overlap(c['box'],row['box']),'appearance':similarity(signature,c['appearance']),'height':c['surface_height']} for c in candidates][:8]
        candidates=[c for c in candidates if overlap(c['box'],row['box'])>.25
                    and similarity(signature,c['appearance'])>=.65]
        if len(candidates)!=1:return None
        return cls(candidates[0],stamp,provider)

    def update(self,frame,stamp,pose=None):
        self.rivals=[]
        if pose is None or not 0<stamp-self.stamp<=.8:return None
        dt=stamp-self.stamp;pred=[self.last_position[i]+self.velocity[i]*dt for i in range(2)]
        matches=[]
        for c in surface_candidates(frame,self.provider(stamp),pose,stamp):
            app=similarity(self.signature,c['appearance'])
            gap=math.dist(pred,c['position'][:2])
            if app<.78 or gap>1.5+dt*2. or abs(c['surface_height']-self.plane_height)>.65:continue
            matches.append((gap+.8*(1-app),c,app))
        matches.sort(key=lambda x:x[0])
        if not matches:return None
        if len(matches)>1 and matches[1][0]-matches[0][0]<.5:
            self.rivals=[x[1]['box'] for x in matches[:2]];return None
        _,best,app=matches[0]
        if dt>.02:
            velocity=[(best['position'][i]-self.last_position[i])/dt for i in range(2)]
            self.velocity=[.8*self.velocity[i]+.2*max(-6.,min(6.,velocity[i])) for i in range(2)]
        self.last_position=best['position'];self.box=best['box'];self.stamp=stamp
        self.plane_height=best['surface_height']
        return self.box,min(.98,.7+.25*app)


def localize_detections(detections,candidates):
    """Keep detector and visual-continuity positions on the same measured surface."""
    result=[]
    for det in detections:
        matching=[c for c in candidates if overlap(c['box'],det['box'])>.25]
        row=dict(det)
        if len(matching)==1:row['position']=list(matching[0]['position'])
        result.append(row)
    return result
