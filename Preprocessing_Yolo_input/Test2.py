import cv2
import math
import numpy as np
import pyautogui

# === TRAFFIC LIGHT CONFIGURATION ===
traffic_lights_positions = {
    # ID‑1 split into two panels, one below the other
    "ID-1-F": (35, 150),
    "ID-1-L": (35, 290),
    # ID‑2 combined
    "ID-2":   (125, 150),
    # ID‑3 split
    "ID-3-F": (200, 150),
    "ID-3-L": (200, 290),
    # ID‑4 combined
    "ID-4":   (290, 150)
}

screen_w, screen_h = pyautogui.size()

# 25 FPS → frame windows for green states (start_frame, end_frame)
#       Traffic Lights Frames count for scheduling
#           for 14 sec ----> 350
#           for 44 sec ----> 1100
#
traffic_light_schedule = {'ID-1-F': [(1020, 2250),
            (4020, 5250),
            (7020, 8250),
            (10020, 11250),
            (13110, 14340),
            (16200, 17430),
            (19290, 20520),
            (22200, 23610),
            (25200, 26700)],
 'ID-1-L': [(1020, 1470),
            (4020, 4470),
            (7020, 7470),
            (10020, 10750),    #fixed
            (13110, 13560),
            (16200, 16650),
            (19290, 19740),
            (22200, 22830),
            (25200, 25920)],
 'ID-2': [(0, 360),
          (3000, 3360),
          (6000, 6360),
          (9000, 9360),
          (12000, 12390),
          (15000, 15480),
          (18050, 18460),
          (21000, 21500),
          (24100, 24450)],
 'ID-3-F': [(1620, 2850),
            (4620, 5850),
            (7620, 8850),
            (10900, 11850),
            (13710, 14850),
            (16800, 17900),
            (19890, 20850),
            (22980, 23950),
            (26070, 26850)],
 'ID-3-L': [(2400, 2850),
            (5400, 5850),
            (8400, 8850),
            (11400, 11850),
            (14490, 14850),
            (17580, 17900),
            (20670, 20850),
            (23760, 23950)],
 'ID-4': [(510, 870),
          (3510, 3870),
          (6510, 6870),
          (9510, 9870),
          (12540, 12960),
          (15630, 16050),
          (18610, 19140),
          (21650, 22050),
          (24600, 25050)]}


# World coords for your 4‑point homography per intersection
world_intersections = {
    "ID-1": np.array([[524,335],[528,346],[827,221],[834,238]], dtype=np.float32),
    "ID-2": np.array([[524,335],[528,346],[827,221],[834,238]], dtype=np.float32),
    "ID-3": np.array([[524,335],[528,346],[827,221],[834,238]], dtype=np.float32),
    "ID-4": np.array([[524,335],[528,346],[827,221],[834,238]], dtype=np.float32)
}


intersection_colors = {
    "ID-1": (255, 0,   0),
    "ID-2": (0,   255, 0),
    "ID-3": (0,   0,   255),
    "ID-4": (255, 255, 0)
}

# BGR color constants
base_green  = (  0,255,  0)
dark_green  = (  0,100,  0)
base_yellow = (  0,255,255)
dark_yellow = (  0,150,150)
base_red    = (  0,  0,255)
dark_red    = (  0,  0,100)

panel_width   = 20
panel_height  = 90
circle_radius = 8
crossing_offset = 9

def get_circle_centers(center):
    cx, cy = center
    return (
        (cx, int(cy - panel_height/3)),
        (cx, cy),
        (cx, int(cy + panel_height/3))
    )
# /////////////////////////////////////////////////////////////////////
def get_panel_colors_by_schedule(light_id, frame_count):
    for start, end in traffic_light_schedule.get(light_id, []):
        # yellow BEFORE green (red→yellow)
        if start - 75 <= frame_count < start:
            return dark_red, base_yellow, dark_green
        # green phase
        if start <= frame_count < end:
            return dark_red, dark_yellow, base_green
        # yellow BEFORE red (green→yellow)
        if end <= frame_count < end + 75:
            return dark_red, base_yellow, dark_green
    # default RED
    return base_red, dark_yellow, dark_green


# //////////////////////////////////////////////////////////////////////////////////
def get_light_state(lid, fcount):
    for start, end in traffic_light_schedule.get(lid, []):
        # yellow before green
        if start - 75 <= fcount < start:
            return 'yellow'
        # green
        if start <= fcount < end:
            return 'green'
        # yellow after green
        if end <= fcount < end + 75:
            return 'yellow'
    return 'red'

def draw_direction_arrows(frame, center, color):
    cx, cy = center
    arrow_y = cy - panel_height//2 - 10
    # ← arrow
    cv2.arrowedLine(frame,
                    (cx-10, arrow_y),
                    (cx-30, arrow_y),
                    color, 2, tipLength=0.3)
    # ↑ arrow
    cv2.arrowedLine(frame,
                    (cx+10, arrow_y),
                    (cx+10, arrow_y-20),
                    color, 2, tipLength=0.3)

def transform_points(pts, H):
    pts = pts.reshape(-1,1,2)
    t   = cv2.perspectiveTransform(pts, H)
    return t.reshape(-1,2).astype(np.int32)

def compute_dynamic_homography(ref_img, cur_img):
    g1 = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(cur_img, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create()
    k1,d1 = sift.detectAndCompute(g1, None)
    k2,d2 = sift.detectAndCompute(g2, None)
    if d1 is None or d2 is None: return None
    bf = cv2.BFMatcher(cv2.NORM_L2)
    m = bf.knnMatch(d1, d2, k=2)
    good = [x for x,y in m if x.distance < 0.75*y.distance]
    if len(good) < 10: return None
    src = np.float32([k1[x.queryIdx].pt for x in good]).reshape(-1,1,2)
    dst = np.float32([k2[x.trainIdx].pt for x in good]).reshape(-1,1,2)
    H,_ = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return H

# --- ANNOTATION SETUP ---
current_annotation_id = None
annotations = {k:[] for k in world_intersections}
intersection_homographies = {}
current_mask_mode       = False
current_mask_annotation = []
mask_polygons           = []
current_crossing_mode   = False
current_crossing_annotation = []
current_crossing_id     = None
crossing_lines          = {}

def mouse_callback_ref(evt, x, y, flags, param):
    global current_annotation_id, current_mask_mode, current_mask_annotation
    global current_crossing_mode, current_crossing_annotation, current_crossing_id
    if evt == cv2.EVENT_LBUTTONDOWN:
        if current_annotation_id:
            annotations[current_annotation_id].append((x,y))
            print(f"{current_annotation_id}: point {(x,y)} ({len(annotations[current_annotation_id])}/4)")
            if len(annotations[current_annotation_id])==4:
                src = world_intersections[current_annotation_id]
                dst = np.array(annotations[current_annotation_id], np.float32)
                H,_ = cv2.findHomography(src, dst, cv2.RANSAC)
                intersection_homographies[current_annotation_id]=H
                print(f"H for {current_annotation_id}:\n{H}")
                current_annotation_id=None
        elif current_mask_mode:
            current_mask_annotation.append((x,y))
        elif current_crossing_mode:
            current_crossing_annotation.append((x,y))

# --- STEP 1: SELECT REF FRAME ---
video_path = r"C:\Users\odysh\OneDrive\Desktop\Preprocessing_Yolo_input\videos\15-min-testing.mp4"
cap = cv2.VideoCapture(video_path)

if not cap.isOpened(): raise Exception("Cannot open video")

# prepare output writer at original size
fps = int(cap.get(cv2.CAP_PROP_FPS))
w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
out = cv2.VideoWriter("output_video.mp4",
                      cv2.VideoWriter_fourcc(*"mp4v"),
                      fps, (w, h))

# create a resizable window
cv2.namedWindow("Dynamic Intersection Overlays", cv2.WINDOW_NORMAL)
#
cv2.namedWindow("Select Reference Frame")
while True:
    ret, frm = cap.read()
    if not ret: raise Exception("Can't read")
    cv2.putText(frm, "Press 'c' to capture, 'q' to quit", (10,30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0),2)
    cv2.imshow("Select Reference Frame", frm)
    k = cv2.waitKey(30)&0xFF
    if k==ord('c'):
        ref_frame = frm.copy()
        break
    if k==ord('q'):
        cap.release(); cv2.destroyAllWindows(); exit()
cv2.destroyWindow("Select Reference Frame")

# --- STEP 2: ANNOTATION MODE ---
cv2.namedWindow("Reference Frame")
cv2.setMouseCallback("Reference Frame", mouse_callback_ref)
print("1-4: intersections | x/p: mask | v/d: crossing | s: start")
while True:
    tmp = ref_frame.copy()
    # draw intersections
    for k,H in intersection_homographies.items():
        poly = transform_points(world_intersections[k], H)
        cv2.polylines(tmp, [poly], True, (0,0,255),1)
    # draw masks
    for poly in mask_polygons:
        cv2.polylines(tmp, [poly.astype(int)], True, (0,0,0),1)
    if current_mask_mode and current_mask_annotation:
        p = np.array(current_mask_annotation,np.int32)
        cv2.polylines(tmp, [p], False, (0,0,0),1)
    # draw crossing-lines
    for poly in crossing_lines.values():
        cv2.polylines(tmp, [poly.astype(int)], False, (0,255,255),1)
    if current_crossing_mode and current_crossing_annotation:
        p = np.array(current_crossing_annotation,np.int32)
        cv2.polylines(tmp, [p], False, (0,255,255),1)

    cv2.imshow("Reference Frame", tmp)
    k = cv2.waitKey(0)&0xFF
    if k==ord('s'): break
    if k in [ord('1'),ord('2'),ord('3'),ord('4')]:
        current_annotation_id = f"ID-{chr(k)}"
        annotations[current_annotation_id]=[]
    elif k==ord('x'):
        current_mask_mode=True; current_mask_annotation=[]
    elif k==ord('p') and current_mask_mode and len(current_mask_annotation)>=3:
        mask_polygons.append(np.array(current_mask_annotation,np.float32))
        current_mask_mode=False; current_mask_annotation=[]
    elif k==ord('v'):
        print("Crossing ID (1-4)?")
        sub = cv2.waitKey(0)&0xFF
        cid = f"ID-{chr(sub)}"
        if cid in intersection_homographies:
            current_crossing_mode=True
            current_crossing_id=cid
            current_crossing_annotation=[]
    elif k==ord('d') and current_crossing_mode and len(current_crossing_annotation)>=2:
        crossing_lines[current_crossing_id] = np.array(current_crossing_annotation,np.float32)
        current_crossing_mode=False
        current_crossing_annotation=[]
        current_crossing_id=None

cv2.destroyWindow("Reference Frame")

# --- STEP 3: RESET & OUTPUT SETUP ---
cap.release()
cap = cv2.VideoCapture(video_path)
fps = int(cap.get(cv2.CAP_PROP_FPS))
w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
out = cv2.VideoWriter("output_video.mp4", cv2.VideoWriter_fourcc(*"mp4v"), fps, (w,h))

# --- STEP 4: MAIN LOOP ---
frame_count = 0
while True:
    ret, frame = cap.read()
    if not ret: break
    frame_count += 1

    Hdyn = compute_dynamic_homography(ref_frame, frame)

    # draw static traffic lights
    for lid, ctr in traffic_lights_positions.items():
        r,y,g = get_panel_colors_by_schedule(lid, frame_count)
        tl = (int(ctr[0]-panel_width/2), int(ctr[1]-panel_height/2))
        br = (int(ctr[0]+panel_width/2), int(ctr[1]+panel_height/2))
        cv2.rectangle(frame, tl, br, (255,255,255), -1)
        rc,yc,gc = get_circle_centers(ctr)
        cv2.circle(frame, rc, circle_radius, r, -1)
        cv2.circle(frame, yc, circle_radius, y, -1)
        cv2.circle(frame, gc, circle_radius, g, -1)
        cv2.putText(frame, lid, (br[0]+5, ctr[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255),1)

        # arrows on ID-2 & ID-4
        if lid in ("ID-2","ID-4"):
            st = get_light_state(lid, frame_count)
            col = base_green if st=="green" else base_yellow if st=="yellow" else base_red
            draw_direction_arrows(frame, ctr, col)
            # arrows on split panels ID-1 and ID-3: only UP for *-F, only LEFT for *-L
        if lid in ("ID-1-F", "ID-3-F", "ID-1-L", "ID-3-L"):
            state = get_light_state(lid, frame_count)
            col = base_green if state == "green" else base_yellow if state == "yellow" else base_red
            arrow_y = ctr[1] - panel_height // 2 - 10

            if lid.endswith("-F"):
                # upward arrow
                cv2.arrowedLine(
                    frame,
                    (ctr[0], arrow_y),
                    (ctr[0], arrow_y - 20),
                    col, 2, tipLength=0.3
                )
            else:
                # leftward arrow
                cv2.arrowedLine(
                    frame,
                    (ctr[0] - 10, arrow_y),
                    (ctr[0] - 30, arrow_y),
                    col, 2, tipLength=0.3
                )


    # dynamic homography overlays & crossing lines
    if Hdyn is not None:
        for key,H in intersection_homographies.items():
            Htot = Hdyn.dot(H)
            poly = transform_points(world_intersections[key], Htot)
            col  = intersection_colors[key]
            cv2.polylines(frame, [poly], True, col,1)
            cv2.putText(frame, key, (poly[0][0], poly[0][1]-10),
                        cv2.FONT_HERSHEY_SIMPLEX,0.5,col,1)
            if len(poly)>=2:
                p1,p2 = poly[0], poly[1]
                v = p2-p1
                n = np.linalg.norm(v)
                if n>1e-5:
                    d = v/n
                    perp = np.array([-d[1], d[0]])
                    if key in ("ID-2","ID-3","ID-4"):
                        perp = -perp
                    pn = np.linalg.norm(perp)
                    if pn>1e-5:
                        perp /= pn
                        c1 = (p1 + crossing_offset*perp).astype(int)
                        c2 = (p2 + crossing_offset*perp).astype(int)
                        if key in ("ID-1", "ID-3"):
                            sF = get_light_state(f"{key}-F", frame_count)
                            sL = get_light_state(f"{key}-L", frame_count)
                            # if both sub-signals are red → red, otherwise green
                            linecol = base_red if (sF == "red" and sL == "red") else base_green
                        else:
                            state = get_light_state(key, frame_count)
                            # yellow now counts as green
                            linecol = base_green if state in ("green", "yellow") else base_red

                        cv2.line(frame, tuple(c1), tuple(c2), linecol, 1)

    # masks
    if Hdyn is not None and mask_polygons:
        for m in mask_polygons:
            tm = transform_points(m, Hdyn)
            cv2.fillPoly(frame,[tm],(0,0,0))

    cv2.putText(frame, f"Frame: {frame_count}", (20,60),
                cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2)
    frame_resized = cv2.resize(frame, (screen_w, screen_h),
                               interpolation=cv2.INTER_LINEAR)
    cv2.imshow("Dynamic Intersection Overlays", frame_resized)
    out.write(frame)

    if cv2.waitKey(1)&0xFF==ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()
print("Processed video saved to output_video.mp4")