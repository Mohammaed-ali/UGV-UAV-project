"""Human frame/instance balance, explicit acceptance and evaluation file lists."""
from collections import Counter, defaultdict
from storage import distribution


def person_band(count):
    if count==0:return '0'
    if count==1:return '1'
    if count<=3:return '2_3'
    if count<=6:return '4_6'
    if count<=10:return '7_10'
    return '11_plus'


def visible_people(record):
    return [o for o in record['objects'] if o['class_name']=='person' and o['label_state']=='labelled']


def size_band(box, thresholds):
    area=(box[2]-box[0])*(box[3]-box[1])
    for name in ('very_small','small','medium'):
        if area<thresholds[name]:return name
    return 'large'


def human_statistics(records,cfg):
    priority=cfg['human_priority'];thresholds=priority['size_area_thresholds_px'];tol=priority['quota_tolerance']
    result={'definition':'Visible person counts use exported valid native boxes. Ignored tiny/occluded persons are counted separately, never silently dropped.',
            'pixel_area_thresholds_px':thresholds,'quota_tolerance_absolute_fraction':tol,'splits':{},'acceptance':{}}
    factors={'altitude':lambda r:str(r['camera']['nominal_altitude_m']), 'angle':lambda r:str(r['camera']['nominal_off_nadir_deg']),
             'background':lambda r:r['background']['family'],'lighting':lambda r:r['lighting']['family']}
    for split in cfg['split_fractions']:
        rows=[r for r in records if r['split']==split];categories=Counter();hist=Counter();instances=Counter();mixed=Counter()
        labelled=[];planned=[];ignored=Counter();tables={k:Counter() for k in list(factors)+['distance','asset','pixel_size','occlusion_requested']}
        boxes=defaultdict(list)
        for r in rows:
            people=visible_people(r);vehicles=[o for o in r['objects'] if o['class_name']!='person' and o['label_state']=='labelled']
            category='human_positive' if people else 'vehicle_only' if vehicles else 'distractor_only' if r['kind']=='distractor_only' else 'empty' if r['kind']=='negative' else 'all_targets_ignored'
            categories[category]+=1;band=person_band(len(people));hist[band]+=1;instances[band]+=len(people)
            planned.extend(o for o in r['objects'] if o['class_name']=='person');labelled.extend(people)
            if people:
                for cls in sorted(set(o['class_name'] for o in vehicles)):mixed[cls]+=1
                if vehicles:mixed['any_vehicle']+=1
            for o in r['objects']:
                if o['class_name']=='person' and o['label_state']!='labelled':ignored[o['label_state']]+=1
            for o in people:
                b=o['bbox_px'];w=b[2]-b[0];h=b[3]-b[1];area=w*h
                for name,fn in factors.items():tables[name][fn(r)]+=1
                for name,key in [('distance','distance_category'),('asset','asset_id')]:tables[name][o[key]]+=1
                tables['pixel_size'][size_band(b,thresholds)]+=1;tables['occlusion_requested'][r['occlusion_requested']]+=1
                for name,key in [('all','all'),('altitude',factors['altitude'](r)),('angle',factors['angle'](r)),('distance',o['distance_category'])]:
                    boxes[(name,key)].append((w,h,area))
        human_frames=categories['human_positive'];multi=sum(n for k,n in hist.items() if k not in ('0','1'))
        stats={'training_or_evaluation_images':len(rows),'composition_visible':dict(categories),
               'composition_requested':dict(Counter(r.get('composition_requested','legacy') for r in rows)),
               'person_frames':human_frames,'person_frame_fraction':human_frames/max(1,len(rows)),
               'single_person_frames':hist['1'],'multi_person_frames':multi,'visible_person_count_histogram':dict(hist),
               'person_instances_labelled':len(labelled),'person_instances_all_including_ignored':len(planned),
               'instances_by_scene_person_count':dict(instances),'ignored_persons':dict(ignored),
               'mixed_person_vehicle_frames':dict(mixed),'vehicle_labelled_instances':dict(Counter(o['class_name'] for r in rows for o in r['objects'] if o['class_name']!='person' and o['label_state']=='labelled')),
               'labelled_person_instances_by':{k:dict(v) for k,v in tables.items()},'bbox_distributions':{}}
        for (name,key),values in boxes.items():
            stats['bbox_distributions'].setdefault(name,{})[key]={metric:distribution([x[i] for x in values]) for i,metric in enumerate(['width_px','height_px','area_px'])}
        stats['pixel_size_percentages']={k:100*v/max(1,len(labelled)) for k,v in tables['pixel_size'].items()}
        result['splits'][split]=stats
    errors=[];train=result['splits']['train'];n=train['training_or_evaluation_images'];human=train['person_frames'];multi=train['multi_person_frames']
    if n:
        for k,target in cfg['scene_composition']['train'].items():
            observed=train['composition_visible'].get(k,0)/n
            if abs(observed-target)>tol:errors.append(f'TRAIN visible {k} fraction {observed:.4f} outside {target:.4f} +/- {tol}')
        for k,key in [('single','single_person_frames'),('multi','multi_person_frames')]:
            observed=train[key]/max(1,human);target=priority['train_scene_counts'][k]
            if abs(observed-target)>tol:errors.append(f'TRAIN human {k} fraction {observed:.4f} outside target {target:.4f}')
        for k,target in priority['multi_count_distribution'].items():
            observed=train['visible_person_count_histogram'].get(k,0)/max(1,multi)
            if abs(observed-target)>tol:errors.append(f'TRAIN multi-person {k} fraction {observed:.4f} outside target {target:.4f}')
        for k,target in priority['distance_weights'].items():
            observed=train['labelled_person_instances_by']['distance'].get(k,0)/max(1,train['person_instances_labelled'])
            if abs(observed-target)>tol:errors.append(f'TRAIN person distance {k} fraction {observed:.4f} outside target {target:.4f}')
        if train['mixed_person_vehicle_frames'].get('any_vehicle',0)/max(1,human)<priority['minimum_substantial_mixed_fraction']:
            errors.append('Insufficient TRAIN human + vehicle scenes')
    # Small technical determinism/crash runs are not a distribution acceptance gate.
    distribution_required=len(records)>=200
    if distribution_required:
        for name,levels in [('altitude',cfg['sampling']['altitude_buckets_m']),('angle',cfg['sampling']['off_nadir_buckets_deg']),('background',cfg['backgrounds']),('lighting',cfg['lighting'])]:
            present={k for split in result['splits'].values() for k,v in split['labelled_person_instances_by'][name].items() if v}
            missing=set(map(str,levels))-present
            if missing:errors.append('Missing valid person '+name+' levels: '+str(sorted(missing)))
        for split in ('val','test'):
            if cfg['scene_composition'][split]==cfg['scene_composition']['train']:errors.append(split+' blindly copies TRAIN oversampling')
            coverage=result['splits'][split]
            if not coverage['person_frames'] or any(not coverage['vehicle_labelled_instances'].get(k) for k in ('car','truck','bus')):errors.append(split+' class coverage incomplete')
    result['acceptance']={'status':'PASSED' if not errors else 'FAIL','errors':errors,'required_for_this_count':distribution_required,
                          'note':'Configured approximate quotas assess valid visible boxes. Small run ratios are diagnostic only; no distribution gate is opened.'}
    return result


def evaluation_subsets(records,cfg):
    subsets={name:[] for name in ['test_person_all','test_person_single','test_person_multi','test_person_small','test_person_far','test_person_occluded','test_person_shadow']}
    for r in records:
        if r['split']!='test':continue
        people=visible_people(r)
        if not people:continue
        path='images/test/'+r['frame_id']+'.png'
        subsets['test_person_all'].append(path)
        subsets['test_person_single' if len(people)==1 else 'test_person_multi'].append(path)
        if any(size_band(o['bbox_px'],cfg['human_priority']['size_area_thresholds_px']) in ('very_small','small') for o in people):subsets['test_person_small'].append(path)
        if any(o['distance_category']=='far' for o in people):subsets['test_person_far'].append(path)
        if r['occlusion_requested']!='none':subsets['test_person_occluded'].append(path)
        if r['lighting']['family']=='shadow':subsets['test_person_shadow'].append(path)
    return subsets
