import cv2
import csv
import numpy as np
from pathlib import Path

# =============================================================================
# Dynamic Annotation + Export Tool
# Combines interactive annotation with per-frame SIFT-based warping
# =============================================================================

# --- CONFIG ---
VIDEO_PATH = r"C:\Users\odysh\OneDrive\Desktop\Preprocessing_Yolo_input\videos\15-min-testing.mp4"
OUTPUT_DIR = Path.cwd()

# --- Globals ---
current_id = None       # e.g. 'ID-1'
mode = None             # 'world' or 'crossing'
current_pts = []        # clicked points
world_intersections = {}  # id -> [4 pts]
crossing_lines = {}       # id -> [2 pts]

# --- Mouse callback ---
def on_mouse(event, x, y, flags, param):
    global current_pts
    if event == cv2.EVENT_LBUTTONDOWN and mode in ('world','crossing'):
        current_pts.append((x,y))
        print(f"Clicked {len(current_pts)} for {current_id}: {(x,y)}")

# --- Instructions ---
def print_instructions():
    print("\n=== INSTRUCTIONS ===")
    print("c : capture reference frame")
    print("1-4 : start world homography for that intersection")
    print("v then 1-4 : start crossing-line for that intersection")
    print("n : finish current shape and save")
    print("s : save CSVs & proceed to export")
    print("q : quit without saving")
    print("====================\n")

# --- Step 1: capture reference ---
cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise IOError(f"Cannot open {VIDEO_PATH}")

print("Press 'c' to select reference frame, 'q' to quit.")
cv2.namedWindow("Select Ref", cv2.WINDOW_NORMAL)
while True:
    ret, frame = cap.read()
    if not ret:
        raise RuntimeError("End of video before selecting reference.")
    cv2.imshow("Select Ref", frame)
    k = cv2.waitKey(30) & 0xFF
    if k == ord('c'):
        ref_frame = frame.copy()
        cv2.destroyWindow("Select Ref")
        break
    elif k == ord('q'):
        cap.release(); cv2.destroyAllWindows(); exit(0)

# --- Step 2: annotate on ref ---
cv2.namedWindow("Annotate", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Annotate", on_mouse)
print_instructions()
while True:
    disp = ref_frame.copy()
    # draw existing
    for iid, pts in world_intersections.items():
        if len(pts)==4:
            cv2.polylines(disp, [np.array(pts,np.int32)], True, (0,255,0),2)
            cv2.putText(disp, iid, pts[0], cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
    for iid, pts in crossing_lines.items():
        if len(pts)==2:
            cv2.line(disp, pts[0], pts[1], (0,0,255),2)
            cv2.putText(disp, iid, pts[0], cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,255),2)
    for pt in current_pts:
        cv2.circle(disp, pt, 4, (255,255,0),-1)
    cv2.imshow("Annotate", disp)
    k = cv2.waitKey(0) & 0xFF
    # world mode
    if k in map(ord, ['1','2','3','4']) and mode is None:
        current_id = f"ID-{chr(k)}"
        mode = 'world'
        current_pts = []
        print(f"Annotate 4 pts for {current_id}")
    # crossing line mode
    elif k == ord('v') and mode is None:
        print("Press 1-4 to pick intersection for crossing line")
        sub = cv2.waitKey(0) & 0xFF
        if sub in map(ord,['1','2','3','4']):
            current_id = f"ID-{chr(sub)}"
            mode = 'crossing'
            current_pts = []
            print(f"Annotate 2 pts for crossing {current_id}")
    # finish shape
    elif k == ord('n') and mode:
        if mode=='world' and len(current_pts)==4:
            world_intersections[current_id] = current_pts.copy()
            print(f"Saved world[{current_id}]: {current_pts}")
        elif mode=='crossing' and len(current_pts)==2:
            crossing_lines[current_id] = current_pts.copy()
            print(f"Saved crossing[{current_id}]: {current_pts}")
        else:
            print(f"Invalid pts count for {mode}")
        mode=None; current_pts=[]
    elif k == ord('s'):
        print("Saving CSVs and exporting...")
        break
    elif k == ord('q'):
        print("Quit without saving.")
        exit(0)
cv2.destroyAllWindows()

# --- write static CSVs ---
with open(OUTPUT_DIR/'world_intersections.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['id','x1','y1','x2','y2','x3','y3','x4','y4'])
    for iid,pts in world_intersections.items():
        w.writerow([iid]+[c for pt in pts for c in pt])
with open(OUTPUT_DIR/'crossing_lines.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['id','x1','y1','x2','y2'])
    for iid,pts in crossing_lines.items():
        w.writerow([iid]+[c for pt in pts for c in pt])

print("Static annotations saved.")

# =============================================================================
# EXPORT: Dynamic per-frame transformation
# =============================================================================

def compute_dynamic_homography(ref,cur):
    g1,g2 = cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY), cv2.cvtColor(cur,cv2.COLOR_BGR2GRAY)
    sift=cv2.SIFT_create()
    k1,d1=sift.detectAndCompute(g1,None); k2,d2=sift.detectAndCompute(g2,None)
    if d1 is None or d2 is None: return None
    bf=cv2.BFMatcher(cv2.NORM_L2); m=bf.knnMatch(d1,d2,k=2)
    good=[x for x,y in m if x.distance<0.75*y.distance]
    if len(good)<10: return None
    src=np.float32([k1[x.queryIdx].pt for x in good]).reshape(-1,1,2)
    dst=np.float32([k2[x.trainIdx].pt for x in good]).reshape(-1,1,2)
    H,_=cv2.findHomography(src,dst,cv2.RANSAC,5.0); return H

# prepare export CSVs
dyn_poly=open(OUTPUT_DIR/'dynamic_polygons.csv','w',newline='')
dyn_line=open(OUTPUT_DIR/'dynamic_lines.csv','w',newline='')
pw=csv.writer(dyn_poly); lw=csv.writer(dyn_line)
pw.writerow(['frame','id','x1','y1','x2','y2','x3','y3','x4','y4'])
lw.writerow(['frame','id','x1','y1','x2','y2'])

# read static back into arrays
world={} ; lines={}
with open(OUTPUT_DIR/'world_intersections.csv') as f:
    for r in csv.DictReader(f):
        world[r['id']] = np.array([
            [float(r['x1']),float(r['y1'])],
            [float(r['x2']),float(r['y2'])],
            [float(r['x3']),float(r['y3'])],
            [float(r['x4']),float(r['y4'])]
        ], np.float32)
with open(OUTPUT_DIR/'crossing_lines.csv') as f:
    for r in csv.DictReader(f):
        lines[r['id']] = np.array([
            [float(r['x1']),float(r['y1'])],
            [float(r['x2']),float(r['y2'])]
        ], np.float32)

# rewind video for export
cap.set(cv2.CAP_PROP_POS_FRAMES,0)
frame_idx=0; last_H=None
while True:
    ret,frm=cap.read()
    if not ret: break
    frame_idx+=1
    H=compute_dynamic_homography(ref_frame,frm)
    if H is not None: last_H=H
    if last_H is None: continue

    # dynamic polygons
    for iid,pts in world.items():
        pts_arr = pts.reshape(-1,1,2)  # now numpy, reshape works
        warped = cv2.perspectiveTransform(pts_arr, last_H).reshape(-1,2)
        pw.writerow([frame_idx,iid] + warped.flatten().tolist())

    # dynamic lines
    for iid,pts in lines.items():
        pts_arr = pts.reshape(-1,1,2)
        warped = cv2.perspectiveTransform(pts_arr, last_H).reshape(-1,2)
        lw.writerow([frame_idx,iid] + warped.flatten().tolist())

cap.release(); dyn_poly.close(); dyn_line.close()
print("Dynamic export complete:")
print(" - dynamic_polygons.csv")
print(" - dynamic_lines.csv")
