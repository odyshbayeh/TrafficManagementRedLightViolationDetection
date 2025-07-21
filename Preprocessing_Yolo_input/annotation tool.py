import cv2
import csv
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------
# Annotation tool for drone-view violation lines and ROI homographies
# ---------------------------------------------------------------------
# Usage: run this script in PyCharm or CLI. It will:
# 1) Capture a reference frame (press 'c').
# 2) Annotate 4-point world intersections (keys 1-4): click 4 pts for each, press 'n' to confirm.
# 3) Annotate crossing lines per intersection (press 'v' then 1-4): click 2 pts, press 'n' to confirm.
# 4) Press 's' to save world_intersections.csv and crossing_lines.csv, then exit.
# 5) Press 'q' to quit without saving.

VIDEO_PATH = r"C:\Users\odysh\OneDrive\Desktop\Preprocessing_Yolo_input\videos\15-min-testing.mp4"
# Save CSVs to current working directory
OUTPUT_DIR = Path.cwd()

# Data structures
def reset_state():
    return None, [], {}

current_id = None         # e.g. 'ID-1'
mode = None               # 'world' or 'crossing'
current_pts = []          # list of clicked points
world_intersections = {}  # id -> [pt1,...,pt4]
crossing_lines = {}       # id -> [pt1, pt2]

# Mouse callback
def on_mouse(event, x, y, flags, param):
    global current_pts
    if event == cv2.EVENT_LBUTTONDOWN and mode in ('world', 'crossing'):
        current_pts.append((x, y))
        print(f"Clicked point {len(current_pts)} at {(x, y)} for {current_id}")

# Display instructions
def print_instructions():
    print("\n=== Instructions ===")
    print("c → capture reference frame")
    print("1-4 → start world annotation for that ID")
    print("v → start crossing-line mode, then press 1-4 to select ID")
    print("n → finish current shape and save")
    print("s → save CSVs and exit")
    print("q → quit without saving")
    print("====================\n")

# ---------------------------------------------------------------------
# Step 1: Capture reference frame
# ---------------------------------------------------------------------
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print(f"Error opening {VIDEO_PATH}")
    exit(1)
print("Press 'c' to capture reference frame or 'q' to quit.")
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read video.")
        cap.release()
        exit(1)
    cv2.imshow("Capture", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('c'):
        ref = frame.copy()
        cv2.destroyWindow("Capture")
        break
    elif key == ord('q'):
        print("Exiting before annotation.")
        cap.release()
        cv2.destroyAllWindows()
        exit(0)

# ---------------------------------------------------------------------
# Step 2: Annotation Mode
# ---------------------------------------------------------------------
cv2.namedWindow("Annotate")
cv2.setMouseCallback("Annotate", on_mouse)
print_instructions()
while True:
    disp = ref.copy()
    # draw world polygons
    for iid, pts in world_intersections.items():
        if len(pts) == 4:
            arr = np.array(pts, np.int32)
            cv2.polylines(disp, [arr], True, (0,255,0), 2)
            cv2.putText(disp, iid, arr[0], cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    # draw crossing lines
    for iid, pts in crossing_lines.items():
        if len(pts) == 2:
            cv2.line(disp, pts[0], pts[1], (0,0,255), 2)
            cv2.putText(disp, iid, pts[0], cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)
    # draw in-progress
    for pt in current_pts:
        cv2.circle(disp, pt, 4, (255,255,0), -1)
    cv2.imshow("Annotate", disp)
    key = cv2.waitKey(0) & 0xFF
    # world mode
    if key in [ord(str(d)) for d in [1,2,3,4]] and mode is None:
        current_id = f"ID-{chr(key)}"
        mode = 'world'
        current_pts = []
        print(f"World homography: click 4 points for {current_id}")
    # crossing mode
    elif key == ord('v') and mode is None:
        print("Press 1-4 to select intersection for crossing line")
        sub = cv2.waitKey(0) & 0xFF
        if sub in [ord(str(d)) for d in [1,2,3,4]]:
            current_id = f"ID-{chr(sub)}"
            mode = 'crossing'
            current_pts = []
            print(f"Crossing line: click 2 points for {current_id}")
    # finish shape
    elif key == ord('n') and mode:
        if mode == 'world' and len(current_pts) == 4:
            world_intersections[current_id] = current_pts.copy()
            print(f"Saved world_intersections['{current_id}']={current_pts}")
        elif mode == 'crossing' and len(current_pts) == 2:
            crossing_lines[current_id] = current_pts.copy()
            print(f"Saved crossing_lines['{current_id}']={current_pts}")
        else:
            print(f"Invalid pts count ({len(current_pts)}) for mode '{mode}'")
        mode = None
        current_pts = []
    elif key == ord('s'):
        print("Annotations complete. Saving CSVs...")
        break
    elif key == ord('q'):
        print("Quitting without saving.")
        exit(0)
cv2.destroyAllWindows()

# ---------------------------------------------------------------------
# Step 3: Save CSVs
# ---------------------------------------------------------------------
print(f"Final world_intersections: {world_intersections}")
print(f"Final crossing_lines: {crossing_lines}")
# write world_intersections.csv
with open(OUTPUT_DIR / 'world_intersections.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['id','x1','y1','x2','y2','x3','y3','x4','y4'])
    for iid, pts in world_intersections.items():
        writer.writerow([iid] + [coord for pt in pts for coord in pt])
# write crossing_lines.csv
with open(OUTPUT_DIR / 'crossing_lines.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['id','x1','y1','x2','y2'])
    for iid, pts in crossing_lines.items():
        writer.writerow([iid] + [coord for pt in pts for coord in pt])

print("Saved: world_intersections.csv and crossing_lines.csv")
