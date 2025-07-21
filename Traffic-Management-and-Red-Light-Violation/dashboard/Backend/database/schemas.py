def individual_data(rec):
    return {
        "id": str(rec["_id"]),
        "chunk": rec["chunk"],
        "best_frames": rec["best_frames"],
        "recommendations": rec["recommendations"],
        "video_path": rec["video_path"],
        "real_world": rec.get("real_world", []),
    }

def all_data(cursor):
    return [ individual_data(r) for r in cursor ]

# Violation data extraction function
def violation_data(doc):
    return {
        "id"            : str(doc["_id"]),
        "car_ID"        : str(doc.get("car_ID", "")),
        "plate_text"    : doc.get("plate_text", ""),
        "plate_detected": doc.get("plate_detected"),
    }

def all_violations(cursor):
    return [violation_data(v) for v in cursor]