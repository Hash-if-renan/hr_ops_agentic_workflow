import logging
import json
import uuid
from pathlib import Path
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession, room_io
from livekit.plugins import openai, silero, assemblyai
from livekit.plugins import noise_cancellation
from dotenv import load_dotenv
from src.tools.job_application_agent import (
    check_existing_application,
    create_job_application,
    query_knowledge_base,
    OPEN_JOBS,
)

load_dotenv()

logger = logging.getLogger("murf-voice-agent")
logger.setLevel(logging.INFO)


# ------------------------
# Agent Definition
# ------------------------
class JobApplicationAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions = f"""
                You are a friendly and professional HR assistant.

                Open Jobs:
                {', '.join([f"{job['job_id']}: {job['title']}" for job in OPEN_JOBS])}

                For ANY user doubts or questions related to jobs or the job application process:
                1. ALWAYS call the 'query_pdf_index' tool with the user's query.
                2. Use the response from the tool as authoritative context when answering the user.
                3. If the tool provides partial or unclear context, combine it with your HR knowledge to give a
                   clear, helpful, and professional answer.

                When a user wants to apply for a job, ask him whether he wants to apply from here or hell do it by himself, if he wants to apply from here:
                1. First, check if an application already exists for the combination of job_id, name, and date of birth
                   by calling the 'check_existing_application' tool.
                2. Ask the user job_id, name, and date of birth first before asking for other details.
                3. If an existing application is found, inform the user of their application ID and do not create a new one.
                4. If no application exists, call the 'create_job_application' tool with these arguments:
                   job_id, name, email, experience, skills, dob (in dd-mm-yyyy format).

                For all other non-job-related queries, provide clear and helpful answers in a professional tone.
            """,

            stt=assemblyai.STT(),
            llm=openai.LLM(model="gpt-4o-2024-08-06"),
            tts=openai.TTS(model="gpt-4o-mini-tts", voice="ash"),
            vad=silero.VAD.load(min_speech_duration=0.1),
            tools=[check_existing_application, create_job_application,query_knowledge_base],
        )
