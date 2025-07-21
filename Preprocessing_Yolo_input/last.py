"""
roi_count_video_polygons.py
Count *cars only* inside polygon‑ROIs read from polygons.csv.

polygons.csv columns:
    frame,id,x1,y1,x2,y2,x3,y3,x4,y4
          ¹   ²   ³   ⁴   ⁵   ⁶   ⁷   ⁸   ⁹   ¹⁰
frame – 1‑based frame index in the video
id    – ROI name (e.g. ID‑1, Right, …)
(x1,y1)…(x4,y4) – 4 vertices, in any consistent order
"""

from ultralytics import YOLO
import cv2, csv, json
from pathlib import Path
import numpy as np

# ------------------------------------------------------------------
# 1) paths
# ------------------------------------------------------------------
# VIDEO_IN   = "output_video.mp4"
# VIDEO_IN = "15_minutes.mp4"
VIDEO_IN = "video_without_polygons.mp4"
MODEL_PT = "best.pt"
POLY_CSV = "polygons.csv"  # a sheet in which has the polygon for each intersection
OUT_DIR = Path("outputs_video")  # the output directory in which output will be saved
OUT_DIR.mkdir(parents=True, exist_ok=True)
LIGHT_DIR = OUT_DIR / "original_lights"
LIGHT_DIR.mkdir(exist_ok=True)

VIDEO_OUT = OUT_DIR / "annotated.mp4"  # annotated output video
COUNTS_DIR = OUT_DIR / "counts"  # output text files that's going to hold the cars count dictionaries
COUNTS_DIR.mkdir(exist_ok=True)

"""
------------------------------------------------------------------
2) load polygon ROIs  →  {frame_idx: [(id, np.ndarray[4,2]), …], …}

- Creates empty dictionary:
- The keys of the dictionary are int, representing frame numbers.
- The values are a list of tuple[str, np.ndarray], where:
- str is the polygon ID (like 'ID‑1', 'Right', etc.)
- {
  1: [
    ('ID-1', array([[ 956,  571],
                    [ 969,  610],
                    [1502,  402],
                    [1477,  359]], dtype=int32)),
    ('ID-2', array([[ 921,  587],
                    [ 892,  600],
                    [ 789,  335],
                    [ 814,  312]], dtype=int32)),
    ('ID-3', array([[ 894,  644],
                    [ 914,  688],
                    [ 409,  976],
                    [ 378,  931]], dtype=int32)),
    ('ID-4', array([[ 949,  667],
                    [ 978,  655],
                    [1010,  902],
                    [ 971,  905]], dtype=int32))
  ],
  2: [
    ('ID-1', array([[ 956,  571],
                    [ 968,  610],
                    [1501,  402],
                    [1477,  359]], dtype=int32)),
    ('ID-2', array([[ 921,  587],
                    [ 892,  601],
                    [ 789,  335],
                    [ 815,  312]], dtype=int32)),
    ('ID-3', array([[ 894,  644],
                    [ 913,  688],
                    [ 409,  976],
                    [ 377,  932]], dtype=int32)),
    ('ID-4', array([[ 949,  667],
                    [ 978,  655],
                    [1008,  902],
                    [ 970,  905]], dtype=int32))
  ]
}
------------------------------------------------------------------
"""
#                   1               ID-1  ([],[],[],[])
poly_by_frame: dict[int, list[tuple[str, np.ndarray]]] = {}

# store the values of the csv file, into the dictionary "poly_by_frame"
with open(POLY_CSV, newline="") as f:
    rdr = csv.DictReader(f)
    for row in rdr:
        fidx = int(row["frame"])  # 1‑based in sheet
        ident = row["id"]
        pts = np.array(
            [
                [int(row["x1"]), int(row["y1"])],
                [int(row["x2"]), int(row["y2"])],
                [int(row["x3"]), int(row["y3"])],
                [int(row["x4"]), int(row["y4"])],
            ],
            dtype=np.int32,
        )
        poly_by_frame.setdefault(fidx, []).append((ident, pts))

# pick some colours
COLOURS = [(0, 255, 0), (0, 128, 255), (255, 0, 0), (128, 0, 255), (0, 255, 255), (255, 0, 255), (255, 255, 0)]

# traffic lights coordinates and colours
traffic_light_polygons = [
    ("ID-1", 15, 83, 40, 130),
    ("ID-2", 105, 83, 40, 130),
    ("ID-3", 180, 83, 40, 130),
    ("ID-4", 270, 83, 40, 130),
]

# TRAFFIC_LIGHT_STATE_COLOUR  = [(255,255,255), (255,255,255), (255,255,255), (255,255,255)]

# colour per detected state  (BGR)
TRAFFIC_LIGHT_STATE_COLOUR = {
    "red": (0, 0, 255),
    "yellow": (0, 255, 255),
    "green": (0, 255, 0),
    "unknown": (128, 128, 128)
}

# priority if two colours are detected on the same pole in one frame
PRIORITY = {"red": 3, "yellow": 2, "green": 1}

# ------------------------------------------------------------------
# 3) YOLO
# ------------------------------------------------------------------
model = YOLO(MODEL_PT)

# ------------------------------------------------------------------
# 4) video I/O
# ------------------------------------------------------------------
cap = cv2.VideoCapture(VIDEO_IN)  # Opens the video file so that we can read frames from it.
assert cap.isOpened(), f"Cannot open {VIDEO_IN}"  # Checks that the video was successfully opened. if not, close program

w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # get width and hight of video
fps = cap.get(cv2.CAP_PROP_FPS) or 30
writer = cv2.VideoWriter(str(VIDEO_OUT), cv2.VideoWriter_fourcc(*"mp4v"), fps,
                         (w, h))  # To write frames -> output video

# ------------------------------------------------------------------
# 5) main loop
# ------------------------------------------------------------------
# SKIP_EVERY = 5
frame_idx = 1  # 1‑based to match CSV

while True:
    ok, frame = cap.read()
    if not ok: break  # leave loop when there is no frames left

    # inside while-loop, right after you read the frame
    tl_state = {name: "unknown" for name, *_ in traffic_light_polygons}
    tl_score = {name: 0.0 for name in tl_state}

    # ── get polygons for this frame; fall back to last known if missing ──
    if frame_idx in poly_by_frame:
        polys = poly_by_frame[frame_idx]
        last_polys = polys  # keep a copy in case next frame missing
    else:
        polys = last_polys  # use previous set

    # build a dict {id:0}
    counts = {pid: 0 for pid, _ in polys}  # looks like: {'ID-1': 0, 'ID-2': 0, 'ID-3': 0, 'ID-4': 0}

    # ── detect cars/traffic lights ──
    res = model(frame, conf=0.20, verbose=False)
    boxes = res[0].boxes

    # ── tally cars per polygon ──
    for box in boxes:
        cls_id = int(box.cls[0])  # car class

        if cls_id != 0:  # skip non-car class detections
            continue

        x1, y1, x2, y2 = box.xyxy[0]
        cx, cy = float((x1 + x2) / 2), float((y1 + y2) / 2)

        for pid, poly in polys:
            # cv2.pointPolygonTest returns +1, 0, -1 (inside, on edge, outside)
            if cv2.pointPolygonTest(poly, (cx, cy), measureDist=False) >= 0:
                counts[pid] += 1
                break

    # ── draw polygons & counts ──
    for i, (pid, poly) in enumerate(polys):
        # print(i) # 0,1,...
        # print(pid) # ID-1, ID-2,...
        # print(poly) # [[ 956  571], [ 969  610], [1502  402], [1477  359]]

        colour = COLOURS[i % len(COLOURS)]  # to get the same colour as the polygon
        cv2.polylines(frame, [poly], isClosed=True, color=colour, thickness=2)

        # put text near first vertex
        # tx,ty = poly[0]
        # cv2.putText(frame, f"{pid}: {counts[pid]}", (tx+5, ty-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, colour, 2)

        text_x = w - 300  # 200 pixels from right edge
        text_y = 40 + i * 40  # stack each line 30px apart
        cv2.putText(
            frame,  # frame to draw on
            f"{pid}: {counts[pid]}",  # text to draw
            (text_x, text_y),  # position
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,  # font scale
            colour,  # text color
            3  # thickness
        )

    # draw YOLO boxes without labels/conf
    frame = res[0].plot(img=frame, labels=False, line_width=2)

    # drawing boxes around traffic lights (optional)
    # for i, (tl_id, x, y, w, h) in enumerate(traffic_light_boxes):
    #     p1 = (x, y)               # top-left
    #     p2 = (x + w, y + h)       # bottom-right

    #     colour = TRAFFIC_COLOURS[i % len(TRAFFIC_COLOURS)]
    #     cv2.rectangle(frame, p1, p2, colour, 2)

    #     # write the ID next to the box
    #     cv2.putText(frame, tl_id, (x + 4, y - 6),
    #                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1)

    for det in boxes:
        cls_id = int(det.cls[0])  # 1=green, 2=red, 3=yellow
        if cls_id not in (1, 2, 3):
            continue  # skip cars etc.

        # map numeric class → colour string
        colour_str = {1: "green", 2: "red", 3: "yellow"}[cls_id]

        # centre of YOLO box
        x1, y1, x2, y2 = det.xyxy[0]
        cx, cy = float((x1 + x2) / 2), float((y1 + y2) / 2)

        conf = float(det.conf[0])  # confidence

        # find which pole the centre falls into
        for name, px, py, pw, ph in traffic_light_polygons:
            if px <= cx <= px + pw and py <= cy <= py + ph:
                # accept new state if (a) state was unknown, (b) new colour has
                # higher PRIORITY than existing, or (c) same colour but higher conf
                old_col = tl_state[name]
                if (old_col == "unknown" or
                        PRIORITY[colour_str] > PRIORITY.get(old_col, 0) or
                        (colour_str == old_col and conf > tl_score[name])):
                    tl_state[name] = colour_str
                    tl_score[name] = conf
                break  # stop checking other poles

    # ------------------------------------------------------------------
    # draw the traffic-light rectangles with colour coded by state
    # ------------------------------------------------------------------
    for name, px, py, pw, ph in traffic_light_polygons:
        state = tl_state[name]
        colour = TRAFFIC_LIGHT_STATE_COLOUR[state]
        cv2.rectangle(frame, (px, py), (px + pw, py + ph), colour, 2)
        cv2.putText(frame, f"{name}:{state}", (px + 2, py - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1)

        # ── save frame & counts ──
    writer.write(frame)
    (COUNTS_DIR / f"frame_{frame_idx:06d}.txt").write_text(json.dumps(counts))

    # # skip frames quickly (≈6× faster)
    # for _ in range(SKIP_EVERY):
    #     if not cap.grab(): break
    #     frame_idx += 1

    # Combine car counts and light states in one record
    record = {
        "cars": counts,  # {'ID-1': 12, …}
        "lights": tl_state  # {'ID-1': 'green', …}
    }
    (LIGHT_DIR / f"frame_{frame_idx:06d}.json").write_text(json.dumps(record))

    frame_idx += 1

    if frame_idx % 100 == 1:
        print(f"[INFO] processed {frame_idx - 1} frames…")

# ------------------------------------------------------------------
cap.release();
writer.release()
print(f"[DONE] annotated video  →  {VIDEO_OUT}")
print(f"[DONE] per‑frame counts →  {COUNTS_DIR}")