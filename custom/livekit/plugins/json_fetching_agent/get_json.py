import json
from pathlib import Path
from typing import Any, Dict, Optional


# Resolve the JSON file shipped alongside this module
JSON_PATH = Path(__file__).with_name("users_applications_with_id.json")


def _normalize_name(name: str) -> str:
    """Normalize human names for comparison (case- and extra-space-insensitive)."""
    return " ".join(name.strip().lower().split())


def _load_records() -> list[Dict[str, Any]]:
    with JSON_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_user(applicant_name: str, dob_yyyy_mm_dd: str) -> Optional[Dict[str, Any]]:
    """
    Lookup a user record by applicant name and DOB (YYYY-MM-DD) from the bundled JSON.

    Params:
        applicant_name: Full name as written in the data (case-insensitive).
        dob_yyyy_mm_dd: Date of birth as YYYY-MM-DD.

    Returns:
        The matching record dict if found, otherwise None.
    """
    target_name = _normalize_name(applicant_name)
    target_dob = dob_yyyy_mm_dd.strip()

    for record in _load_records():
        record_name = _normalize_name(str(record.get("user name", "")))
        record_dob = str(record.get("DOB", "")).strip()
        if record_name == target_name and record_dob == target_dob:
            return record
    return None


def agent(applicant_name: str, dob_yyyy_mm_dd: str) -> str:
    """
    Minimal agent interface: takes name and DOB, returns a succinct, LLM-friendly string.
    """
    record = find_user(applicant_name, dob_yyyy_mm_dd)
    if record is None:
        return (
            f"No record found for name='{applicant_name}' with DOB='{dob_yyyy_mm_dd}'."
        )

    # Format a compact response suitable for direct model consumption
    user = record.get("user name", "Unknown")
    dob = record.get("DOB", "Unknown")
    status = record.get("application status", "Unknown")
    description = record.get("description", "")
    app_id = record.get("application id", "")

    return (
        f"user: {user} | dob: {dob} | status: {status} | id: {app_id} | "
        f"notes: {description}"
    )


__all__ = [
    "agent",
    "find_user",
]


# if __name__ == "__main__":
#     # Simple CLI for quick manual testing
#     import sys

#     if len(sys.argv) != 3:
#         print("Usage: python get_json.py '<Full Name>' YYYY-MM-DD")
#         raise SystemExit(2)

#     name_arg, dob_arg = sys.argv[1], sys.argv[2]
#     print(agent(name_arg, dob_arg))


