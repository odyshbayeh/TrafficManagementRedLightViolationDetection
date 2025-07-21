export interface RealWorldStat {
  id: string;
  cars_passed_in_real: number;
}

export interface BestFrame {
  id: string
  image: string  // base64 JPEG string
}

export interface Recommendation {
  current: string
  recommended: string
  duration_sec: number
  all_counts: Record<string, number>
  all_states: Record<string, string>
}

export interface TrafficRecord {
  id: string           // MongoDB _id as string
  chunk: number
  best_frames: BestFrame[]
  recommendations: Recommendation[]
  video_path: string
  real_world: RealWorldStat[]
}

export interface Violation {
  id:          string;   // MongoDB _id
  car_ID:      string;
  plate_text:  string;
  plate_detected: string; // base-64 JPEG
}