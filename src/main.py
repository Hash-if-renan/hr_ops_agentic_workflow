# src/main.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from livekit.plugins import openai 

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import AgentSession, room_io
from livekit.plugins import noise_cancellation
from livekit import rtc
from src.agents.job_application import JobApplicationAgent
from src.agents.onboarding import OnboardingAgent

# Configure detailed logging
# logging.basicConfig(
#     level=logging.WARN,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)
from livekit.plugins import silero, assemblyai, elevenlabs, murfai

# from src.agents.job_application import JobApplicationAgent
# from src.agents.onboarding import OnboardingAgent
from src.agents.router import RouterAgent

# Load .env from repo root
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(f"OPENAI_API_KEY missing. Expected in {ROOT / '.env'}")

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    llm = openai.LLM(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    session = AgentSession(llm=llm)
    await session.start(
        agent=RouterAgent(),
        room_input_options=room_io.RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
        room=ctx.room,
    )

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))