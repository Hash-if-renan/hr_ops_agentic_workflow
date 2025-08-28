import json
import uuid
from pathlib import Path
from typing import Any, Dict


JSON_PATH = Path(__file__).with_name("users_applications_with_id.json")


def add_user_record(applicant_name: str, dob_yyyy_mm_dd: str) -> str:
    """
    Append a new applicant record to the JSON file if an exact match doesn't already exist.

    The new record uses:
      - application status: "pending"
      - description: "your application is under careful consideration"

    Returns a short confirmation string.
    """
    if not applicant_name or not dob_yyyy_mm_dd:
        return "name and dob are required"

    # Load existing records
    try:
        with JSON_PATH.open("r", encoding="utf-8") as f:
            data: list[Dict[str, Any]] = json.load(f)
    except FileNotFoundError:
        data = []

    norm_name = " ".join(applicant_name.strip().split())
    norm_dob = dob_yyyy_mm_dd.strip()

    # Check for duplicate (same name and DOB)
    for rec in data:
        if str(rec.get("user name", "")).strip().lower() == norm_name.lower() and str(
            rec.get("DOB", "")
        ).strip() == norm_dob:
            return "record already exists"

    new_rec: Dict[str, Any] = {
        "user name": norm_name,
        "DOB": norm_dob,
        "application status": "pending",
        "description": "your application is under careful consideration",
        "application id": str(uuid.uuid4()),
    }

    data.append(new_rec)

    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return (
        #------
        f"added user: {norm_name}, application id: {new_rec['application id']}"
        #----
    )


__all__ = ["add_user_record"]


