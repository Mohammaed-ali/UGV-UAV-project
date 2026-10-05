Actual split composition uses valid exported visible-person boxes; ignored targets remain counted separately.

| Measure | Train | Validation | Test |
| --- | --- | --- | --- |
| Images | 1600 | 200 | 200 |
| Person frames | 945 (59.062%) | 59 (29.500%) | 59 (29.500%) |
| Vehicle-only frames | 329 | 100 | 100 |
| Distractor-only frames | 160 | 20 | 20 |
| Empty negative frames | 160 | 20 | 20 |
| Intended positives with all targets ignored | 6 | 1 | 1 |
| Single-person frames | 423 | 35 | 35 |
| Multi-person frames | 522 | 24 | 24 |
| Labelled person instances | 3000 | 156 | 154 |
| All person instances, including ignored | 3088 | 157 | 159 |
| Ignored persons: tiny | 48 | 0 | 3 |
| Ignored persons: occluded | 40 | 1 | 2 |
| Human + vehicle frames | 470 | 30 | 30 |

| Class | Train labels | Validation labels | Test labels | Total labels | All targets |
| --- | --- | --- | --- | --- | --- |
| person | 3000 | 156 | 154 | 3310 | 3404 |
| car | 765 | 148 | 142 | 1055 | 1056 |
| truck | 713 | 136 | 155 | 1004 | 1004 |
| bus | 715 | 134 | 142 | 991 | 992 |

| Visible people per TRAIN frame | Frames | Fraction of multi-person frames | Person instances | Fraction of person instances |
| --- | --- | --- | --- | --- |
| 1 | 423 | single | 423 | 14.100% |
| 2–3 | 212 | 40.613% | 518 | 17.267% |
| 4–6 | 185 | 35.441% | 915 | 30.500% |
| 7–10 | 101 | 19.349% | 846 | 28.200% |
| 11+ | 24 | 4.598% | 298 | 9.933% |

Valid TRAIN person instances by altitude:

| altitude | Instances | Fraction |
| --- | --- | --- |
| 10 | 620 | 20.667% |
| 15 | 645 | 21.500% |
| 20 | 562 | 18.733% |
| 30 | 603 | 20.100% |
| 40 | 570 | 19.000% |

Valid TRAIN person instances by angle:

| angle | Instances | Fraction |
| --- | --- | --- |
| 0 | 690 | 23.000% |
| 10 | 792 | 26.400% |
| 20 | 696 | 23.200% |
| 30 | 822 | 27.400% |

Valid TRAIN person instances by distance:

| distance | Instances | Fraction |
| --- | --- | --- |
| edge | 282 | 9.400% |
| far | 905 | 30.167% |
| medium | 911 | 30.367% |
| near | 902 | 30.067% |

Valid TRAIN person instances by background:

| background | Instances | Fraction |
| --- | --- | --- |
| dirt | 761 | 25.367% |
| grass | 710 | 23.667% |
| mixed | 736 | 24.533% |
| road | 793 | 26.433% |

Valid TRAIN person instances by lighting:

| lighting | Instances | Fraction |
| --- | --- | --- |
| evening | 695 | 23.167% |
| morning | 798 | 26.600% |
| noon | 805 | 26.833% |
| shadow | 702 | 23.400% |

Valid TRAIN person instances by asset:

| asset | Instances | Fraction |
| --- | --- | --- |
| human_mesh_0 | 383 | 12.767% |
| human_mesh_1 | 354 | 11.800% |
| human_mesh_2 | 375 | 12.500% |
| human_mesh_3 | 417 | 13.900% |
| human_mesh_4 | 356 | 11.867% |
| human_mesh_5 | 390 | 13.000% |
| human_mesh_6 | 356 | 11.867% |
| human_mesh_7 | 369 | 12.300% |

Valid TRAIN person instances by occlusion_requested:

| occlusion_requested | Instances | Fraction |
| --- | --- | --- |
| mild | 486 | 16.200% |
| moderate | 181 | 6.033% |
| none | 2333 | 77.767% |

Person pixel-area categories: very small <64 px²; small 64–<1,024; medium 1,024–<9,216; large ≥9,216.

| Pixel area group | Train | Validation | Test |
| --- | --- | --- | --- |
| very_small | 739 (24.633%) | 48 (30.769%) | 44 (28.571%) |
| small | 2044 (68.133%) | 103 (66.026%) | 101 (65.584%) |
| medium | 217 (7.233%) | 5 (3.205%) | 9 (5.844%) |
| large | 0 (0.000%) | 0 (0.000%) | 0 (0.000%) |

Native valid TRAIN person box size by altitude (width/height are separately summarized, not one actual median box):

| altitude | Count | Width median / p05 / p95 (px) | Height median / p05 / p95 (px) | Area median / p05 / p95 (px²) |
| --- | --- | --- | --- | --- |
| 10 | 620 | 26.00 / 12.00 / 56.05 | 29.00 / 15.00 / 45.05 | 736.00 / 247.95 / 2024.00 |
| 15 | 645 | 17.00 / 8.00 / 39.00 | 18.00 / 10.00 / 29.80 | 306.00 / 117.60 / 834.40 |
| 20 | 562 | 12.00 / 6.00 / 28.95 | 13.00 / 8.00 / 22.00 | 154.00 / 65.00 / 449.90 |
| 30 | 603 | 8.00 / 4.00 / 20.00 | 9.00 / 5.00 / 14.90 | 77.00 / 24.00 / 223.70 |
| 40 | 570 | 6.00 / 3.00 / 13.00 | 6.00 / 3.00 / 11.00 | 40.00 / 15.00 / 110.00 |

Native valid TRAIN person box size by distance (width/height are separately summarized, not one actual median box):

| distance | Count | Width median / p05 / p95 (px) | Height median / p05 / p95 (px) | Area median / p05 / p95 (px²) |
| --- | --- | --- | --- | --- |
| edge | 282 | 14.00 / 4.00 / 33.00 | 11.00 / 4.00 / 25.00 | 152.50 / 21.00 / 671.20 |
| far | 905 | 17.00 / 5.00 / 53.00 | 16.00 / 6.00 / 42.00 | 270.00 / 44.00 / 1757.60 |
| medium | 911 | 13.00 / 4.00 / 39.00 | 14.00 / 5.00 / 35.00 | 180.00 / 28.00 / 1130.00 |
| near | 902 | 9.00 / 4.00 / 25.00 | 12.00 / 4.00 / 31.00 | 106.50 / 18.00 / 690.00 |

Native valid TRAIN person box size by angle (width/height are separately summarized, not one actual median box):

| angle | Count | Width median / p05 / p95 (px) | Height median / p05 / p95 (px) | Area median / p05 / p95 (px²) |
| --- | --- | --- | --- | --- |
| 0 | 690 | 13.00 / 4.00 / 45.55 | 12.00 / 4.00 / 40.00 | 156.00 / 20.45 / 1471.35 |
| 10 | 792 | 13.00 / 4.00 / 44.00 | 13.00 / 5.00 / 40.00 | 180.00 / 25.00 / 1439.10 |
| 20 | 696 | 12.00 / 4.00 / 39.25 | 12.00 / 5.00 / 33.00 | 140.00 / 20.00 / 1131.75 |
| 30 | 822 | 12.00 / 4.00 / 38.95 | 15.00 / 6.00 / 34.00 | 181.00 / 25.00 / 1078.50 |

| Test subset file list | Images |
| --- | --- |
| test_person_all | 59 |
| test_person_far | 33 |
| test_person_multi | 24 |
| test_person_occluded | 10 |
| test_person_shadow | 14 |
| test_person_single | 35 |
| test_person_small | 59 |

| Person yaw bin (all realized people) | Train | Validation | Test |
| --- | --- | --- | --- |
| 0–30 | 237 | 14 | 15 |
| 30–60 | 256 | 16 | 13 |
| 60–90 | 268 | 10 | 13 |
| 90–120 | 255 | 14 | 16 |
| 120–150 | 240 | 14 | 11 |
| 150–180 | 254 | 12 | 25 |
| 180–210 | 274 | 21 | 8 |
| 210–240 | 245 | 14 | 17 |
| 240–270 | 249 | 15 | 12 |
| 270–300 | 285 | 10 | 11 |
| 300–330 | 255 | 9 | 12 |
| 330–360 | 270 | 8 | 6 |

All classes ignored: {'ignored_occluded': 45, 'ignored_tiny': 51}. Placement shortfall: 59. Truncated target instances: 1147.
