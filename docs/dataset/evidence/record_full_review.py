"""Record the completed agent visual review; findings are manual, not image scores."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / 'datasets/gazebo_aerial_v1'
QA = DATASET / 'qa'

# These notes were recorded after viewing all five native-frame/crop review pages.
# Keep the original feature records and unique-instance replay evidence intact.
notes = [
    (7350, 'incidental_tree_occlusion', 'Tree crown covers nearly all the full person silhouette. The remaining 2x4 px native sliver is ignored_tiny and is not exported to YOLO.'),
    (375, 'edge_clipping_and_rasterization', 'At the top/right boundary only a 1x1 px fragment remains. Full projected extrema extend off screen; this target is ignored_tiny.'),
    (4869, 'edge_clipping_and_canopy_occlusion', 'Right-edge clipping and canopy/support overlap leave a 2x2 px fragment, correctly ignored_tiny.'),
    (9836, 'incidental_wall_occlusion', 'The white masonry shadow wall covers most of the person despite requested occlusion none. The 3x2 px fragment is ignored_tiny.'),
    (8009, 'edge_clipping', 'Bottom-edge clipping leaves a 2x5 px fragment, below the minimum width and correctly ignored_tiny.'),
    (6498, 'canopy_occlusion', 'The canopy masks most of the full silhouette; the exposed right portion gives the 8x5 px valid native box.'),
    (3774, 'edge_clipping', 'The person crosses the bottom boundary, leaving a 2x4 px ignored_tiny fragment.'),
    (9443, 'canopy_occlusion_and_rasterization', 'The canopy masks the body, leaving a 3x4 px valid native fragment whose small extrema amplify pixel rounding.'),
    (1444, 'canopy_occlusion', 'A canopy leaves only a 3x2 px strip of the person. Height is below threshold and the target is ignored_tiny.'),
    (5351, 'canopy_occlusion', 'Roof occlusion hides most of the body; the exposed lower part produces the 7x6 px native box.'),
    (1142, 'canopy_occlusion', 'The canopy covers part of the projected body, leaving an exposed portion with a 17x11 px native rectangle.'),
    (4127, 'canopy_occlusion', 'The canopy hides the left/upper part of the person; the body on its right remains visible.'),
    (8161, 'canopy_occlusion_and_rasterization', 'Partial canopy overlap and a 4x3 px visible footprint explain the low visible/full IoU.'),
    (9623, 'edge_clipping', 'Top-edge clipping leaves a 15x5 px fragment. The visible cut mesh has narrower extrema than the clipped full rectangle.'),
    (5093, 'edge_clipping', 'The bus crosses the top/right boundaries. Its clipped rotated mesh silhouette occupies less height than the clipped full bounding rectangle; nearby tree context can also hide part.'),
    (8600, 'canopy_occlusion', 'The canopy removes the upper part of the person, leaving a 5x14 px visible box.'),
    (1818, 'canopy_occlusion', 'A canopy partly masks the distant body. The native 7x7 px rectangle bounds the remaining visible part.'),
    (5842, 'canopy_occlusion', 'The canopy cuts across the diagonal person silhouette, leaving a 12x10 px visible part.'),
    (2961, 'canopy_occlusion', 'Canopy occlusion leaves a horizontal 16x6 px body strip.'),
    (6198, 'edge_clipping', 'The bus crosses the bottom/right boundaries. The remaining slanted mesh silhouette has shorter extrema than the clipped full rectangle.'),
    (5073, 'canopy_occlusion', 'The canopy hides the right part of the person; the exposed body has a 12x10 px native box.'),
    (8359, 'canopy_occlusion_and_rasterization', 'Only a 7x3 px person strip is exposed along the canopy; pixel extrema further affect visible/full IoU.'),
    (3249, 'canopy_occlusion', 'The canopy masks the front/upper portion of the truck. The native 33x43 px rectangle follows the visible cargo/body.'),
    (6556, 'small_pixel_rasterization', 'An unoccluded person on terrain occupies only 4x3 px. Subpixel projection and integer raster extrema dominate this comparison.'),
    (9290, 'small_pixel_rasterization', 'The small nadir person has a 3x4 px native footprint. Integer pixel rounding explains the difference from continuous projected extrema.'),
    (9298, 'canopy_occlusion', 'A canopy partially masks the person, leaving a 6x6 px visible body.'),
    (9453, 'edge_clipping', 'The person crosses the left image boundary. The visible cut body is shorter than the clipped full projected rectangle.'),
    (782, 'canopy_occlusion', 'Canopy overlap covers the upper/left body; the exposed part gives a 6x27 px native rectangle.'),
    (8172, 'small_pixel_rasterization', 'An unoccluded person on terrain occupies 3x4 px; integer raster extrema explain the low IoU.'),
    (7010, 'canopy_occlusion', 'The canopy hides the head/shoulders, leaving the lower body with an 11x23 px native box.'),
    (548, 'edge_clipping_and_incidental_wall_occlusion', 'The car crosses the left boundary and the masonry shadow wall masks its lower region. Requested none permits incidental context occlusion.'),
    (4807, 'small_pixel_rasterization', 'The unoccluded terrain person has a 2x5 px footprint, below minimum width. It remains ignored_tiny rather than an exported label.'),
    (2003, 'edge_clipping', 'Right-edge clipping changes the extrema of the visible person silhouette, leaving a 7x4 px box.'),
    (527, 'edge_clipping', 'The person crosses the right boundary. Boundary cropping dominates the difference, with a moderate occlusion request also present.'),
    (3114, 'canopy_occlusion', 'A canopy masks the upper/left person; the exposed body lies along the roof edge.'),
    (9208, 'edge_clipping_and_canopy_occlusion', 'The bottom-edge person is partly hidden by a canopy and clipped at the image boundary.'),
    (2861, 'edge_clipping_and_rasterization', 'Top-edge cropping of the person leaves a 4x5 px fragment; cut-mesh extrema and raster rounding explain the difference.'),
    (3965, 'edge_clipping_and_canopy_occlusion', 'The gray canopy partly masks the person, with left-edge clipping also reducing its visible rectangle.'),
    (8730, 'edge_clipping_and_canopy_occlusion', 'The top-edge person is reduced to an 8x8 px fragment; a moderate canopy request and boundary crop both apply.'),
    (4458, 'edge_clipping', 'Top-edge clipping leaves a 7x7 px body fragment, differing from the clipped full projection rectangle.'),
    (9247, 'canopy_occlusion', 'The canopy partly masks the person, leaving a 10x7 px visible box.'),
    (2884, 'small_pixel_rasterization', 'An unoccluded terrain person occupies 2x6 px and is correctly ignored_tiny. Minimum width and integer rasterization explain the tail.'),
    (9123, 'edge_clipping', 'The truck crosses the top boundary. A visible rear fragment has an 8 px height despite the larger clipped rotated-mesh rectangle.'),
    (8565, 'canopy_occlusion', 'A canopy hides the upper person extrema, leaving a 5x7 px native rectangle.'),
    (3480, 'canopy_occlusion', 'The moderate canopy masks the head/upper body. The exposed lower body produces the 24x22 px native box.'),
    (8373, 'canopy_occlusion', 'The canopy masks the upper body, leaving an 11x16 px visible part.'),
    (1281, 'small_pixel_rasterization', 'The unoccluded person has a thin 3x8 px footprint. Pixel rounding dominates; nearby tree context does not show clear overlap.'),
    (7176, 'edge_clipping_and_incidental_wall_occlusion', 'The bus crosses the top/left boundaries and the masonry shadow wall hides its lower part. Requested occlusion none does not preclude this context overlap.'),
    (799, 'small_pixel_rasterization', 'The unoccluded far person occupies 3x7 px; roughly one-pixel differences in extrema strongly affect IoU.'),
    (8816, 'small_pixel_rasterization', 'The unoccluded medium-distance person projects to a small horizontal 6x3 px footprint; continuous/raster extrema explain the difference.'),
]
features = json.loads((QA / 'low_iou_features.json').read_text())
identity = json.loads((QA / 'instance_identity_audit.json').read_text())
assert identity['status'] == 'PASSED' and not identity['failed_frames']
assert len(features) == len(notes) == len(identity['frames']) == 50
by_id = {r['frame_id']: r for r in identity['frames']}
for feature, (index, cause, finding) in zip(features, notes):
    assert feature['index'] == index
    check = by_id[feature['frame_id']]
    assert check['status'] == 'PASSED' and check['yolo_bytes_identical']
    feature.update(cause=cause, visual_finding=finding,
                   instance_identity_check=check['status'],
                   yolo_bytes_identical=True, status='PASSED')
now = datetime.now(timezone.utc).isoformat()
tail = {
    'status': 'PASSED', 'review_timestamp': now,
    'reviewer': 'Codex agent visual inspection',
    'frames': features, 'cause_counts': dict(Counter(f['cause'] for f in features)),
    'review_pages': [f'low_iou/review_pages/{i:03d}.png' for i in range(1, 6)],
    'instance_identity_evidence': 'qa/instance_identity_audit.json',
    'decision': 'No unexplained registration or instance-association defect found in the reviewed tail. Retain native visible rectangles and ignored reasons; do not enlarge labels or remove difficult samples to improve IoU.',
    'limitations': 'These 50 investigated frames are an audit sample, not exhaustive visibility or identity certification of every full-dataset target. IoU includes ignored_tiny boxes and compares visible raster rectangles with full projected mesh rectangles, not pixel visibility fractions.',
}
review = {
    'status': 'PASSED', 'review_timestamp': now,
    'reviewer': 'Codex agent visual inspection', 'reviewed_previews': 100,
    'review_pages': [f'review_pages/{i:03d}.jpg' for i in range(1, 5)],
    'dedicated_contact_sheets': ['best_quality', 'human_focused', 'single_person',
        'multi_person', 'person_vehicle', 'shadow', 'occluded', 'lowest_fidelity'],
    'native_images_reviewed': ['scene_a61990328d99d760_009428',
                              'scene_1f3574e059db1711_007034'],
    'background_extent_diagnostic': 'qa/background_extent_review.json',
    'criteria': {
        'human_recognizability': {'status': 'PASSED', 'finding': 'Native larger-human examples show clothed heads, torsos and limbs, including 14-person mixed scenes. Full sheets cover single/multi people at all factors. Far/nadir people are pixel-limited, and all eight appearances share one template.'},
        'vehicle_recognizability': {'status': 'PASSED', 'finding': 'Shaped cabins, wheels, cargo bodies and coach window/roof structure distinguish cars, trucks and buses. The retained assets remain stylized.'},
        'terrain_realism': {'status': 'PASSED', 'finding': 'Photographic PBR grass, soil, asphalt and irregular mixed patches improve terrain fidelity. The terrain is planar and repeats mosaics; road layouts are simplified.'},
        'lighting_realism': {'status': 'PASSED', 'finding': 'Directional sun, subdued warm morning/evening and neutral noon produce coherent ground/object shading. No atmospheric or physically calibrated sky model is claimed.'},
        'shadow_realism': {'status': 'PASSED', 'finding': 'Trees, vehicles, canopies and masonry walls cast localized shadows with both lit and shaded people. Shadows remain hard and some walls are deliberate occluders.'},
        'scene_plausibility': {'status': 'PASSED', 'finding': 'Targets are grounded and separated across single, crowd and mixed vehicle scenes. Layouts are simplified and do not model traffic/crowd behavior. Finite terrain and fixed far clipping expose background corners in 643/10000 frames, at most 7.045% of pixels.'},
    },
    'judgment': 'Acceptable improved simplified synthetic imagery under the revised smoke/pilot criteria. This is not photorealistic or equivalent to real aerial photography, and it supplies no real-world detector accuracy or sim-to-real evidence.',
    'limitations_document': 'docs/dataset/ASSETS_V2.md',
}
for name, report in [('low_iou_investigations.json', tail), ('realism_review.json', review)]:
    (QA / name).write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': 'PASSED', 'low_iou_frames_reviewed': len(features),
                  'preview_frames_reviewed': 100, 'cause_counts': tail['cause_counts']}, indent=2))
