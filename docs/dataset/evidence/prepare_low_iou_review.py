"""Prepare inspectable full-frame/nearest-pixel-crop pages, without accepting a gate."""
import argparse
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/synthetic_dataset/scripts'))
from geometry import clip_box
from storage import committed_records
from common import write_json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('dataset'); args = p.parse_args()
root = Path(args.dataset)
records = {r['frame_id']: r for r in committed_records(root)}
ids = json.loads((root/'qa/preview_index.json').read_text())['lowest_iou_frames']
features = []
tiles = []
for n, fid in enumerate(ids, 1):
    r = records[fid]
    o = min((o for o in r['objects'] if o['bbox_px']), key=lambda o: o['annotation_iou'])
    b = o['bbox_px']; s = clip_box(o['secondary_bbox_px'], r['camera']['model'])
    raw = Image.open(root/'images'/r['split']/(fid+'.png')).convert('RGB')
    annotated = Image.open(root/'qa/low_iou'/(fid+'.png')).convert('RGB')
    canvas = Image.new('RGB', (520, 270), (22,22,22)); draw = ImageDraw.Draw(canvas)
    draw.text((3,2), f"{n:02d} #{r['index']} {o['class_name']} IoU {o['annotation_iou']:.4f} {o['label_state']}", fill='white')
    canvas.paste(annotated.resize((320,240)), (0,26))
    window = min(240, max(48, int(max(s[2]-s[0], s[3]-s[1])*1.3)))
    cx, cy = (s[0]+s[2])/2, (s[1]+s[3])/2
    left = max(0,min(640-window,int(cx-window/2))); top = max(0,min(480-window,int(cy-window/2)))
    crop = raw.crop((left,top,left+window,top+window))
    cd = ImageDraw.Draw(crop)
    for box, color in [(s,(0,160,255)),(b,(0,255,0))]:
        cd.rectangle((box[0]-left,box[1]-top,box[2]-left,box[3]-top),outline=color,width=1)
    canvas.paste(crop.resize((192,192),Image.Resampling.NEAREST),(324,26))
    draw.text((324,220), f"native {b[2]-b[0]:g}x{b[3]-b[1]:g}px",fill='white')
    draw.text((324,234), f"{o['distance_category']}, requested {r['occlusion_requested']}",fill='white')
    draw.text((324,248), 'green native / blue full',fill='white')
    tiles.append(canvas)
    features.append({'rank':n,'frame_id':fid,'index':r['index'],'split':r['split'],
        'worst_instance_id':o['instance_id'],'class':o['class_name'],'iou':o['annotation_iou'],
        'native_bbox_px':b,'full_projected_bbox_px':o['secondary_bbox_px'],
        'label_state':o['label_state'],'distance':o['distance_category'],'truncated':o['truncated'],
        'requested_occlusion':r['occlusion_requested'],'altitude':r['camera']['nominal_altitude_m'],
        'angle':r['camera']['nominal_off_nadir_deg'],
        'ignored_objects':[{'instance_id':v['instance_id'],'reason':v['ignored_reason']} for v in r['objects'] if v['label_state']!='labelled'],
        'context_ids':[v['instance_id'] for v in r['distractors']]})
out = root/'qa/low_iou/review_pages'; out.mkdir(parents=True,exist_ok=True)
for i in range(0,len(tiles),10):
    page=Image.new('RGB',(1040,1350),(0,0,0))
    for j,tile in enumerate(tiles[i:i+10]):page.paste(tile,((j%2)*520,(j//2)*270))
    page.save(out/f'{i//10+1:03d}.png')
write_json(root/'qa/low_iou_features.json',features)
print(f'Prepared {len(tiles)} review tiles; no acceptance decision written.')
