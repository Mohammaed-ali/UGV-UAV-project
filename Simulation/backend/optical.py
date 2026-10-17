"""Selected-object optical continuity between sparse detector observations.

Tracks foreground image features with forward/backward checks and RANSAC.
It cannot discover a new class or recover a lost identity without detector input.
"""
import cv2
import numpy as np
from .tracking import appearance,similarity


def compensated_seed(frame,box,old_pose,new_pose,plane_height=0.):
    """Reproject a captured anchor using calibrated poses, never target truth.

    This is an initialization hypothesis. It becomes a sighting only after the
    tracker matches the current camera image. Height is a class-wide approximation.
    """
    import math
    from .transport import quaternion_matrix
    from .vision import camera_to_world
    h,w=frame.shape[:2];f=w/(2*math.tan(1.22/2))
    source=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
    origin=camera_to_world([0,0,0],old_pose);rotation=quaternion_matrix(new_pose['quaternion'])
    destination=[]
    for u,v in source:
        ray=camera_to_world([(u-w/2)/f,(v-h/2)/f,1],old_pose)-origin
        if ray[2]>=-.1:return None
        world=origin+ray*(plane_height-origin[2])/ray[2]
        body=rotation.T@(world-np.asarray(new_pose['position']));depth=-body[2]-.08
        if depth<1:return None
        destination.append([w/2-f*body[1]/depth,h/2-f*body[0]/depth])
    matrix=cv2.getPerspectiveTransform(source,np.float32(destination))
    x,y,bw,bh=box;corners=np.float32([[[x,y],[x+bw,y],[x+bw,y+bh],[x,y+bh]]])
    moved=cv2.perspectiveTransform(corners,matrix)[0];low=np.maximum(moved.min(0),[0,0]);high=np.minimum(moved.max(0),[w-1,h-1])
    size=high-low
    if min(size)<8:return None
    warped=cv2.warpPerspective(frame,matrix,(w,h),borderValue=(114,114,114))
    return warped,[*low,*size]

def interior_patch(box,fraction=.5,cap=None):
    """A central part of an already identified image object, never a new ID."""
    x,y,w,h=box
    bw=max(8.,min(w,w*fraction,cap if cap is not None else w))
    bh=max(8.,min(h,h*fraction,cap if cap is not None else h))
    return [x+(w-bw)/2,y+(h-bh)/2,bw,bh]

class Optical:
    def __init__(self,frame,box,stamp,pose=None,plane_height=0.,person_guard=False,close_mode=False):
        self.close_mode=close_mode
        self.gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY);self.box=list(box);self.stamp=stamp
        x,y,w,h=box;self.corners=np.array([[x,y,1],[x+w,y,1],[x,y+h,1],[x+w,y+h,1]],dtype=float)
        self.signature=appearance(frame,box,person_guard);self.points=self.features(frame,box)
        self.method='CSRT' if hasattr(cv2,'TrackerCSRT_create') else 'optical-flow'
        self.correlation=None;self.initial_update=True
        self.frame=frame.copy();self.pose=pose;self.plane_height=plane_height;self.rivals=[];self.person_guard=person_guard
        self.shirt_hue=None;self.shirt_area=0;self.shirt_box_area=max(1.,box[2]*box[3]);self.clothing_present=True
        if person_guard:
            x,y,w,h=box;roi=frame[max(0,int(y+h*.12)):int(y+h*.88),max(0,int(x+w*.15)):int(x+w*.85)]
            if roi.size:
                hsv=cv2.cvtColor(roi,cv2.COLOR_BGR2HSV);colours=hsv[:,:,0][(hsv[:,:,1]>60)&(hsv[:,:,2]>45)]
                if len(colours)>=12:
                    histogram=np.bincount(colours//6,minlength=30);self.shirt_hue=int(histogram.argmax()*6+3);self.shirt_area=int(histogram.max())
        if self.method=='CSRT':self.rebase(frame,box)
    def rebase(self,frame,box):
        # Reinitialize geometry after a camera transform; preserve the original
        # appearance signature so rebasing cannot bless a different object.
        self.box=list(box);self.gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        x,y,w,h=box;self.corners=np.array([[x,y,1],[x+w,y,1],[x,y+h,1],[x+w,y+h,1]],dtype=float)
        self.points=self.features(frame,box)
        if self.method=='CSRT':
            parameters=cv2.TrackerCSRT_Params();parameters.template_size=160;parameters.admm_iterations=2;parameters.number_of_scales=17
            self.correlation=cv2.TrackerCSRT_create(parameters);self.correlation.init(frame,tuple(map(int,box)))
    def similar_regions(self,frame,box,pose):
        # Conservative pixel-only identity guard. It does not classify a new
        # person or add a catalogue sighting; it challenges an optical lock when
        # a separate nearby region shares the original saturated clothing colour.
        if not self.person_guard or self.shirt_hue is None or pose is None:return []
        import math
        hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV);delta=np.abs(hsv[:,:,0].astype(float)-self.shirt_hue)
        mask=((np.minimum(delta,180-delta)<12)&(hsv[:,:,1]>60)&(hsv[:,:,2]>45)).astype(np.uint8)
        _,_,stats,centres=cv2.connectedComponentsWithStats(mask,8)
        x,y,w,h=box;cx,cy=x+w/2,y+h/2
        pixels_per_m=frame.shape[1]/(2*math.tan(1.22/2))/max(2.,pose['position'][2]-.6)
        # A shifted optical box containing only pavement can still have a
        # similar whole-box histogram. The real person outside that box is
        # then a lost lock, not a second identity. Require current clothing
        # pixels inside the tracked box before raising a lookalike dispute.
        roi=mask[max(0,int(y)):min(frame.shape[0],int(y+h)),max(0,int(x)):min(frame.shape[1],int(x+w))]
        scale=w*h/self.shirt_box_area
        self.clothing_present=int(roi.sum())>=max(8,self.shirt_area*.2*scale)
        if not self.clothing_present:return []
        matches=[]
        for bounds,centre in zip(stats[1:],centres[1:]):
            if bounds[4]<max(8,self.shirt_area*.25):continue
            u,v=centre
            if x-w*.2<=u<=x+w*1.2 and y-h*.2<=v<=y+h*1.2:continue
            gap=math.hypot(u-cx,v-cy)
            if max(.8*pixels_per_m,.7*max(w,h))<gap<3.*pixels_per_m:matches.append(bounds[:4].astype(float).tolist())
        return matches
    def features(self,frame,box):
        h,w=frame.shape[:2];x,y,bw,bh=map(int,box);x=max(0,x);y=max(0,y);xa=min(w,x+bw);ya=min(h,y+bh)
        mask=np.zeros((h,w),np.uint8)
        if xa-x<5 or ya-y<5:return None
        lab=cv2.cvtColor(frame,cv2.COLOR_BGR2LAB).astype(np.float32)
        outer=lab[max(0,y-5):min(h,ya+5),max(0,x-5):min(w,xa+5)]
        background=np.median(outer.reshape(-1,3),axis=0)
        difference=np.linalg.norm(lab[y:ya,x:xa]-background,axis=2)
        foreground=(difference>18).astype(np.uint8)*255
        # Corner detection is constrained to object pixels, reducing pavement drift.
        mask[y:ya,x:xa]=foreground
        return cv2.goodFeaturesToTrack(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),maxCorners=45,qualityLevel=.015,minDistance=2,mask=mask,blockSize=3)
    def update(self,frame,stamp,pose=None):
        if stamp<=self.stamp or stamp-self.stamp>(1.5 if self.initial_update else 1.)+1e-6:return None
        if pose is not None and self.pose is not None:
            movement=np.linalg.norm(np.asarray(pose['position'])-self.pose['position'])
            rotation=abs(float(np.dot(pose['quaternion'],self.pose['quaternion'])))
            if movement>.02 or rotation<.99998:
                corrected=compensated_seed(self.frame,self.box,self.pose,pose,self.plane_height)
                if corrected is None:return None
                self.rebase(*corrected)
        if self.correlation is not None:
            # The first current image may follow a slow detector result. Later
            # updates keep the original one-second continuity limit.
            if stamp<=self.stamp or stamp-self.stamp>(1.5 if self.initial_update else 1.)+1e-6:return None
            self.initial_update=False
            found,box=self.correlation.update(frame)
            if not found:return None
            x,y,w,h=box;height,width=frame.shape[:2]
            if x<0 or y<0 or x+w>width or y+h>height or min(w,h)<6:return None
            app=similarity(self.signature,appearance(frame,box,self.person_guard))
            if app<.72:return None
            self.rivals=self.similar_regions(frame,box,pose)
            if self.rivals or not self.clothing_present:return None
            if self.close_mode and max(w/width,h/height)>.45:
                box=interior_patch(box);self.rebase(frame,box)
            self.box=list(box);self.stamp=stamp;self.frame=frame.copy();self.pose=pose
            return self.box,float(min(.98,.7+.25*app))
        if self.points is None or len(self.points)<4 or stamp<=self.stamp or stamp-self.stamp>1.:return None
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        current,status,_=cv2.calcOpticalFlowPyrLK(self.gray,gray,self.points,None,winSize=(17,17),maxLevel=3)
        if current is None:return None
        back,back_status,_=cv2.calcOpticalFlowPyrLK(gray,self.gray,current,None,winSize=(17,17),maxLevel=3)
        if back is None:return None
        errors=np.linalg.norm(self.points-back,axis=2).reshape(-1)
        good=(status.reshape(-1)>0)&(back_status.reshape(-1)>0)&(errors<.8)
        if good.sum()<4 or good.mean()<.55:return None
        affine,inliers=cv2.estimateAffinePartial2D(self.points[good],current[good],method=cv2.RANSAC,ransacReprojThreshold=1.2)
        if affine is None or inliers is None or inliers.mean()<.65:return None
        scale=np.linalg.norm(affine[:,0])
        if scale<.75 or scale>1.3:return None
        corners=self.corners@affine.T
        minimum=corners.min(0);maximum=corners.max(0);box=[*minimum,*(maximum-minimum)]
        height,width=frame.shape[:2]
        if box[0]<0 or box[1]<0 or box[0]+box[2]>width or box[1]+box[3]>height or min(box[2:])<6:return None
        app=similarity(self.signature,appearance(frame,box,self.person_guard))
        if app<.78:return None
        self.rivals=self.similar_regions(frame,box,pose)
        if self.rivals or not self.clothing_present:return None
        quality=float(min(.98,.75+.15*app+.1*float(inliers.mean())))
        self.gray=gray;self.points=current[good][inliers.reshape(-1)>0];self.box=box;self.stamp=stamp;self.frame=frame.copy();self.pose=pose;self.initial_update=False
        self.corners=np.column_stack([corners,np.ones(4)])
        # Refresh feature locations from the foreground without changing the identity signature.
        if len(self.points)<12:
            replenished=self.features(frame,box)
            if replenished is not None and len(replenished)>=4:self.points=replenished
        return box,quality
