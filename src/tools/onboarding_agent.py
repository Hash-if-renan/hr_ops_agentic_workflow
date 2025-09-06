import os, re, json
from datetime import datetime
from typing import Dict, Any, Optional, List
from livekit.agents import function_tool
from pathlib import Path
from livekit.agents import RunContext
# from src.agents.job_application import JobApplicationAgent


OFFERS_DIR = Path("data/offers")

def _normalize_for_filename(name: str, email: str) -> str:
    safe_name = re.sub(r'[^a-z0-9]+', '_', name.lower())
    safe_email = re.sub(r'[^a-z0-9@]+', '_', email.lower())
    print(safe_email)
    return f"{safe_name}_{safe_email}.json"

def _load_candidate_record(name: str, email: str) -> Optional[Dict[str, Any]]:
    fn = _normalize_for_filename(name, email)
    print("Loading candidate record:", fn)
    fp = OFFERS_DIR / fn
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return None



@function_tool(
    description="Check the offer status and ETA for sending the offer letter."
)
async def check_offer_status(name: str, email: str) -> dict:
    print("Checking offer status for:", name, email)
    rec = _load_candidate_record(name, email)
    print("Record loaded:", rec)
    if not rec:
        result = {"error": "No record found"}
    else:
        offer = rec.get("offer", {})
        result = {"status": offer.get("status"), "eta_hours": offer.get("eta_hours")}
    
    # Save result to shared file
    return result



@function_tool(
    description="Get the high-level summary of the candidate’s offer (title, level, base, variable, benefits, location, tentative joining)."
)
async def get_offer_summary(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        return {"error": "No record found"}
    return rec.get("offer", {}).get("summary", {})



@function_tool(
    description="Confirm the candidate’s tentative joining date."
)
async def confirm_joining_date(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        return {"error": "No record found"}
    
    return {"joining_date": rec.get("joining", {}).get("date")}


@function_tool(
    description="Get the reporting manager details (name, title, email, calendar link)."
)
async def get_reporting_manager(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        result = {"error": "No record found"}
    else:
        result = rec.get("reporting", {})
    
    # Save result to shared file
    return result



@function_tool(
    description="Return the list of documents the candidate must upload for pre-boarding."
)
async def get_documents_checklist(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        result = {"error": "No record found"}
    else:
        result = {"documents": rec.get("preboarding", {}).get("documents", [])}
    
    return result


@function_tool(
    description="Return the list of tasks the candidate must complete before joining."
)
async def get_preboarding_tasks(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        return {"error": "No record found"}
    return {"tasks": rec.get("preboarding", {}).get("tasks", [])}
@function_tool(
    description="Return the candidate's background verification (BGV) status, expected completion days, and remarks."
)
async def get_background_verification_status(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        return {"error": "No record found"}

    bgv = rec.get("bgv", {})
    return {
        "status": bgv.get("status", "unknown"),
        "expected_days": bgv.get("expected_days", ""),
        "remarks": bgv.get("remarks", "")
    }



@function_tool(
    description="""
    Mark candidate’s joining deferral request with a new date.
    """
)
async def mark_deferral(name: str, email: str, new_date: str) -> dict:
    """
    new_date: must be in format YYYY-MM-DD
    """
    fn = _normalize_for_filename(name=name,email=email)
    fp = OFFERS_DIR / fn

    if not fp.exists():
        return {"error": "Offer record not found"}

    data = json.loads(fp.read_text(encoding="utf-8"))
    data.setdefault("escalations", {})
    data["escalations"]["joining_deferral"] = {
        "requested": True,
        "new_date": new_date
    }

    fp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"success": True, "joining_deferral": new_date}

@function_tool(
    description="""
    Schedule or mark the 1:1 intro call with the reporting manager.
    """
)
async def schedule_intro_call(name: str, email: str, date: str) -> dict:
    """
    date: must be in format YYYY-MM-DDTHH:MM (ISO8601)
    """
    fn = _normalize_for_filename(name=name,email=email)

    fp = OFFERS_DIR / fn

    if not fp.exists():
        return {"error": "Offer record not found"}

    data = json.loads(fp.read_text(encoding="utf-8"))
    data.setdefault("reporting", {})
    data["reporting"]["intro_call_scheduled"] = True
    data["reporting"]["intro_call_date"] = date

    fp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"success": True, "intro_call_date": date}

@function_tool(
    description="""
    Update or add candidate’s preferred laptop shipping address.
    """
)
async def update_shipping_address(name: str, email: str, address: str) -> dict:
    # name_norm = _normalize_for_filename(name)
    # email_norm = _normalize_for_filename(email)
    fn = _normalize_for_filename(name=name,email=email)
    fp = OFFERS_DIR / fn

    if not fp.exists():
        return {"error": "Offer record not found"}

    data = json.loads(fp.read_text(encoding="utf-8"))
    data.setdefault("it_assets", {})
    data["it_assets"]["preferred_shipping_address"] = address

    fp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"success": True, "preferred_shipping_address": address}

# async def update_joining_date(name: str, email: str, new_date: str) -> dict:
#     """
#     new_date: must be in format YYYY-MM-DD
#     """
    
#     fn = _normalize_for_filename(name=name,email=email)
#     fp = OFFERS_DIR / fn
#     if not fp.exists():
#         return {"error": "Offer record not found"}

#     data = json.loads(fp.read_text(encoding="utf-8"))
#     data["offer"]["joining_date"] = new_date

#     fp.write_text(json.dumps(data, indent=2), encoding="utf-8")
#     return {"success": True, "joining_date": new_date}

@function_tool(
    description="""
    Fetch candidate's offer details from stored JSON.
    Only call this for offer letter received candidates.
    Input: name + email (asked only once in session).
    Matches file: data/offers/<normalized_name>_<normalized_email>.json

    Output: full candidate record (offer, reporting, documents, preboarding, IT, etc.)
    """
)
async def get_offer_details(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        result = {"error": "No record found"}
    else:
        result = {"offer_letter":rec.get("offer")}
    
    return result

@function_tool(
    description="""
    Log a negotiation request from the candidate.
    It appends the request into the 'negotiations' key inside their JSON record.
    If 'negotiations' does not exist, it creates a list.
    Returns a friendly confirmation message (not the raw JSON).
    """
)
async def log_negotiation(name: str, email: str, request: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        return {"error": "No record found"}

    # Ensure negotiations list exists
    if "negotiations" not in rec:
        rec["negotiations"] = []

    rec["negotiations"].append({
        "request": request,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

    # Save back to file
    fn = _normalize_for_filename(name, email)
    fp = OFFERS_DIR / fn
    fp.write_text(json.dumps(rec, indent=2), encoding="utf-8")

    return {
        "message": "Your request for negotiation has been shared with the compensation team, thank you."
    }

@function_tool(
    description="""
    Email the candidate their required document checklist.
    This will send a secure email to the candidate’s registered email address with the list of documents.
    """
)
async def email_documents_checklist(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        return {"error": "No record found"}

    documents = rec.get("preboarding", {}).get("documents", [])
    if not documents:
        return {"error": "No documents checklist found for this candidate"}

    # Simulate sending email (replace this with actual email service later)
    print(f"Sending documents checklist to {email}:\n- " + "\n- ".join(documents))

    return {
        "message": f"✅ I’ve just sent the document checklist to {email}. Please check your inbox (and spam folder just in case)."
    }

@function_tool(
    description="""
    Send a summary email of the current onboarding conversation to the candidate.
    The summary text must be provided by the calling agent (not fetched from JSON).
    """
)
async def send_onboarding_summary(name: str, email: str, conversation_summary: str) -> dict:
    subject = f"Onboarding Plan – {name}"
    email_body = f"""
    Hi {name},

    Here's a quick recap of our conversation today:

    {conversation_summary}

    Excited to have you onboard! 🎉

    Regards,  
    HR Team
    """

    print(f"Sending onboarding summary to {email}:\nSubject: {subject}\n\n{email_body}")
    result = {
        "message": f"✅ I've sent the conversation summary to {email}. Please check your inbox for '{subject}'"
    }
    
    return result

@function_tool(
    description="""
    Retrieve the candidate's Day-1 agenda (orientation and activities planned on the first day).
    """
)
async def get_day1_agenda(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        return {"error": "No record found"}

    day1_agenda = rec.get("it_assets", {}).get("day1_agenda", {})

    if not day1_agenda:
        return {"error": "No Day-1 agenda found for this candidate"}

    return {
        "day1_agenda": day1_agenda
    }

@function_tool(
    description="""
    Retrieve the candidate's IT asset provisioning details 
    (laptop shipping, email provisioning, VPN access, shipping address).
    """
)
async def get_it_assets(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        return {"error": "No record found"}

    it_assets = rec.get("it_assets", {})

    if not it_assets:
        return {"error": "No IT assets details found for this candidate"}

    return {
        "laptop_shipping": it_assets.get("laptop_shipping"),
        "email_provisioning": it_assets.get("email_provisioning"),
        "vpn_access": it_assets.get("vpn_access"),
        "preferred_shipping_address": it_assets.get("preferred_shipping_address"),
    }

@function_tool(
    description="""
    Retrieve the candidate's assigned work location (e.g., office campus, building, or remote model).
    """
)
async def get_work_location(name: str, email: str) -> dict:
    rec = _load_candidate_record(name, email)
    if not rec:
        return {"error": "No record found"}

    location = rec.get("candidate", {}).get("location")
    work_model = rec.get("candidate", {}).get("work_model")

    if not location and not work_model:
        return {"error": "No work location details found for this candidate"}

    return {
        "work_location": location,
        "work_model": work_model
    }

#______________________________________________________________________________________________________________#
#--------------------------------------------------------------------------------------------------------------#
#______________________________________________________________________________________________________________#


#______________________________________________________________________________________________________________#
#--------------------------------------------------------------------------------------------------------------#
#______________________________________________________________________________________________________________#
