"""Follow one operator-selected camera track, with bounded loss handling."""
import math
from .tracking import similarity
from .service import CloseApproach

class Follow:
    def __init__(self,target_id,did,now,config,public_paths=None):
        self.target_id=target_id;self.drone_id=did;self.state='REACQUIRING';self.entered=now
        self.started=now;self.tracking_started=None;self.lost_since=now;self.reason=None;self.outcome=None;self.timeline=[];self.config=config
        self.close=CloseApproach(config)
        self.initial_ground=None;self.cancelled=False;self.finished_at=None;self.loss_at=None;self.public_paths=public_paths or [];self.search_anchor=None;self.search_goal=None;self.filtered_goal=None;self.goal_time=now
    def phase(self,state,now,detail):
        if self.state==state:return
        self.state=state;self.entered=now;self.timeline.append({'time':round(now,2),'state':state,'detail':detail});self.timeline=self.timeline[-80:]
    def finish(self,engine,reason,outcome='finished'):
        # A repeated stop/recall must preserve an approach already under way.
        if self.cancelled:return
        self.close.stop(engine.now(),reason)
        gz=getattr(getattr(engine,'runtime',None),'gz',None)
        if hasattr(gz,'proximity'):gz.proximity(self.drone_id,False)
        vision=getattr(engine,'vision',None)
        if hasattr(vision,'depth_targets'):vision.depth_targets.pop(self.drone_id,None)
        if hasattr(vision,'close_observations'):vision.close_observations.pop(self.drone_id,None)
        self.reason=reason;self.outcome=outcome;self.cancelled=True;self.finished_at=engine.now()
        if outcome=='lost':self.phase('LOST',engine.now(),reason)
        self.phase('RETURNING',engine.now(),reason)
        d=engine.drones[self.drone_id]
        if d['deployed']:engine.transition(d,'RETURNING',reason)
    def tick(self,engine,d,pos,alt):
        now=engine.now();registry=engine.vision.registry;target=registry.get(self.target_id,now)
        if self.loss_at is not None:
            if now-self.loss_at>=self.config.loiter_seconds:self.finish(engine,'Lost-target loiter completed','lost');return
            p=(target or {}).get('predicted_position',pos)
            angle=(now-self.loss_at)*.4;radius=self.config.loiter_radius if self.config.no_target_policy=='loiter' else 0.
            engine.set_goal(d,[p[0]+radius*math.cos(angle),p[1]+radius*math.sin(angle),alt]);return
        if self.tracking_started is not None and now-self.tracking_started>=self.config.tracking_seconds:
            self.finish(engine,'Tracking duration completed');return
        if now-self.started>self.config.tracking_seconds+self.config.reacquire_seconds+100:
            self.finish(engine,'Maximum airborne tracking budget reached');return
        if target is None:self.finish(engine,'Selected camera track expired','lost');return
        if self.close.active and self.close.tick(engine,d,pos,alt,target):return
        fresh=target['age']<1. and not target['ambiguous'] and target['identity_confidence']>=self.config.reacquire_confidence
        if fresh:
            if max(abs(target['position'][0]),abs(target['position'][1]))>self.config.flight_boundary+max(1.,target['uncertainty_m']):
                self.finish(engine,'Target left the operating boundary','left-area');return
            self.lost_since=None;self.search_anchor=None;self.search_goal=None
            if self.tracking_started is None:self.tracking_started=now
            self.phase('TRACKING',now,'Selected identity confirmed in fresh camera observations')
            if d['state']!='TARGET_TRACKING':engine.transition(d,'TARGET_TRACKING','Following selected camera identity')
            velocity=target['velocity'];speed=math.hypot(*velocity)
            # Reserve image space for the whole object plus aircraft tilt. These
            # are class-wide size estimates, never the simulator actor's geometry.
            span={'person':1.8,'car':4.5,'truck':7.8,'bus':8.5}.get(target['class'],4.5)
            half_view=(alt-.8)*math.tan(1.22/2)*480/640
            centre_budget=max(.5,half_view-span/2-alt*.2)
            offset=min(self.config.tracking_distance,centre_budget)/max(.1,speed)
            goal=[target['position'][0]+velocity[0]*(.6-offset),target['position'][1]+velocity[1]*(.6-offset),alt]
            # Bound changes of the observed follow goal. Pixel-box corrections
            # can jump while the same physical target continues walking; avoid
            # requesting abrupt reversals that tilt it out of the nadir image.
            if self.filtered_goal is not None:
                dt=max(0.,min(.25,now-self.goal_time));gap=math.dist(goal[:2],self.filtered_goal[:2]);step=self.config.flight_speed*dt
                if gap>step and gap>0:
                    goal=[self.filtered_goal[i]+(goal[i]-self.filtered_goal[i])*step/gap for i in range(2)]+[alt]
            self.filtered_goal=list(goal);self.goal_time=now
            # A nadir camera needs no heading alignment; retaining launch heading
            # avoids rotating the image whenever a noisy velocity changes sign.
            d['target']=target;engine.set_goal(d,goal)
            d['tracking_image_age']=target['age'];d['tracking_identity']=target['identity_confidence']
        else:
            self.filtered_goal=None
            if self.lost_since is None:self.lost_since=now
            lost_for=now-self.lost_since
            if lost_for>=self.config.reacquire_seconds:
                if self.config.no_target_policy!='return' and self.config.loiter_seconds>0:
                    self.loss_at=now;self.phase('LOST',now,'Selected target could not be reacquired in time');self.phase('LOITERING',now,'Configured lost-target wait before return');engine.transition(d,'TARGET_LOITERING','Lost-target wait');return
                self.finish(engine,'Selected target could not be reacquired in time','lost');return
            predicted=target['predicted_position']
            if self.search_anchor is None:self.search_anchor=now
            if self.tracking_started is not None and lost_for<2:
                self.phase('OCCLUDED',now,'Short camera gap; bounded movement estimate')
                engine.set_goal(d,[*predicted[:2],alt]);return
            self.phase('REACQUIRING' if self.tracking_started is None else 'SEARCHING',now,
                       'Identity uncertain; bounded search, operator confirmation available')
            if d['state']!='TARGET_SEARCHING':engine.transition(d,'TARGET_SEARCHING','Searching for selected identity')
            # A widening search around the bounded movement estimate, never actor truth.
            radius=min(45.,max(2.,target['uncertainty_m'],target['age']*.9,lost_for*.5))
            angle=(now-self.entered)*self.config.flight_speed/max(2.,radius)
            velocity=target['velocity'];speed=math.hypot(*velocity)
            if speed>.25:
                # Search a bounded sector ahead of the last measured heading.
                ux,uy=velocity[0]/speed,velocity[1]/speed
                forward=radius*(.6+.25*math.cos(angle));lateral=radius*.55*math.sin(angle)
                goal=[predicted[0]+ux*forward-uy*lateral,predicted[1]+uy*forward+ux*lateral,alt]
            else:goal=[predicted[0]+radius*math.cos(angle),predicted[1]+radius*math.sin(angle),alt]
            from .navigation import public_search_candidate
            public=public_search_candidate(self.public_paths,target['position'],target['velocity'],target['age'],now-self.search_anchor,'sidewalk' if target['class']=='person' else 'vehicle')
            if public is not None:goal=[*public,alt]
            self.search_goal=goal;engine.set_goal(d,goal)
    def candidates(self,registry,now):
        with registry.lock:
            source=registry.tracks.get(self.target_id)
            if source is None:return []
            result=[]
            for candidate in registry.snapshot(now):
                if candidate['id']==self.target_id or candidate['class']!=source['class'] or candidate['age']>1:continue
                appearance=similarity(source['_appearance'],registry.tracks[candidate['id']]['_appearance'])
                if appearance>=.78:result.append({'id':candidate['id'],'appearance_similarity':round(appearance,3),'age':candidate['age']})
            return sorted(result,key=lambda c:-c['appearance_similarity'])[:5]
    def snapshot(self,registry,now):
        return {'target_id':self.target_id,'drone_id':self.drone_id,'state':self.state,'reason':self.reason,'outcome':self.outcome,
                'elapsed':round(max(0,(self.finished_at or now)-(self.tracking_started if self.tracking_started is not None else now)),2),'duration':self.config.tracking_seconds,
                'close_approach':self.close.snapshot(now),'timeline':self.timeline,'search_goal':self.search_goal,'candidates':self.candidates(registry,now) if self.state in ('REACQUIRING','SEARCHING','OCCLUDED') else []}
