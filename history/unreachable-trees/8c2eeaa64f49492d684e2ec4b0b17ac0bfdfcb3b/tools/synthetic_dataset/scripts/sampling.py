"""Quota based independent factor schedules and one immutable scene per sample."""
import math
import random
import numpy as np
from common import canonical, digest
from geometry import (quaternion, rotation, project_points, ground_ray, footprint,
                      footprint_radius, distance_category, clip_box)


def seeded(master, key):
    return int(digest(f'{master}:{key}')[:16],16)


def weighted(rng, weights):
    return rng.choices(list(weights),weights=list(weights.values()),k=1)[0]


def schedule(values,count,seed):
    result=[values[i%len(values)] for i in range(count)]
    random.Random(seed).shuffle(result)
    return result


def split_schedule(count, fractions, seed):
    train=int(count*fractions['train']);val=int(count*fractions['val'])
    result=['train']*train+['val']*val+['test']*(count-train-val)
    random.Random(seed).shuffle(result)
    return result


def projected_geometry(asset,pose,camera,cam):
    points=np.asarray(asset['geometry_points'])@rotation(pose['quaternion']).T+pose['position']
    uv=project_points(points,camera,cam)
    if uv is None: return None
    return [float(uv[:,0].min()),float(uv[:,1].min()),float(uv[:,0].max()),float(uv[:,1].max())]


class Sampler:
    def __init__(self,cfg,count,seed):
        self.cfg,self.count,self.seed=cfg,count,seed
        self.assets={a['asset_id']:a for a in cfg['assets']}
        s=cfg['sampling']
        self.splits=split_schedule(count,cfg['split_fractions'],seeded(seed,'split'))
        self.factors={key:schedule(values,count,seeded(seed,key)) for key,values in
                      [('altitude',s['altitude_buckets_m']),('angle',s['off_nadir_buckets_deg']),
                       ('lighting',list(cfg['lighting'])),('background',cfg['backgrounds'])]}
        for split in cfg['split_fractions']:
            indices=[i for i,x in enumerate(self.splits) if x==split]
            for key,values in [('altitude',s['altitude_buckets_m']),('angle',s['off_nadir_buckets_deg']),
                               ('lighting',list(cfg['lighting'])),('background',cfg['backgrounds'])]:
                quota=schedule(values,len(indices),seeded(seed,key+split))
                for i,value in zip(indices,quota): self.factors[key][i]=value
        n=int(count*s['negative_ratio']);d=int(count*s['distractor_only_ratio'])
        self.kinds=['negative']*n+['distractor_only']*d+['positive']*(count-n-d)
        random.Random(seeded(seed,'kind')).shuffle(self.kinds)
        self.backgrounds=[a for a in cfg['assets'] if a['category']=='background']

    def scene(self,index):
        c=self.cfg;s=c['sampling'];rng=random.Random(seeded(self.seed,index));split=self.splits[index]
        altitude=self.factors['altitude'][index];angle=self.factors['angle'][index]
        background=self.factors['background'][index];lighting=self.factors['lighting'][index]
        candidates=[a for a in self.backgrounds if a['family']==background and split in a['eligibility']
                    and (split!='test' or a['held_out'])]
        material=rng.choice(candidates);zone=self.backgrounds.index(material)*c['world']['zone_spacing_m']
        height=altitude+rng.uniform(-s['altitude_jitter_m'],s['altitude_jitter_m'])
        actual_angle=max(0,angle+rng.uniform(-s['angle_jitter_deg'],s['angle_jitter_deg']))
        yaw=rng.uniform(*s['camera_yaw_deg']);roll=math.radians(rng.uniform(-s['roll_jitter_deg'],s['roll_jitter_deg']))
        pitch=math.pi/2-math.radians(actual_angle)
        camera={'position':[zone,0,height+c['world']['ground_z']], 'quaternion':quaternion(roll,pitch,math.radians(yaw)),
                'roll':roll,'pitch':pitch,'yaw':math.radians(yaw),'viewing_azimuth_deg':yaw,
                'nominal_altitude_m':altitude,'altitude_agl_m':height,'ground_reference_z':c['world']['ground_z'],
                'nominal_off_nadir_deg':angle,'actual_off_nadir_deg':actual_angle}
        center=ground_ray(c['camera']['cx'],c['camera']['cy'],camera,c['camera'],c['world']['ground_z'])[:2]
        polygon=footprint(camera,c['camera'],c['world']['ground_z'])
        l=c['lighting'][lighting];elev=rng.uniform(*l['elevation_deg']);az=rng.uniform(*l['azimuth_deg'])
        er,ar=math.radians(elev),math.radians(az)
        light={'family':lighting,'elevation_deg':elev,'azimuth_deg':az,'intensity':rng.uniform(*l['intensity']),
               'color':l['color'],'direction':[-math.cos(er)*math.cos(ar),-math.cos(er)*math.sin(ar),-math.sin(er)],
               'ambient':c['world']['ambient'],'cast_shadows':True}
        kind=self.kinds[index];objects=[];used={}
        planned=0 if kind!='positive' else rng.choices(list(range(1,9)),weights=s['object_count_weights'],k=1)[0]
        for j in range(planned):
            cls=rng.choice(c['classes'])
            pool=[a for a in c['assets'] if a['category']==cls['name'] and split in a['eligibility']
                  and used.get(a['asset_id'],0)<c['world']['pool_copies_per_variant']]
            if not pool: break
            asset=rng.choice(pool);slot=used.get(asset['asset_id'],0)
            radius=math.hypot(*asset['physical_dimensions_m'][:2])/2
            placed=None
            for attempt in range(s['placement_attempts']):
                band=weighted(rng,s['distance_weights']);low,high=s['distance_bands'][band]
                fraction=rng.uniform(low,high);azimuth=rng.uniform(0,2*math.pi);direction=np.array([math.cos(azimuth),math.sin(azimuth)])
                boundary=footprint_radius(center,direction,polygon,camera,c['camera'])
                xy=center+direction*boundary*fraction;object_yaw=rng.uniform(*s['object_yaw_deg'])
                pose={'position':[float(xy[0]),float(xy[1]),c['world']['ground_z']],
                      'quaternion':quaternion(0,0,math.radians(object_yaw))}
                if any(np.linalg.norm(xy-np.asarray(o['pose']['position'][:2])) < radius+o['footprint_radius_m']+s['min_spacing_m'] for o in objects): continue
                box=projected_geometry(asset,pose,camera,c['camera']);clipped=clip_box(box,c['camera'])
                if clipped is None: continue
                if band!='edge' and (box[0]<2 or box[1]<2 or box[2]>c['camera']['width']-2 or box[3]>c['camera']['height']-2): continue
                placed=dict(instance_id=f"pool_{asset['asset_id']}_{slot}",asset_id=asset['asset_id'],
                            class_name=cls['name'],class_id=cls['yolo_id'],gazebo_label=cls['gazebo_label'],
                            pose=pose,yaw_deg=object_yaw,physical_dimensions_m=asset['physical_dimensions_m'],
                            distance_category=band,horizontal_range_m=float(np.linalg.norm(xy-np.asarray(camera['position'][:2]))),
                            slant_range_m=float(np.linalg.norm(np.asarray(pose['position'])-camera['position'])),
                            normalized_footprint_distance=fraction,footprint_reference=center.tolist(),
                            usable_direction_radius_m=boundary,footprint_radius_m=radius)
                break
            if placed:
                objects.append(placed);used[asset['asset_id']]=slot+1
        if kind=='positive' and not objects:
            raise ValueError('No target fits in usable footprint')
        clutter=[]
        if kind!='negative':
            number=rng.randint(*s['distractor_count'])
            for k in range(number):
                for _ in range(s['placement_attempts']):
                    xy=center+np.array([rng.uniform(-1,1),rng.uniform(-1,1)])*height*.8
                    if all(np.linalg.norm(xy-np.asarray(o['pose']['position'][:2]))>o['footprint_radius_m']+2 for o in objects): break
                else: continue
                clutter.append({'instance_id':f'clutter_{k}','pose':{'position':[float(xy[0]),float(xy[1]),c['world']['ground_z']],
                                                                  'quaternion':quaternion(0,0,rng.uniform(0,2*math.pi))}})
        occlusion=weighted(rng,s['occlusion_weights']) if objects else 'none'
        if objects and occlusion!='none':
            first=objects[0];x,y,_=first['pose']['position']
            # A supported canopy above the target, no target/occluder solid intersection.
            clutter.append({'instance_id':'canopy_'+occlusion,'pose':{'position':[x+first['physical_dimensions_m'][0]*.45,y,c['world']['ground_z']],
                                                                      'quaternion':quaternion(0,0,0)}})
        if objects and lighting=='shadow':
            for target in objects:
                x,y,_=target['pose']['position'];offset=target['footprint_radius_m']+3.5
                xy=np.array([x+math.cos(ar)*offset,y+math.sin(ar)*offset])
                if all(np.linalg.norm(xy-np.asarray(o['pose']['position'][:2]))>o['footprint_radius_m']+3.1+s['min_spacing_m'] for o in objects):
                    clutter.append({'instance_id':'shadow_wall','pose':{'position':[float(xy[0]),float(xy[1]),c['world']['ground_z']],
                                                                       'quaternion':quaternion(0,0,ar+math.pi/2)}})
                    break
        scene={'frame_id':f'scene_{seeded(self.seed,index):016x}_{index:06d}','scene_id':f'{self.seed}:{index}',
               'scene_family':f'{self.seed}:{index}','index':index,'split':split,'master_seed':self.seed,
               'scene_seed':seeded(self.seed,index),'kind':kind,'camera':camera,'lighting':light,
               'background':{'family':background,'asset_id':material['asset_id'],'zone_x_m':zone,
                             'texture_rotation_deg':0,'texture_scale':1,'texture_offset':[0,0]},
               'objects':objects,'distractors':clutter,'planned_target_count':planned,
               'placement_shortfall':planned-len(objects),'occlusion_requested':occlusion}
        scene['scenario_sha256']=digest(canonical({k:v for k,v in scene.items() if k not in
                                                   ('frame_id','scene_id','scene_family','index','split','master_seed','scene_seed')}))
        return scene
