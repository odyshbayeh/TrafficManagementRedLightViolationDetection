from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from bson import ObjectId

class RealWorldStat(BaseModel):
    id: str
    cars_passed_in_real: int

class BestFrame(BaseModel):
    id: str
    image: Optional[str] = None

class Recommendation(BaseModel):
    current: str
    recommended: str
    duration_sec: int
    all_counts: Dict[str, int]
    all_states: Dict[str, str]

class Record(BaseModel):
    id: Optional[str] = Field(None, alias="_id")

    chunk: int
    best_frames: List[BestFrame]
    recommendations: List[Recommendation]
    video_path: str
    real_world: List[RealWorldStat]

class Violation(BaseModel):
    id            : Optional[str] = Field(None, alias="_id")
    car_ID        : str
    plate_text    : str
    plate_detected: Optional[str] = None     # base-64 JPEG

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}
        extra = "ignore"    # ignore extra fields in input data
