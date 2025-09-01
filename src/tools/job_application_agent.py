import logging
from typing import List
import json
import uuid
from pathlib import Path
from livekit.agents import JobContext, WorkerOptions, cli, function_tool
from livekit.agents.voice import Agent, AgentSession, room_io
from livekit.plugins import openai, silero, assemblyai
from livekit.plugins import noise_cancellation
from dotenv import load_dotenv
from src.utils.retriever import Retriever

# Initialize retriever (ensure index is already built or loaded)

@function_tool(
    description="""
    Query the PDF knowledge base that has been indexed into FAISS.

    Arguments:
    - query (str): The question to ask against the PDF documents.

    Returns:
    - A string context that agent can use while generating response.
    """
)
async def query_knowledge_base(query: str) -> str:
    """
    This tool searches the PDF knowledge base for job-related context.
    The response is used by the agent to provide job-related answers.
    """
    try:
        retriever = Retriever()

        response = retriever.query(query,top_k=5)
        print(f"Knowledge Base Response: {response}")
        return response  # LlamaIndex returns a Response object
    except Exception as e:
        return f"❌ Error querying index: {e}"


OPEN_JOBS = [
    {"job_id": "J001", "title": "Software Engineer"},
    {"job_id": "J002", "title": "Data Analyst"},
    {"job_id": "J003", "title": "Product Manager"},
]

@function_tool(
    description="""
    Checks the application status for a given applicant.

    Arguments:
    - application_id (str, optional): Unique application identifier. If provided, this will be used first.
    - email (str, optional): Applicant's email address. Used if application_id not provided.
    - job_id (str, optional): Job ID to narrow down results when email is provided.

    Returns:
    - A list of matching application JSONs (typically one, but could be multiple if the applicant has multiple applications).
    """
)
async def check_application_status(
    application_id: str | None = None,
    email: str | None = None,
    job_id: str | None = None,
) -> list[dict]:
    import re

    out_dir = Path("data/applications")
    if not out_dir.exists():
        return []

    results = []

    # Case 1: Lookup by application_id
    if application_id:
        for file in out_dir.glob(f"*_{application_id}.json"):
            with open(file, "r") as f:
                return [json.load(f)]

    # Case 2: Lookup by email + job_id
    if email and job_id:
        normalized_email = re.sub(r"[^a-zA-Z0-9]", "_", email.strip().lower())
        normalized_job_id = job_id.strip().lower()

        for file in out_dir.glob(f"{normalized_job_id}_{normalized_email}_*.json"):
            with open(file, "r") as f:
                results.append(json.load(f))

    return results



@function_tool(
    description="""
    Checks if a job application already exists for a given combination of job_id and email.

    Arguments:
    - job_id (str): The ID of the job to check.
    - email (str): Applicant's email address.

    Returns:
    - The existing application ID if found.
    - None if no existing application exists for that job_id and email.
    """
)
async def check_existing_application(job_id: str, email: str) -> str | None:
    import re

    normalized_job_id = job_id.strip().lower()
    normalized_email = re.sub(r"[^a-zA-Z0-9]", "_", email.strip().lower())

    out_dir = Path("data/applications")
    out_dir.mkdir(exist_ok=True)

    for file in out_dir.glob(f"{normalized_job_id}_{normalized_email}_*.json"):
        with open(file, "r") as f:
            existing_application = json.load(f)
        return existing_application["application_id"]

    return None


@function_tool(
    description="""
    Creates a new job application JSON for a given job. Allows the same person to apply for multiple jobs.

    Arguments:
    - job_id (str): The ID of the job to apply for.
    - name (str): Applicant's full name.
    - dob (str): Date of birth in dd-mm-yyyy format.
    - email (str): Applicant's email address.
    - skills (list[str]): List of applicant's skills.
    - experience (str): Description of applicant's experience.

    Returns:
    - A message confirming submission along with the application ID and filepath.
    """
)
async def create_job_application(
    job_id: str, name: str, dob: str, email: str, skills: list[str], experience: str
) -> str:
    from datetime import datetime
    import re

    # Validate job_id
    selected_job = next(
        (job for job in OPEN_JOBS if job["job_id"].lower() == job_id.lower()), None
    )
    if not selected_job:
        return f"❌ Invalid Job ID '{job_id}'. Application canceled."

    # Validate DOB
    try:
        dob_date = datetime.strptime(dob.strip(), "%d-%m-%Y")
        formatted_dob = dob_date.strftime("%d-%m-%Y")
    except ValueError:
        return "❌ Invalid DOB format. Please provide in dd-mm-yyyy format."

    normalized_job_id = selected_job["job_id"].lower()
    normalized_email = re.sub(r"[^a-zA-Z0-9]", "_", email.strip().lower())

    out_dir = Path("data/applications")
    out_dir.mkdir(exist_ok=True)

    # Prevent duplicate application for the same job_id + email
    existing_id = await check_existing_application(job_id, email)
    if existing_id:
        return f"⚠️ You have already applied for '{selected_job['title']}'. Your application ID is {existing_id}."

    # Generate unique application ID
    application_id = str(uuid.uuid4())

    application = {
        "application_id": application_id,
        "job_id": selected_job["job_id"],
        "job_title": selected_job["title"],
        "name": name,
        "dob": formatted_dob,
        "email": email,
        "skills": skills,
        "experience": experience,
        "application_status": "Pending",
        "resume_reviewed": "Not yet",
        "response_timeframe": "2 weeks",
        "rejection_reason": "",
        "reapply_possible": "",
    }

    # Filename format: jobid_email_appid.json
    filename = f"{normalized_job_id}_{normalized_email}_{application_id}.json"
    filepath = out_dir / filename

    with open(filepath, "w") as f:
        json.dump(application, f, indent=2)

    return f"✅ Application submitted for '{selected_job['title']}'! Your application ID is {application_id}. Saved at {filepath}"
