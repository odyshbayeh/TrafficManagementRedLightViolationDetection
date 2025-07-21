import time
import threading
import pygame
import sys
import os
import json
import cv2  # ADD THIS LINE
from pymongo import MongoClient

FPS = 30

def phase_speed(num_cars: int, duration: float, direction: str) -> float:
    if num_cars <= 0 or duration <= 0:
        return speeds['car']    # fallback

    d_first = 900
    car_len = 60 if direction in ('left', 'right') else 30
    g       = gap2

    px_per_second = (d_first + (num_cars - 1) * (car_len + g)) / duration
    px_per_frame  = px_per_second / FPS              # <<< THE IMPORTANT LINE
    return max(0.05, min(px_per_frame, 1.5))         # clamp for safety

def fetch_phases_from_db(chunk_number: int | None = 0):
    query = {} if chunk_number is None else {"chunk": chunk_number}

    doc = records.find_one(
        query,
        projection={"recommendations": 1, "_id": 0},  # <-- keep ONLY this field
        sort=[("_id", -1)]
    )

    if not doc or "recommendations" not in doc:
        raise RuntimeError(f"No schedule document matched {query}")

    # print(f"Fetched schedule document with chunk {chunk_number} from MongoDB: {doc['recommendations']}")
    return doc["recommendations"]

# ──────────────────────────────────────────────────────────────
#  Load several chunks and merge their "recommendations" arrays
# ──────────────────────────────────────────────────────────────
def fetch_phases_for_chunks(chunk_nums: list[int]) -> list[dict]:
    merged: list[dict] = []
    for num in chunk_nums:
        try:
            merged.extend(fetch_phases_from_db(num))
        except RuntimeError as exc:
            print(f"[WARN] {exc} — chunk {num} skipped.")
    if not merged:
        raise RuntimeError("No phases found for any requested chunk!")
    return merged

# MongoDB connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://nafe:0597785625nafe@coffeeshop.s8duwhp.mongodb.net/?retryWrites=true&w=majority"
)
DB_NAME = os.getenv("DB_NAME", "trafficmanagement")
COL_NAME = os.getenv("COL_NAME", "records")

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[DB_NAME]
records = mongo_db[COL_NAME]

defaultRed = 150
defaultYellow = 5
defaultGreen = 20
defaultMinimum = 10
defaultMaximum = 60

signals = []
noOfSignals = 4
timeElapsed = 0
noOfLanes = 2

speeds = {'car': 2.5}
x = {'right': [0, 0], 'down': [615, 670], 'left': [1400, 1400], 'up': [752, 777]}
y = {'right': [385, 435], 'down': [0, 0], 'left': [330, 280], 'up': [800, 800]}

vehicles = {
    'right': {0: [], 1: [], 'crossed': 0},
    'down': {0: [], 1: [], 'crossed': 0},
    'left': {0: [], 1: [], 'crossed': 0},
    'up': {0: [], 1: [], 'crossed': 0}
}

ID_TO_DIRECTION_INDEX = {
    'ID-1': 2,  # left
    'ID-2': 1,  # down
    'ID-3': 3,  # right
    'ID-4': 0,  # up
}

ID_TO_DIRECTION = {
    'ID-1': 'left',
    'ID-2': 'down',
    'ID-3': 'right',
    'ID-4': 'up',
}

signalCoods = {
    'ID-1': (950, 100),
    'ID-2': (450, 100),
    'ID-3': (450, 550),
    'ID-4': (950, 550)
}

signalTimerCoods = {
    'ID-1': (980, 80),
    'ID-2': (480, 80),
    'ID-3': (480, 530),
    'ID-4': (980, 530)
}

vehicleCountCoods = {
    'ID-1': (930, 80),
    'ID-2': (430, 80),
    'ID-3': (430, 530),
    'ID-4': (930, 530)
}

stopLines = {'right': 535, 'down': 255, 'left': 880, 'up': 490}
defaultStop = {'right': 535, 'down': 255, 'left': 880, 'up': 490}
stops = {'right': [535, 535], 'down': [255, 255], 'left': [880, 880], 'up': [490, 490]}

gap = 15
gap2 = 15

pygame.init()
simulation = pygame.sprite.Group()

green_signal_timer = {"ID-1": 0, "ID-2": 0, "ID-3": 0, "ID-4": 0}
current_green_id = None
current_green_phase_end = 0

cumulative_cross_count = {"ID-1": 0, "ID-2": 0, "ID-3": 0, "ID-4": 0}
live_phase_cross_count = {"ID-1": 0, "ID-2": 0, "ID-3": 0, "ID-4": 0}

simulation_done = False


class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.totalGreenTime = 0


class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, direction_number, direction, speed=None):
        pygame.sprite.Sprite.__init__(self)
        self.lane = lane
        self.vehicleClass = 'car'
        self.speed = speed if speed is not None else speeds['car']  # عدل هذا السطر
        self.direction_number = direction_number
        self.direction = direction
        self.x = x[direction][lane]
        self.y = y[direction][lane]
        self.crossed = 0

        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1

        path = os.path.join("images/car1.png")
        try:
            base_img = pygame.image.load(path)
        except Exception:
            base_img = pygame.Surface((40, 20))
            base_img.fill((255, 0, 0))

        if self.direction == 'right':
            self.currentImage = base_img
        elif self.direction == 'down':
            self.currentImage = pygame.transform.rotate(base_img, -90)
        elif self.direction == 'left':
            self.currentImage = pygame.transform.rotate(base_img, 180)
        elif self.direction == 'up':
            self.currentImage = pygame.transform.rotate(base_img, 90)
        else:
            self.currentImage = base_img

        if direction == 'right':
            if self.index > 0 and vehicles[direction][lane][self.index - 1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index - 1].stop - \
                            vehicles[direction][lane][self.index - 1].currentImage.get_rect().width - gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().width + gap
            x[direction][lane] -= temp
            stops[direction][lane] -= temp
        elif direction == 'left':
            if self.index > 0 and vehicles[direction][lane][self.index - 1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index - 1].stop + \
                            vehicles[direction][lane][self.index - 1].currentImage.get_rect().width + gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().width + gap
            x[direction][lane] += temp
            stops[direction][lane] += temp
        elif direction == 'down':
            if self.index > 0 and vehicles[direction][lane][self.index - 1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index - 1].stop - \
                            vehicles[direction][lane][self.index - 1].currentImage.get_rect().height - gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().height + gap
            y[direction][lane] -= temp
            stops[direction][lane] -= temp
        elif direction == 'up':
            if self.index > 0 and vehicles[direction][lane][self.index - 1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index - 1].stop + \
                            vehicles[direction][lane][self.index - 1].currentImage.get_rect().height + gap
            else:
                self.stop = defaultStop[direction]
            temp = self.currentImage.get_rect().height + gap
            y[direction][lane] += temp
            stops[direction][lane] += temp

        simulation.add(self)

    def render(self, screen):
        screen.blit(self.currentImage, (self.x, self.y))

    def move(self):
        signal = signals[self.direction_number]
        id_map = {2: 'ID-1', 1: 'ID-2', 3: 'ID-3', 0: 'ID-4'}
        my_id = id_map[self.direction_number]
        global live_phase_cross_count, cumulative_cross_count, current_green_id

        # ما هو خط التوقف الحقيقي؟ إذا الإشارة خضراء، استخدم self.stop، إذا أصفر/أحمر، استخدم خط التوقف العام
        if signal.green > 0 and current_green_id == my_id:
            effective_stop = self.stop
        else:
            effective_stop = stopLines[self.direction]

        if self.direction == 'right':
            if (self.crossed == 0 and
                    self.x + self.currentImage.get_rect().width > stopLines[self.direction] and
                    current_green_id == my_id and signal.green > 0):
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
                live_phase_cross_count[my_id] += 1
                cumulative_cross_count[my_id] += 1

            # Use effective_stop instead of self.stop
            if ((self.x + self.currentImage.get_rect().width <= effective_stop or self.crossed == 1 or
                 (signal.green > 0)) and
                    (self.index == 0 or self.x + self.currentImage.get_rect().width <
                     (vehicles[self.direction][self.lane][self.index - 1].x - gap2))):
                self.x += self.speed * 1.5

        elif self.direction == 'down':
            if (self.crossed == 0 and
                    self.y + self.currentImage.get_rect().height > stopLines[self.direction] and
                    current_green_id == my_id and signal.green > 0):
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
                live_phase_cross_count[my_id] += 1
                cumulative_cross_count[my_id] += 1

            if ((self.y + self.currentImage.get_rect().height <= effective_stop or self.crossed == 1 or
                 (signal.green > 0)) and
                    (self.index == 0 or self.y + self.currentImage.get_rect().height <
                     (vehicles[self.direction][self.lane][self.index - 1].y - gap2))):
                self.y += self.speed * 2
                

        elif self.direction == 'left':
            if (self.crossed == 0 and
                    self.x < stopLines[self.direction] and
                    current_green_id == my_id and signal.green > 0):
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
                live_phase_cross_count[my_id] += 1
                cumulative_cross_count[my_id] += 1

            if ((self.x >= effective_stop or self.crossed == 1 or (signal.green > 0)) and
                    (self.index == 0 or self.x >
                     (vehicles[self.direction][self.lane][self.index - 1].x +
                      vehicles[self.direction][self.lane][self.index - 1].currentImage.get_rect().width + gap2))):
                self.x -= self.speed * 0.75

        elif self.direction == 'up':
            if (self.crossed == 0 and
                    self.y < stopLines[self.direction] and
                    current_green_id == my_id and signal.green > 0):
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
                live_phase_cross_count[my_id] += 1
                cumulative_cross_count[my_id] += 1

            if ((self.y >= effective_stop or self.crossed == 1 or (signal.green > 0)) and
                    (self.index == 0 or self.y >
                     (vehicles[self.direction][self.lane][self.index - 1].y +
                      vehicles[self.direction][self.lane][self.index - 1].currentImage.get_rect().height + gap2))):
                self.y -= self.speed * 2


def run_phases_from_json(phases):
    global timeElapsed, green_signal_timer, current_green_id, current_green_phase_end, live_phase_cross_count
    global simulation_done

    max_seen_cars = {"ID-1": 0, "ID-2": 0, "ID-3": 0, "ID-4": 0}
    last_recommended_phase = {"ID-1": None, "ID-2": None, "ID-3": None, "ID-4": None}
    last_manual_added_count = {"ID-1": None, "ID-2": None, "ID-3": None, "ID-4": None}
    last_current_phase = {"ID-1": None, "ID-2": None, "ID-3": None, "ID-4": None}

    for idx, phase in enumerate(phases):
        all_states = phase['all_states']
        duration = phase['duration_sec']
        counts = phase['all_counts']
        recommended = phase.get('recommended', None)
        current = phase.get('current', None)
        print(f"\n---------------------------")
        print(f"PHASE idx={idx} | recommended={recommended} | current={current}")
        print(f"last_recommended_phase: {last_recommended_phase}")
        print(f"last_manual_added_count: {last_manual_added_count}")
        print(f"last_current_phase: {last_current_phase}")
        print(f"all_counts: {counts}")

        # Update last phase in which each ID was current
        if current:
            last_current_phase[current] = idx

        if idx == 0:
            print("[INIT] Spawning vehicles for all IDs in first phase...")
            for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
                direction = ID_TO_DIRECTION[id]
                dir_index = ID_TO_DIRECTION_INDEX[id]
                num_cars = counts[id]
                is_yellow = all_states[id] == "yellow"
                # my_speed = 2.5 if is_yellow else speeds['car']
                # find the speed that will exhaust the green exactly
                v = phase_speed(num_cars=counts[id],               # N
                duration=duration,                # T
                direction=direction)              # to pick correct car_le

                if direction in ['down', 'up']:
                    for _ in range(num_cars):
                        Vehicle(0, dir_index, direction, speed=v)
                else:
                    for lane in range(noOfLanes):
                        cars_per_lane = num_cars // noOfLanes
                        extra = num_cars % noOfLanes
                        for _ in range(cars_per_lane + (1 if lane < extra else 0)):
                            Vehicle(lane, dir_index, direction, speed=v)
            for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
                max_seen_cars[id] = counts[id]
            if recommended:
                last_recommended_phase[recommended] = idx
                last_manual_added_count[recommended] = None
        else:
            for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
                last_phase = last_recommended_phase[id]
                last_current = last_current_phase[id]
                diff_idx = idx - last_phase if last_phase is not None else None

                # -- الحالة 1: إذا الـID كان current في الفيز قبل ما يصير recommended، أضف السيارات بعد فيز واحد فقط --
                if (last_phase is not None and last_current is not None
                        and last_current == last_phase - 1 and diff_idx == 1):
                    cars_now = counts[id]
                    direction = ID_TO_DIRECTION[id]
                    dir_index = ID_TO_DIRECTION_INDEX[id]
                    is_yellow = all_states[id] == "yellow"
                    # my_speed = 2.5 if is_yellow else speeds['car']
                    # find the speed that will exhaust the green exactly
                    v = phase_speed(num_cars=counts[id],               # N
                    duration=duration,                # T
                    direction=direction)              # to pick correct car_le

                    print(f"    ==> [ADD] Spawning {cars_now} car(s) for {id} (After 1 phase, because it was current before recommended)")
                    if direction in ['down', 'up']:
                        for _ in range(cars_now):
                            Vehicle(0, dir_index, direction, speed=v)
                    else:
                        for lane in range(noOfLanes):
                            cars_per_lane = cars_now // noOfLanes
                            extra = cars_now % noOfLanes
                            for _ in range(cars_per_lane + (1 if lane < extra else 0)):
                                Vehicle(lane, dir_index, direction, speed=v)
                    last_manual_added_count[id] = cars_now
                    max_seen_cars[id] = counts[id]

                # -- الحالة 2: بعد فيزين من آخر مرة كان recommended (أول مرة فقط) --
                elif last_phase is not None and diff_idx == 2:
                    cars_now = counts[id]
                    direction = ID_TO_DIRECTION[id]
                    dir_index = ID_TO_DIRECTION_INDEX[id]
                    is_yellow = all_states[id] == "yellow"
                    # my_speed = 2.5 if is_yellow else speeds['car']
                    my_speed = phase_speed(num_cars=cars_now,               # N
                                           duration=duration,                # T
                                           direction=direction)

                    print(f"    ==> [ADD] Spawning {cars_now} car(s) for {id} (After 2 phases from last recommended)")
                    if direction in ['down', 'up']:
                        for _ in range(cars_now):
                            Vehicle(0, dir_index, direction, speed=v)
                    else:
                        for lane in range(noOfLanes):
                            cars_per_lane = cars_now // noOfLanes
                            extra = cars_now % noOfLanes
                            for _ in range(cars_per_lane + (1 if lane < extra else 0)):
                                Vehicle(lane, dir_index, direction, speed=v)
                    last_manual_added_count[id] = cars_now
                    max_seen_cars[id] = counts[id]

                # -- الحالة 3-أ: مراقبة مستمرة بعد أول إضافة يدوية --
                elif last_manual_added_count[id] is not None and counts[id] > last_manual_added_count[id]:
                    cars_to_add = counts[id] - last_manual_added_count[id]
                    direction = ID_TO_DIRECTION[id]
                    dir_index = ID_TO_DIRECTION_INDEX[id]
                    is_yellow = all_states[id] == "yellow"
                    # my_speed = 2.5 if is_yellow else speeds['car']
                    v = phase_speed(num_cars=cars_to_add,               # N
                                             duration=duration,                # T
                                                direction=direction)              # to pick correct car_le

                    print(f"    ==> [ADD] Spawning {cars_to_add} NEW car(s) for {id} (Continuous monitoring after key phase)")
                    if direction in ['down', 'up']:
                        for _ in range(cars_to_add):
                            Vehicle(0, dir_index, direction, speed=v)
                    else:
                        for lane in range(noOfLanes):
                            cars_per_lane = cars_to_add // noOfLanes
                            extra = cars_to_add % noOfLanes
                            for _ in range(cars_per_lane + (1 if lane < extra else 0)):
                                Vehicle(lane, dir_index, direction, speed=v)
                    last_manual_added_count[id] = counts[id]
                    max_seen_cars[id] = counts[id]

                # -- الحالة 3-ب: زيادة أولى قبل أي إضافة يدوية --
                elif last_manual_added_count[id] is None and counts[id] > max_seen_cars[id] \
                        and id != recommended:  # avoid double-spawning when it’s about to be handled below
                    cars_to_add = counts[id] - max_seen_cars[id]
                    direction = ID_TO_DIRECTION[id]
                    dir_index = ID_TO_DIRECTION_INDEX[id]
                    is_yellow = all_states[id] == "yellow"
                    # my_speed = 2.5 if is_yellow else speeds['car']
                    v = phase_speed(num_cars=cars_to_add,               # N
                                           duration=duration,                # T
                                           direction=direction)

                    print(f"    ==> [ADD] Spawning {cars_to_add} NEW car(s) for {id} "
                          "(First growth before any manual add)")
                    if direction in ['down', 'up']:
                        for _ in range(cars_to_add):
                            Vehicle(0, dir_index, direction, speed=v)
                    else:
                        for lane in range(noOfLanes):
                            cars_per_lane = cars_to_add // noOfLanes
                            extra = cars_to_add % noOfLanes
                            for _ in range(cars_per_lane + (1 if lane < extra else 0)):
                                Vehicle(lane, dir_index, direction, speed=v)

                    last_manual_added_count[id] = counts[id]   # start tracking from now
                    max_seen_cars[id] = counts[id]

            # If there is a new recommended phase in the current phase:
            if recommended:
                direction = ID_TO_DIRECTION[recommended]
                dir_index = ID_TO_DIRECTION_INDEX[recommended]
                num_cars_now = counts[recommended]
                previous_max = max_seen_cars[recommended]
                cars_to_spawn = max(0, num_cars_now - previous_max)

                is_yellow = all_states[recommended] == "yellow"
                my_speed = 2.5 if is_yellow else speeds['car']

                print(f"  [RECOMMENDED] {recommended} at idx={idx} | cars_to_spawn: {cars_to_spawn}")
                if cars_to_spawn > 0:
                    print(f"    ==> [ADD] Spawning {cars_to_spawn} car(s) for {recommended} (Recommended now)")
                    if direction in ['down', 'up']:
                        for _ in range(cars_to_spawn):
                            Vehicle(0, dir_index, direction, speed=my_speed)
                    else:
                        for lane in range(noOfLanes):
                            cars_per_lane = cars_to_spawn // noOfLanes
                            extra = cars_to_spawn % noOfLanes
                            for _ in range(cars_per_lane + (1 if lane < extra else 0)):
                                Vehicle(lane, dir_index, direction, speed=my_speed)
                last_recommended_phase[recommended] = idx
                last_manual_added_count[recommended] = None

            # Update max seen cars for each ID
            for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
                if counts[id] > max_seen_cars[id]:
                    max_seen_cars[id] = counts[id]

        # ---- Traffic-signal handling ----
        if recommended and all_states[recommended] == "yellow":
            for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
                i = ID_TO_DIRECTION_INDEX[id]
                if id == recommended:
                    signals[i].yellow = 2.5
                    signals[i].green = 0
                    signals[i].red = 0
                    green_signal_timer[id] = 0
                else:
                    signals[i].yellow = 0
                    signals[i].green = 0
                    signals[i].red = 3
                    green_signal_timer[id] = 0
            phase_start = time.time()
            while time.time() - phase_start < 2.5:
                time.sleep(0.1)
                timeElapsed += 0.1

            for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
                i = ID_TO_DIRECTION_INDEX[id]
                if id == recommended:
                    signals[i].yellow = 0
                    signals[i].green = duration
                    signals[i].red = 0
                    green_signal_timer[id] = duration
                    current_green_id = id
                    current_green_phase_end = time.time() + duration
                    live_phase_cross_count[id] = 0
                else:
                    signals[i].yellow = 0
                    signals[i].green = 0
                    signals[i].red = duration
                    green_signal_timer[id] = 0
            phase_start = time.time()
            while time.time() - phase_start < duration:
                time.sleep(0.1)
                timeElapsed += 0.1

            for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
                i = ID_TO_DIRECTION_INDEX[id]
                if id == recommended:
                    signals[i].yellow = 2.5
                    signals[i].green = 0
                    signals[i].red = 0
                else:
                    signals[i].yellow = 0
                    signals[i].green = 0
                    signals[i].red = 3
            phase_start = time.time()
            while time.time() - phase_start < 2.5:
                time.sleep(0.1)
                timeElapsed += 0.1
            continue

        green_id = None
        for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
            i = ID_TO_DIRECTION_INDEX[id]
            state = all_states[id]
            if state == "yellow":
                signals[i].yellow = duration
                signals[i].green = 0
                signals[i].red = 0
                green_signal_timer[id] = 0
            elif state == "red":
                signals[i].yellow = 0
                signals[i].green = 0
                signals[i].red = duration
                green_signal_timer[id] = 0
            elif state == "green":
                signals[i].yellow = 0
                signals[i].green = duration
                signals[i].red = 0
                green_signal_timer[id] = duration
                current_green_id = id
                current_green_phase_end = time.time() + duration
                live_phase_cross_count[id] = 0
                green_id = id

        phase_start = time.time()
        while time.time() - phase_start < duration:
            time.sleep(0.1)
            timeElapsed += 0.1

        if green_id is not None:
            for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
                i = ID_TO_DIRECTION_INDEX[id]
                if id == green_id:
                    signals[i].yellow = 2.5
                    signals[i].green = 0
                    signals[i].red = 0
                else:
                    signals[i].yellow = 0
                    signals[i].green = 0
                    signals[i].red = 3
            phase_start = time.time()
            while time.time() - phase_start < 2.5:
                time.sleep(0.1)
                timeElapsed += 0.1

    for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
        i = ID_TO_DIRECTION_INDEX[id]
        signals[i].red = 10
        signals[i].yellow = 0
        signals[i].green = 0
        green_signal_timer[id] = 0

    time.sleep(1)
    simulation_done = True


def initialize():
    for _ in range(4):
        signals.append(TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum))


class Main:
    thread1 = threading.Thread(name="initialization", target=initialize, args=())
    thread1.daemon = True
    thread1.start()

    # phases = fetch_phases_from_db(chunk_number=0)

    CHUNKS_TO_LOAD = [0, 1]
    phases = fetch_phases_for_chunks(CHUNKS_TO_LOAD)
    print(f"Loaded {len(phases)} phases from chunks {CHUNKS_TO_LOAD}")

    with open("retrieved.json", "w", encoding="utf-8") as f:
        json.dump(phases, f, ensure_ascii=False, indent=2)

    thread2 = threading.Thread(name="run_phases_from_json", target=run_phases_from_json, args=(phases,))
    thread2.daemon = True
    thread2.start()

    black = (0, 0, 0)
    white = (255, 255, 255)
    screenWidth = 1400
    screenHeight = 800
    screenSize = (screenWidth, screenHeight)
    background = pygame.transform.scale(
        pygame.image.load('images/mod_int.png'),
        (screenWidth, screenHeight)
    )

    screen = pygame.display.set_mode(screenSize)
    pygame.display.set_caption("SIMULATION")

    redSignal = pygame.image.load('images/signals/red.png')
    yellowSignal = pygame.image.load('images/signals/yellow.png')
    greenSignal = pygame.image.load('images/signals/green.png')
    font = pygame.font.Font(None, 30)

    # --- Video Setup ---
    fps = 30
    video_filename = "video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(video_filename, fourcc, fps, (screenWidth, screenHeight))
    clock = pygame.time.Clock()

    running = True
    show_complete_screen = False
    complete_screen_start_time = None
    global simulation_done

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if simulation_done and not show_complete_screen:
            # Display completion screen and start timer
            screen_end = pygame.display.set_mode((screenWidth, screenHeight))
            font_big = pygame.font.Font(None, 100)
            screen_end.fill((255, 255, 255))
            txt = font_big.render("Simulation Complete", True, (0, 0, 0), (255, 255, 255))
            rect = txt.get_rect(center=(screenWidth // 2, screenHeight // 2))
            screen_end.blit(txt, rect)
            pygame.display.update()
            show_complete_screen = True
            complete_screen_start_time = time.time()
            # record first frame
            arr = pygame.surfarray.array3d(screen_end)
            arr = arr.swapaxes(0, 1)
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            video_writer.write(arr)
        elif show_complete_screen:
            if time.time() - complete_screen_start_time <= 3:
                screen_end = pygame.display.set_mode((screenWidth, screenHeight))
                font_big = pygame.font.Font(None, 100)
                screen_end.fill((255, 255, 255))
                txt = font_big.render("Simulation Complete", True, (0, 0, 0), (255, 255, 255))
                rect = txt.get_rect(center=(screenWidth // 2, screenHeight // 2))
                screen_end.blit(txt, rect)
                pygame.display.update()
                arr = pygame.surfarray.array3d(screen_end)
                arr = arr.swapaxes(0, 1)
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                video_writer.write(arr)
                clock.tick(fps)
            else:
                running = False
        else:
            screen.blit(background, (0, 0))

            now = time.time()
            for id in ['ID-1', 'ID-2', 'ID-3', 'ID-4']:
                i = ID_TO_DIRECTION_INDEX[id]
                signal_obj = signals[i]

                if signal_obj.yellow > 0:
                    screen.blit(yellowSignal, signalCoods[id])
                elif signal_obj.green > 0:
                    screen.blit(greenSignal, signalCoods[id])
                else:
                    screen.blit(redSignal, signalCoods[id])

                if id == current_green_id and green_signal_timer[id] > 0:
                    remaining = int(current_green_phase_end - now)
                    if remaining < 0:
                        remaining = 0
                    green_signal_timer[id] = remaining
                    signal_text = remaining
                else:
                    signal_text = 0

                txt_img = font.render(str(signal_text), True, white, black)
                screen.blit(txt_img, signalTimerCoods[id])

                display_count = cumulative_cross_count[id]
                vehicleCountText = font.render(str(display_count), True, black, white)
                screen.blit(vehicleCountText, vehicleCountCoods[id])

            timeElapsedText = font.render(("Time Elapsed: " + str(int(timeElapsed))), True, black, white)
            screen.blit(timeElapsedText, (1100, 50))

            for vehicle in simulation:
                screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
                vehicle.move()
            pygame.display.update()

            # --- Save frame to video ---
            arr = pygame.surfarray.array3d(screen)
            arr = arr.swapaxes(0, 1)
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            video_writer.write(arr)
            clock.tick(fps)

    video_writer.release()
    pygame.quit()
    sys.exit()


Main()