# src/main.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import AgentSession, room_io
from livekit.plugins import noise_cancellation
from livekit import rtc
from src.agents.job_application import JobApplicationAgent
from src.agents.onboarding import OnboardingAgent

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load .env from repo root
ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(f"OPENAI_API_KEY missing. Expected in {ROOT / '.env'}")

async def entrypoint(ctx: JobContext):
    try:
        await ctx.connect()
        logger.info(f"Connected to room: {ctx.room.name}")
        
        # Log participant connection events
        @ctx.room.on("participant_connected")
        def on_participant_connected(participant):
            logger.info(f"Participant connected: {participant.identity}")
        
        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            logger.info(f"Participant disconnected: {participant.identity}")
        

        session = AgentSession()
        await session.start(
            agent=OnboardingAgent(chat_ctx=None, room=ctx.room),  
            room_input_options=room_io.RoomInputOptions(
                noise_cancellation=noise_cancellation.BVC()
            ),
            room=ctx.room,
        )
        
    except Exception as e:
        logger.error(f"Error in entrypoint: {e}")
        raise

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))