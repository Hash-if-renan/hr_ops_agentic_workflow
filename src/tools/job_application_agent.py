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

#------
@function_tool(
    description="""
    Checks the application status for a given applicant.

    Arguments:
    - application_id (str, optional): Unique application identifier. If provided, this will be used first.
    - name (str, optional): Applicant's full name. Required only if application_id is not provided.
    - dob (str, optional): Date of birth in dd-mm-yyyy format. Required only if application_id is not provided.

    Returns:
    - The full application JSON if found, otherwise None.
    """
)
async def check_application_status(
    application_id: str | None = None,
    name: str | None = None,
    dob: str | None = None,
) -> dict | None:
    from pathlib import Path
    import json
    from datetime import datetime

    out_dir = Path("data/applications")
    if not out_dir.exists():
        return None

    # Case 1: Lookup by application_id
    if application_id:
        for file in out_dir.glob(f"*_{application_id}.json"):
            with open(file, "r") as f:
                return json.load(f)

    # Case 2: Fallback to name + dob
    if not name or not dob:
        return None

    try:
        dob_date = datetime.strptime(dob.strip(), "%d-%m-%Y")
        formatted_dob = dob_date.strftime("%d-%m-%Y")
    except ValueError:
        return None

    normalized_name = name.strip().lower().replace(" ", "_")
    normalized_dob = formatted_dob.lower().replace("/", "-")

    for file in out_dir.glob(f"*_{normalized_name}_{normalized_dob}_*.json"):
        with open(file, "r") as f:
            return json.load(f)

    return None

@function_tool(
    description="""
    Checks if a job application already exists for a given combination of job_id, name, and dob.

    Arguments:
    - job_id (str): The ID of the job to check.
    - name (str): Applicant's full name.
    - dob (str): Date of birth in dd-mm-yyyy format.

    Returns:
    - The existing application ID if found.
    - None if no existing application exists.
    """
)
async def check_existing_application(job_id: str, name: str, dob: str) -> str | None:
    from pathlib import Path
    import json
    from datetime import datetime

    # Validate and format DOB
    try:
        dob_date = datetime.strptime(dob.strip(), "%d-%m-%Y")
        formatted_dob = dob_date.strftime("%d-%m-%Y")
    except ValueError:
        return "❌ Invalid DOB format. Please provide in dd-mm-yyyy format."

    normalized_job_id = job_id.strip().lower()
    normalized_name = name.strip().lower().replace(" ", "_")
    normalized_dob = formatted_dob.lower().replace("/", "-")

    out_dir = Path("data/applications")
    out_dir.mkdir(exist_ok=True)

    for file in out_dir.glob(
        f"{normalized_job_id}_{normalized_name}_{normalized_dob}_*.json"
    ):
        with open(file, "r") as f:
            existing_application = json.load(f)
        return existing_application["application_id"]

    return None


@function_tool(
    description="""
    Creates a new job application JSON for a given job. Assumes no existing application exists.

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
    from pathlib import Path
    import json, uuid

    # Validate job_id
    selected_job = next(
        (job for job in OPEN_JOBS if job["job_id"].lower() == job_id.lower()), None
    )
    if not selected_job:
        return f"❌ Invalid Job ID '{job_id}'. Application canceled."

    # Validate and format DOB
    try:
        dob_date = datetime.strptime(dob.strip(), "%d-%m-%Y")
        formatted_dob = dob_date.strftime("%d-%m-%Y")
    except ValueError:
        return "❌ Invalid DOB format. Please provide in dd-mm-yyyy format."

    normalized_job_id = selected_job["job_id"].lower()
    normalized_name = name.strip().lower().replace(" ", "_")
    normalized_dob = formatted_dob.lower().replace("/", "-")

    out_dir = Path("data/applications")
    out_dir.mkdir(exist_ok=True)

    # Generate unique application ID
    application_id = str(uuid.uuid4())

    # Build application JSON
    application = {
        "application_id": application_id,
        "job_id": selected_job["job_id"],
        "job_title": selected_job["title"],
        "name": name,
        "dob": formatted_dob,
        "email": email,
        "skills": skills,
        "experience": experience,
        # Additional placeholders
        "application_status": "Pending",
        "resume_reviewed": "Not yet",
        "response_timeframe": "2 weeks",
        "rejection_reason": "",
        "reapply_possible": "",
    }

    # Create filename including application ID
    filename = (
        f"{normalized_job_id}_{normalized_name}_{normalized_dob}_{application_id}.json"
    )
    filepath = out_dir / filename

    # Save JSON
    with open(filepath, "w") as f:
        json.dump(application, f, indent=2)

    return f"✅ Application submitted for '{selected_job['title']}'! Your application ID is {application_id}. Saved at {filepath}"
