import logging
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession, room_io
from livekit.plugins import noise_cancellation
from src.agents.job_application import JobApplicationAgent
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger("murf-voice-agent")
logger.setLevel(logging.INFO)


# ------------------------
# Entry Point
# ------------------------
async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession()
    await session.start(
        agent=JobApplicationAgent(),
        room_input_options=room_io.RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
