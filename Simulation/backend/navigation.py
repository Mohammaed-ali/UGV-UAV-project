"""Static-map aircraft routing. Does not know moving target truth."""
import math,heapq

class FlightPlanner:
    def __init__(self,buildings,boundary=116.):self.boundary=boundary;self.buildings=[o for o in buildings if o['kind']=='building'];self.cache={}
    def boxes(self,altitude):
        return [(o['x']-o['sx']/2-1.8,o['x']+o['sx']/2+1.8,o['y']-o['sy']/2-1.8,o['y']+o['sy']/2+1.8) for o in self.buildings if altitude<o['sz']+2.]
    def clear(self,a,b,boxes):
        for x0,x1,y0,y1 in boxes:
            low,high=0.,1.
            for p,q in [(-(b[0]-a[0]),a[0]-x0),(b[0]-a[0],x1-a[0]),(-(b[1]-a[1]),a[1]-y0),(b[1]-a[1],y1-a[1])]:
                if abs(p)<1e-9:
                    if q<0:break
                elif p<0:low=max(low,q/p)
                else:high=min(high,q/p)
                if low>high:break
            else:
                if low<=high:return False
        return True
    def goal(self,did,current,wanted):
        target=[max(-self.boundary,min(self.boundary,wanted[0])),max(-self.boundary,min(self.boundary,wanted[1])),wanted[2]];boxes=self.boxes(min(current[2],target[2]))
        for x0,x1,y0,y1 in boxes:
            if x0<target[0]<x1 and y0<target[1]<y1:
                candidates=[(x0-.2,target[1]),(x1+.2,target[1]),(target[0],y0-.2),(target[0],y1+.2)]
                target[:2]=min(candidates,key=lambda p:math.dist(p,current[:2]))
        if self.clear(current,target,boxes):self.cache.pop(did,None);return target
        old=self.cache.get(did)
        if old and math.dist(old['target'],target)<2. and old['path']:
            while len(old['path'])>1 and math.dist(current[:2],old['path'][0])<1.:old['path'].pop(0)
            if self.clear(current,old['path'][0],boxes):return [*old['path'][0],target[2]]
        nodes=[current[:2],target[:2]]
        for x0,x1,y0,y1 in boxes:nodes.extend([(x0-.2,y0-.2),(x0-.2,y1+.2),(x1+.2,y0-.2),(x1+.2,y1+.2)])
        costs={0:0.};parent={};queue=[(0.,0)]
        while queue:
            cost,i=heapq.heappop(queue)
            if cost!=costs[i]:continue
            if i==1:break
            for j,p in enumerate(nodes):
                if j==i or not self.clear(nodes[i],p,boxes):continue
                new=cost+math.dist(nodes[i],p)
                if new<costs.get(j,float('inf')):costs[j]=new;parent[j]=i;heapq.heappush(queue,(new,j))
        if 1 not in costs:return list(current)
        route=[];i=1
        while i!=0:route.append(nodes[i]);i=parent[i]
        route.reverse();self.cache[did]={'target':target,'path':route}
        return [*route[0],target[2]]


def public_search_candidate(paths,last_position,velocity,age,search_time,kind):
    """Hypothesis on public map geometry, without actor IDs or assigned routes."""
    speed=min(3.,math.hypot(*velocity))
    if speed<.25:return None
    matches=[]
    for path in paths:
        if path['kind']!=kind:continue
        points=path['points'];lengths=[0.]
        for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+math.dist(a,b))
        best=(float('inf'),0.,1.)
        for i,(a,b) in enumerate(zip(points,points[1:])):
            dx,dy=b[0]-a[0],b[1]-a[1];size=math.hypot(dx,dy)
            if size<1e-6:continue
            t=max(0.,min(1.,((last_position[0]-a[0])*dx+(last_position[1]-a[1])*dy)/(size*size)))
            distance=math.hypot(last_position[0]-a[0]-t*dx,last_position[1]-a[1]-t*dy)
            if distance<best[0]:best=(distance,lengths[i]+t*size,1. if dx*velocity[0]+dy*velocity[1]>=0 else -1.)
        if best[0]<4.:matches.append((best[0]+len(points)*.0001,points,lengths,best))
    if not matches:return None
    _,points,lengths,(_,s,direction)=min(matches,key=lambda m:m[0])
    # Extended search hypotheses are bounded to 120 m of observed-motion extrapolation and
    # 8 m of scanning. They do not refresh a track or imply a confirmed sighting.
    s=(s+direction*(min(120.,speed*min(age,120.))+8.*math.sin(search_time*.18)))%lengths[-1]
    for i,(a,b) in enumerate(zip(points,points[1:])):
        if lengths[i+1]>=s:
            fraction=(s-lengths[i])/max(1e-6,lengths[i+1]-lengths[i]);return [a[0]+fraction*(b[0]-a[0]),a[1]+fraction*(b[1]-a[1])]
    return None
