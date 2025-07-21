from typing import List
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from configurations import collection, violations_coll
from database.schemas import *
from database.models import Record, Violation
from bson import ObjectId

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

# @router.get("/", response_model=List[Record])
# async def get_all_records():
#     records = collection.find()
#     return all_data(records)

# ────────── RECORD LIST (just the chunk numbers) ────────────────────
@router.get("/chunks", response_model=List[int])
async def list_chunks():
    docs   = collection.find({}, {"chunk": 1, "_id": 0})
    chunks = sorted({d["chunk"] for d in docs})
    return chunks

# ────────── VIOLATIONS ENDPOINTS  (STATIC PATHS FIRST!) ──────────────
@router.get("/violations", response_model=List[Violation])
async def get_violations():
    """Return *all* violation documents."""
    return all_violations(violations_coll.find())

@router.get("/violations/{car_id}", response_model=List[Violation])
async def get_violations_by_car(car_id: str):
    """All violations for the given `car_ID`."""
    docs = list(violations_coll.find({"car_ID": car_id}))
    if not docs:
        raise HTTPException(404, f"No violations found for car {car_id}")
    return all_violations(docs)


# ────────── SINGLE CHUNK RECORD  (DYNAMIC ROUTE LAST!) ───────────────
@router.get("/{chunk}", response_model=Record)
async def get_record(chunk: int):
    rec = collection.find_one({"chunk": chunk})
    if not rec:
        raise HTTPException(404, f"Chunk {chunk} not found")
    return individual_data(rec)

# include everything
app.include_router(router)
