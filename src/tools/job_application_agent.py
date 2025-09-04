# hr/tools/job_application_agent.py

import re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from agents.onboarding import OnboardingAgent
from livekit.agents import RunContext
from livekit.agents import function_tool  # decorator used by the agent to call tools


# ---------- Constants & Helpers ----------

APPS_DIR = Path("data/applications")


# Professional, friendly phone-call style status lines
_STATUS_LINES: Dict[str, str] = {
    "submitted": "We’ve received your application and will begin our review shortly. No action needed from you right now.",
    "in_review": "Your application is currently under review by our recruiting team.",
    "interview_scheduled": "Your interview has been scheduled. Let me know if you'd like any preparation guidance",
    "selected": "Congratulations—your application has been selected. Our team will reach out with next steps.",
    "rejected": "Unfortunately, we won’t be moving forward with this application, but we appreciate your time. Thank you for your interest!"
}


def _normalize_email_for_filename(email: str) -> str:
    """Match your filename convention: lowercase; non-alphanumerics -> '_'."""
    return re.sub(r"[^a-zA-Z0-9]", "_", (email or "").strip().lower())

def _humanize_status(raw: Optional[str]) -> str:
    return _STATUS_LINES.get((raw or "").strip().lower(), "We’re processing your application.")

def _humanize_updated_at(ts: Optional[str]) -> str:
    """Return a simple 'dd-mm-YYYY' string for speech; fall back to raw if parse fails."""
    if not ts:
        return ""
    try:
        # Accept '...Z' and no 'Z'
        dt = datetime.fromisoformat(str(ts).replace("Z", ""))
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return str(ts)


# ---------- Tool: list all apps for an email (login + fan-out) ----------

@function_tool(
    description="""
    Return all applications for a given email (case-insensitive).
    Matches files named: <application_id>_<normalized_email>.json in data/applications.

    Output:
    {
      "email": "<input email>",
      "name": "<first found full name or null>",
      "count": <int>,
      "applications": [
        {
          "application_id": "<id>",
          "job_title": "<title>",
          "status": "<submitted|in_review|interview_scheduled|selected|rejected>",
          "human_status": "<friendly sentence>",
          "updated_at": "<ISO8601>",
          "updated_at_human": "dd-mm-YYYY"
        }
      ]
    }
    """
)
async def list_applications_by_email(email: str) -> dict:
    """
    This doubles as the 'login fetch':
    - normalizes email per filename
    - returns a user-facing summary for 1-or-many apps
    """
    apps: List[Dict[str, Any]] = []
    inferred_name: Optional[str] = None

    email_norm = _normalize_email_for_filename(email)

    if APPS_DIR.exists():
        # Sort newest first by file mtime for nicer UX.
        files = sorted(
            APPS_DIR.glob(f"*_{email_norm}.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for fp in files:
            try:
                rec = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue

            status = (rec.get("status") or "submitted").strip().lower()
            human = _humanize_status(status)

            updated_at = rec.get("updated_at")
            if not updated_at:
                try:
                    updated_at = datetime.fromtimestamp(fp.stat().st_mtime).isoformat(timespec="seconds") + "Z"
                except Exception:
                    updated_at = None
            updated_at_human = _humanize_updated_at(updated_at)

            job_title = rec.get("job_title") or rec.get("title") or "Unknown role"

            nm = rec.get("name") or rec.get("full_name") or rec.get("applicant_name")
            if nm and not inferred_name:
                inferred_name = nm

            apps.append({
                "application_id": rec.get("application_id"),
                "job_title": job_title,
                "status": status,
                "human_status": human,
                "updated_at": updated_at,
                "updated_at_human": updated_at_human,
            })

    return {
        "email": email,
        "name": inferred_name,
        "count": len(apps),
        "applications": apps,
    }

@function_tool(
    description="""
    Given an application_id, return the application's current status in a human-friendly form.
    It looks for file: <application_id>_*.json in data/applications.

    Returns:
    {
      "found": true|false,
      "application": {
        "application_id": "...",
        "job_title": "...",
        "status": "submitted|in_review|interview_scheduled|selected|rejected",
        "human_status": "...",
        "updated_at": "YYYY-MM-DDTHH:MM:SSZ",
        "updated_at_human": "dd-mm-YYYY",
        "name": "Full Name or null",
        "email": "raw email",
        "phone": "raw phone or null",
        "response_timeframe": "natural text or null",
        "description": "free text or null"
      }
    }
    """
)
async def check_application_status(application_id: str) -> dict:
    # Locate the file by filename pattern first
    fp = next(iter(APPS_DIR.glob(f"{application_id}_*.json")), None)

    # Fallback: scan contents if filename didn’t match (handles manual naming)
    if fp is None:
        for cand in APPS_DIR.glob("*.json"):
            try:
                rec = json.loads(cand.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(rec.get("application_id", "")).strip().lower() == application_id.strip().lower():
                fp = cand
                break

    if fp is None or not fp.exists():
        return {"found": False, "application": None}

    # Read and shape the record
    try:
        rec = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {"found": False, "application": None}

    status = (rec.get("status") or "submitted").strip().lower()
    human = _humanize_status(status)

    updated_at = rec.get("updated_at")
    if not updated_at:
        try:
            updated_at = datetime.fromtimestamp(fp.stat().st_mtime).isoformat(timespec="seconds") + "Z"
        except Exception:
            updated_at = None
    updated_at_human = _humanize_updated_at(updated_at)

    job_title = rec.get("job_title") or rec.get("title") or "Unknown role"

    return {
        "found": True,
        "application": {
            "application_id": rec.get("application_id"),
            "job_title": job_title,
            "status": status,
            "human_status": human,
            "updated_at": updated_at,
            "updated_at_human": updated_at_human,
            "name": rec.get("name"),
            "email": rec.get("email"),
            "phone": rec.get("phone"),
            "response_timeframe": rec.get("response_timeframe"),
            "description": rec.get("description"),
        }
    }


@function_tool(
    description="""
    Interpret a user's selection among multiple applications and return the chosen application.
    The user can reply with a number (as listed) or a job title (full or partial).

    Inputs:
      - email (str): The email used to fetch the applications.
      - choice (str): The user's reply, e.g., "2" or "Backend Engineer".

    Behavior:
      - Loads apps for the given email from files named <application_id>_<normalized_email>.json
      - If 'choice' is a number within range, selects that index (1-based)
      - Otherwise, matches by job title (case-insensitive), supporting exact, prefix, and substring matches

    Returns:
    {
      "matched": true|false,
      "ambiguous": true|false,
      "selection": { "index": <1-based>, "application_id": "...", "job_title": "..." } | null,
      "options": [ { "index": <1-based>, "application_id": "...", "job_title": "..." }, ... ]  // present when ambiguous or not matched
    }
    """
)
async def select_application_by_choice(email: str, choice: str) -> dict:
    email_norm = _normalize_email_for_filename(email)
    files = sorted(
        APPS_DIR.glob(f"*_{email_norm}.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Build the in-memory list (titles only for speech, but keep IDs)
    apps = []
    for fp in files:
        try:
            rec = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        apps.append({
            "application_id": rec.get("application_id"),
            "job_title": rec.get("job_title") or rec.get("title") or "Unknown role",
        })

    if not apps:
        return {"matched": False, "ambiguous": False, "selection": None, "options": []}

    # 1) Numeric selection (1-based)
    choice_str = (choice or "").strip()
    if choice_str.isdigit():
        idx = int(choice_str)
        if 1 <= idx <= len(apps):
            sel = apps[idx - 1]
            return {
                "matched": True,
                "ambiguous": False,
                "selection": {"index": idx, "application_id": sel["application_id"], "job_title": sel["job_title"]},
                "options": []
            }
        # fall through to text matching if out of range

    # 2) Title-based selection
    def _norm_text(s: str) -> str:
        return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()

    norm_choice = _norm_text(choice_str)
    if not norm_choice:
        return {"matched": False, "ambiguous": False, "selection": None, "options": [
            {"index": i+1, "application_id": a["application_id"], "job_title": a["job_title"]} for i, a in enumerate(apps)
        ]}

    exact, prefix, contains, token = [], [], [], []

    # Build normalized titles once
    norm_titles = [_norm_text(a["job_title"]) for a in apps]
    choice_tokens = set(norm_choice.split())

    for i, (a, t) in enumerate(zip(apps, norm_titles)):
        title_tokens = set(t.split())
        if t == norm_choice:
            exact.append(i)
        elif t.startswith(norm_choice):
            prefix.append(i)
        elif norm_choice in t:
            contains.append(i)
        elif choice_tokens and choice_tokens.issubset(title_tokens):
            token.append(i)

    def pick(indices):
        if not indices:
            return None
        if len(indices) == 1:
            i = indices[0]
            return {
                "matched": True,
                "ambiguous": False,
                "selection": {"index": i+1, "application_id": apps[i]["application_id"], "job_title": apps[i]["job_title"]},
                "options": []
            }
        # ambiguous: return compact options
        opts = [{"index": i+1, "application_id": apps[i]["application_id"], "job_title": apps[i]["job_title"]} for i in indices][:5]
        return {"matched": False, "ambiguous": True, "selection": None, "options": opts}

    # Preference order: exact > prefix > contains > token
    for bucket in (exact, prefix, contains, token):
        res = pick(bucket)
        if res:
            return res

    # No match: return all options so Eve can re-ask politely
    return {
        "matched": False,
        "ambiguous": False,
        "selection": None,
        "options": [{"index": i+1, "application_id": a["application_id"], "job_title": a["job_title"]}
                    for i, a in enumerate(apps)]
    }

# ---------- Tool: query the FAQ knowledge base (RAG) ----------

@function_tool(
    description="""
    Answer general HR questions from the internal FAQ knowledge base (RAG).
    Use this for policy, onboarding, benefits, leave, documents, etc.
    Returns a concise answer plus supporting snippets for transparency.
    """
)
async def query_knowledge_base(question: str, top_k: int = 4) -> dict:
    """
    Thin wrapper over your existing retriever. It supports two setups:

    1) Function style:
         from src.utils.retriever import query as rag_query
         texts = rag_query(question, top_k=top_k)

    2) Class style:
         from src.utils.retriever import Retriever
         retriever = Retriever(index_dir="storage/faq_index")
         texts = retriever.query(question, top_k=top_k)

    It normalizes outputs into:
      {
        "answer": "<concise stitched text>",
        "snippets": [{"text": "...", "source": "<file or url or page ref>"}]
      }
    """
    # Lazy import so the file loads even if retriever deps aren't ready
    retriever_mode = None
    rag_query = None
    retriever = None

    try:
        # prefer function-style if available
        from src.utils.retriever import query as _q  # type: ignore
        rag_query = _q
        retriever_mode = "func"
    except Exception:
        try:
            from src.utils.retriever import Retriever  # type: ignore
            retriever = Retriever(index_dir="storage/faq_index")
            retriever_mode = "class"
        except Exception as e:
            return {
                "answer": "Sorry, I can't access the knowledge base right now.",
                "snippets": [],
                "error": f"retriever import failed: {e.__class__.__name__}"
            }

    # Run the search
    try:
        if retriever_mode == "func":
            results = rag_query(question, top_k=top_k)  # could be str or list-like
        else:
            results = retriever.query(question, top_k=top_k)
    except Exception as e:
        return {
            "answer": "Sorry, I had trouble searching the knowledge base.",
            "snippets": [],
            "error": f"retriever query failed: {e.__class__.__name__}"
        }

    # Normalize to a list of snippet dicts
    snippets = []
    if isinstance(results, str):
        # Some implementations return a single stitched string
        snippets = [{"text": results, "source": None}]
    elif isinstance(results, list):
        # Expect list of strings or dicts
        for item in results[: top_k or 4]:
            if isinstance(item, str):
                snippets.append({"text": item, "source": None})
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("chunk") or ""
                src = (
                    item.get("source")
                    or item.get("file")
                    or item.get("doc")
                    or item.get("metadata", {}).get("source")
                    or item.get("metadata", {}).get("file_name")
                )
                snippets.append({"text": text, "source": src})
    else:
        # Unknown format; best effort
        snippets = [{"text": str(results), "source": None}]

    # Build a short, speakable answer by stitching first few snippets
    stitched = " ".join(s["text"].strip() for s in snippets if s.get("text"))[:800]
    stitched = stitched.strip() or "I couldn't find a clear answer in the knowledge base."

    return {
        "answer": stitched,
        "snippets": snippets
    }
@function_tool
async def handover_to_onboarding(context: RunContext[dict]):
        """Switch to the onboarding agent when user needs onboarding help."""
        onboarding_agent = OnboardingAgent(chat_ctx=context.session._chat_ctx)
        return onboarding_agent, "wait for a moment", 

#_____________________________________________________________________________________________#