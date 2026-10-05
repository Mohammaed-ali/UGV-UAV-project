Actual split composition uses valid exported visible-person boxes; ignored targets remain counted separately.

| Measure | Train | Validation | Test |
| --- | --- | --- | --- |
| Images | 8000 | 1000 | 1000 |
| Person frames | 4722 (59.025%) | 295 (29.500%) | 293 (29.300%) |
| Vehicle-only frames | 1643 | 502 | 503 |
| Distractor-only frames | 800 | 100 | 100 |
| Empty negative frames | 800 | 100 | 100 |
| Intended positives with all targets ignored | 35 | 3 | 4 |
| Single-person frames | 2123 | 175 | 174 |
| Multi-person frames | 2599 | 120 | 119 |
| Labelled person instances | 15093 | 761 | 777 |
| All person instances, including ignored | 15520 | 779 | 797 |
| Ignored persons: tiny | 256 | 9 | 11 |
| Ignored persons: occluded | 171 | 9 | 9 |
| Human + vehicle frames | 2355 | 147 | 147 |

| Class | Train labels | Validation labels | Test labels | Total labels | All targets |
| --- | --- | --- | --- | --- | --- |
| person | 15093 | 761 | 777 | 16631 | 17096 |
| car | 3676 | 780 | 752 | 5208 | 5225 |
| truck | 3547 | 689 | 703 | 4939 | 4942 |
| bus | 3482 | 731 | 685 | 4898 | 4899 |

| Visible people per TRAIN frame | Frames | Fraction of multi-person frames | Person instances | Fraction of person instances |
| --- | --- | --- | --- | --- |
| 1 | 2123 | single | 2123 | 14.066% |
| 2–3 | 1039 | 39.977% | 2594 | 17.187% |
| 4–6 | 927 | 35.668% | 4563 | 30.233% |
| 7–10 | 507 | 19.508% | 4262 | 28.238% |
| 11+ | 126 | 4.848% | 1551 | 10.276% |

Valid TRAIN person instances by altitude:

| altitude | Instances | Fraction |
| --- | --- | --- |
| 10 | 3037 | 20.122% |
| 15 | 3098 | 20.526% |
| 20 | 3110 | 20.606% |
| 30 | 2955 | 19.579% |
| 40 | 2893 | 19.168% |

Valid TRAIN person instances by angle:

| angle | Instances | Fraction |
| --- | --- | --- |
| 0 | 3681 | 24.389% |
| 10 | 3836 | 25.416% |
| 20 | 3802 | 25.190% |
| 30 | 3774 | 25.005% |

Valid TRAIN person instances by distance:

| distance | Instances | Fraction |
| --- | --- | --- |
| edge | 1431 | 9.481% |
| far | 4556 | 30.186% |
| medium | 4566 | 30.252% |
| near | 4540 | 30.080% |

Valid TRAIN person instances by background:

| background | Instances | Fraction |
| --- | --- | --- |
| dirt | 3778 | 25.031% |
| grass | 3739 | 24.773% |
| mixed | 3714 | 24.607% |
| road | 3862 | 25.588% |

Valid TRAIN person instances by lighting:

| lighting | Instances | Fraction |
| --- | --- | --- |
| evening | 3746 | 24.819% |
| morning | 3808 | 25.230% |
| noon | 3932 | 26.052% |
| shadow | 3607 | 23.898% |

Valid TRAIN person instances by asset:

| asset | Instances | Fraction |
| --- | --- | --- |
| human_mesh_0 | 1853 | 12.277% |
| human_mesh_1 | 1905 | 12.622% |
| human_mesh_2 | 1903 | 12.608% |
| human_mesh_3 | 1946 | 12.893% |
| human_mesh_4 | 1788 | 11.847% |
| human_mesh_5 | 1873 | 12.410% |
| human_mesh_6 | 1915 | 12.688% |
| human_mesh_7 | 1910 | 12.655% |

Valid TRAIN person instances by occlusion_requested:

| occlusion_requested | Instances | Fraction |
| --- | --- | --- |
| mild | 2368 | 15.689% |
| moderate | 752 | 4.982% |
| none | 11973 | 79.328% |

Person pixel-area categories: very small <64 px²; small 64–<1,024; medium 1,024–<9,216; large ≥9,216.

| Pixel area group | Train | Validation | Test |
| --- | --- | --- | --- |
| very_small | 3757 (24.892%) | 182 (23.916%) | 222 (28.571%) |
| small | 10305 (68.277%) | 519 (68.200%) | 488 (62.806%) |
| medium | 1031 (6.831%) | 60 (7.884%) | 67 (8.623%) |
| large | 0 (0.000%) | 0 (0.000%) | 0 (0.000%) |

Native valid TRAIN person box size by altitude (width/height are separately summarized, not one actual median box):

| altitude | Count | Width median / p05 / p95 (px) | Height median / p05 / p95 (px) | Area median / p05 / p95 (px²) |
| --- | --- | --- | --- | --- |
| 10 | 3037 | 26.00 / 12.00 / 61.00 | 28.00 / 15.00 / 47.00 | 736.00 / 238.00 / 2108.20 |
| 15 | 3098 | 16.00 / 8.00 / 38.00 | 19.00 / 10.00 / 30.00 | 304.00 / 110.00 / 828.00 |
| 20 | 3110 | 12.00 / 6.00 / 28.00 | 14.00 / 8.00 / 22.00 | 168.00 / 66.00 / 448.00 |
| 30 | 2955 | 8.00 / 4.00 / 18.00 | 9.00 / 5.00 / 15.00 | 70.00 / 28.00 / 192.00 |
| 40 | 2893 | 6.00 / 3.00 / 14.00 | 6.00 / 4.00 / 11.00 | 40.00 / 15.00 / 105.00 |

Native valid TRAIN person box size by distance (width/height are separately summarized, not one actual median box):

| distance | Count | Width median / p05 / p95 (px) | Height median / p05 / p95 (px) | Area median / p05 / p95 (px²) |
| --- | --- | --- | --- | --- |
| edge | 1431 | 13.00 / 4.00 / 33.00 | 12.00 / 5.00 / 26.00 | 140.00 / 24.00 / 745.00 |
| far | 4556 | 17.00 / 5.00 / 57.00 | 15.00 / 6.00 / 43.00 | 270.00 / 40.00 / 1786.75 |
| medium | 4566 | 13.00 / 4.00 / 39.00 | 13.00 / 5.00 / 36.00 | 170.00 / 28.00 / 1110.00 |
| near | 4540 | 9.00 / 4.00 / 24.00 | 12.00 / 4.00 / 31.00 | 112.00 / 18.00 / 640.20 |

Native valid TRAIN person box size by angle (width/height are separately summarized, not one actual median box):

| angle | Count | Width median / p05 / p95 (px) | Height median / p05 / p95 (px) | Area median / p05 / p95 (px²) |
| --- | --- | --- | --- | --- |
| 0 | 3681 | 13.00 / 4.00 / 45.00 | 13.00 / 5.00 / 39.00 | 189.00 / 24.00 / 1323.00 |
| 10 | 3836 | 13.00 / 4.00 / 46.00 | 13.00 / 5.00 / 39.00 | 165.00 / 24.00 / 1397.25 |
| 20 | 3802 | 12.00 / 4.00 / 40.00 | 13.00 / 5.00 / 35.00 | 160.00 / 24.00 / 1100.00 |
| 30 | 3774 | 11.00 / 4.00 / 37.00 | 13.00 / 5.00 / 32.00 | 135.00 / 24.00 / 1023.35 |

| Test subset file list | Images |
| --- | --- |
| test_person_all | 293 |
| test_person_far | 136 |
| test_person_multi | 119 |
| test_person_occluded | 55 |
| test_person_shadow | 73 |
| test_person_single | 174 |
| test_person_small | 278 |

| Person yaw bin (all realized people) | Train | Validation | Test |
| --- | --- | --- | --- |
| 0–30 | 1326 | 63 | 77 |
| 30–60 | 1281 | 73 | 62 |
| 60–90 | 1340 | 54 | 57 |
| 90–120 | 1299 | 82 | 69 |
| 120–150 | 1258 | 63 | 56 |
| 150–180 | 1336 | 68 | 76 |
| 180–210 | 1307 | 59 | 69 |
| 210–240 | 1326 | 50 | 74 |
| 240–270 | 1255 | 64 | 63 |
| 270–300 | 1277 | 59 | 51 |
| 300–330 | 1269 | 76 | 72 |
| 330–360 | 1246 | 68 | 71 |

All classes ignored: {'ignored_occluded': 207, 'ignored_tiny': 279}. Placement shortfall: 354. Truncated target instances: 5681.
