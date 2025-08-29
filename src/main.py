import logging
import asyncio
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import AgentSession, room_io
from livekit.plugins import noise_cancellation
from src.agents.job_application import JobApplicationAgent
from dotenv import load_dotenv

# import your updater function
from src.utils.update_applications import update_applications

load_dotenv()

logger = logging.getLogger("murf-voice-agent")
logger.setLevel(logging.INFO)


# ------------------------
# Background updater task
# ------------------------
async def run_updater(interval: int = 30):
    """Run the updater every `interval` seconds (default = 30s)."""
    while True:
        try:
            logger.info("🔄 Running application updater...")
            update_applications()  # your function
        except Exception as e:
            logger.error(f"Updater failed: {e}")
        await asyncio.sleep(interval)


# ------------------------
# Entry Point
# ------------------------
async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession()

    # Start updater in the background (defaults to 30s)
    asyncio.create_task(run_updater())

    await session.start(
        agent=JobApplicationAgent(),
        room_input_options=room_io.RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
