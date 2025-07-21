import cv2
import math
import numpy as np
import pprint

# === VIDEO & SCHEDULE PARAMETERS ===
fps = 30
total_frames = 895 * fps    # 45 525 frames in a 895-second video
gap   = 150                # 150-frame gap between green phases

# === DURATIONS BEFORE FRAME 10000 ===
dur1 = {
    "ID-2":   360,
    "ID-4":   360,
    "ID-1-L": 450,
    "ID-1-F":1230,
    "ID-3-F":1230,
    "ID-3-L": 450
}

# === DURATIONS AFTER FRAME 10000 (initially same as dur1) ===
dur2 = {
    "ID-2":   390,
    "ID-4":   420,
    "ID-1-L": 450,
    "ID-1-F":1230,
    "ID-3-F":1230,
    "ID-3-L": 450
}


# === BUILD HYBRID SCHEDULE ===
schedule = {k: [] for k in dur1}
cycle_start = 0

while cycle_start < total_frames:
    # choose which duration-set applies
    d = dur1 if cycle_start < 11250 else dur2

    # 1) ID-2
    s2 = cycle_start
    e2 = s2 + d["ID-2"]
    if s2 < total_frames:
        schedule["ID-2"].append((s2, min(e2, total_frames)))

    # 2) ID-4
    s4 = e2 + gap
    e4 = s4 + d["ID-4"]
    if s4 < total_frames:
        schedule["ID-4"].append((s4, min(e4, total_frames)))

    # 3) ID-1-L and ID-1-F (start at same time)
    s1l = e4 + gap
    e1l = s1l + d["ID-1-L"]
    s1f = s1l
    e1f = s1f + d["ID-1-F"]
    if s1l < total_frames:
        schedule["ID-1-L"].append((s1l, min(e1l, total_frames)))
    if s1f < total_frames:
        schedule["ID-1-F"].append((s1f, min(e1f, total_frames)))

    # 4) ID-3-F (after ID-1-L)
    s3f = e1l + gap
    e3f = s3f + d["ID-3-F"]
    if s3f < total_frames:
        schedule["ID-3-F"].append((s3f, min(e3f, total_frames)))

    # 5) ID-3-L (after ID-1-F)
    s3l = e1f + gap
    e3l = s3l + d["ID-3-L"]
    if s3l < total_frames:
        schedule["ID-3-L"].append((s3l, min(e3l, total_frames)))

    # advance to end of this cycle
    cycle_end = max(e3f, e3l)
    cycle_start = cycle_end + gap

# === PRINT THE HYBRID SCHEDULE ===
print("Hybrid traffic_light_schedule:")
pprint.pprint(schedule)