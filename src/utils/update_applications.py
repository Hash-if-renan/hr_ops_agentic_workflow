import json
import random
from pathlib import Path


def update_applications():
    app_dir = Path("data/applications")
    if not app_dir.exists():
        print("⚠️ No applications found.")
        return

    status_options = [
        "Pending",
        "Under Review",
        "Interview Scheduled",
        "Selected",
        "Rejected",
    ]
    resume_reviewed_options = ["Not yet", "In Progress", "Completed"]
    timeframe_options = ["1 week", "2 weeks", "3 days", "Immediate"]
    rejection_reasons = [
        "Skills did not match requirements",
        "Insufficient experience",
        "Position filled",
        "Better suited candidates available",
    ]

    reapply_possible_options = ["Yes", "No"]

    # turn into a list so we don't deal with generators
    files = list(app_dir.glob("*.json"))

    for file in files:
        with open(file, "r") as f:
            app = json.load(f)

        new_status = random.choice(status_options)
        app["application_status"] = new_status

        if new_status == "Pending":
            app["resume_reviewed"] = "Not yet"
            app["response_timeframe"] = "2 weeks"
            app["rejection_reason"] = ""
            app["reapply_possible"] = ""
        elif new_status == "Under Review":
            app["resume_reviewed"] = random.choice(["In Progress", "Completed"])
            app["response_timeframe"] = random.choice(timeframe_options)
            app["rejection_reason"] = ""
            app["reapply_possible"] = ""
        elif new_status == "Interview Scheduled":
            app["resume_reviewed"] = "Completed"
            app["response_timeframe"] = "1 week"
            app["rejection_reason"] = ""
            app["reapply_possible"] = ""
        elif new_status == "Selected":
            app["resume_reviewed"] = "Completed"
            app["response_timeframe"] = "Immediate"
            app["rejection_reason"] = ""
            app["reapply_possible"] = ""
        elif new_status == "Rejected":
            app["resume_reviewed"] = "Completed"
            app["response_timeframe"] = "Closed"
            app["rejection_reason"] = random.choice(rejection_reasons)
            app["reapply_possible"] = random.choice(reapply_possible_options)

        with open(file, "w") as f:
            json.dump(app, f, indent=2)

