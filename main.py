import logging
from livekit.agents import JobContext, WorkerOptions, cli, mcp
from livekit.agents.voice import Agent, AgentSession, room_io
from livekit.plugins import openai, silero, assemblyai
from custom.livekit.plugins import murfai
from livekit.plugins import noise_cancellation
from dotenv import load_dotenv
# LIVEKIT_ROOM=my-room python main.py console
load_dotenv()

#------
from livekit.agents.llm.tool_context import function_tool
from custom.livekit.plugins.json_fetching_agent.get_json import agent as json_agent
from custom.livekit.plugins.json_fetching_agent.update_json import add_user_record


@function_tool(
    name="get_user_info",
    description="Fetch user info by full name and DOB (YYYY-MM-DD)",
)
async def get_user_info(applicant_name: str, dob_yyyy_mm_dd: str) -> str:
    return json_agent(applicant_name, dob_yyyy_mm_dd)
#----

#------
@function_tool(
    name="add_user_info",
    description="Add a new applicant with name and DOB; status is always pending",
)
async def add_user_info(applicant_name: str, dob_yyyy_mm_dd: str) -> str:
    return add_user_record(applicant_name, dob_yyyy_mm_dd)
#----

logger = logging.getLogger("murf-voice-agent")
logger.setLevel(logging.INFO)


class MurfVoiceAgent(Agent):
    def __init__(self) -> None:

        murf_voice_id = "en-US-amara"  # voice
        murf_voice_style = "Conversational"  # style
        murf_locale = "en-US"  # multi-native locale

        super().__init__(
            instructions="""
                You are a friendly and helpful Agent
            """,
            stt=assemblyai.STT(),
            llm=openai.LLM(model="gpt-4o-2024-08-06"),
            # _tts=murfai.TTS(voice=murf_voice_id, style=murf_voice_style, locale=murf_locale)  # evaluate latency
            tts=openai.TTS(
                model="gpt-4o-mini-tts",
                voice="ash",
                instructions="Speak in a friendly and conversational tone.",
            ),
            vad=silero.VAD.load(min_speech_duration=0.1),
#------
            tools=[get_user_info, add_user_info],
#----
            mcp_servers=[
                mcp.MCPServerHTTP(
                    url="http://localhost:8000/sse",
                    timeout=10,
                    client_session_timeout_seconds=10,
                )
            ],
        )

    async def on_enter(self):
        await self.session.say(f"Hello! I'm Amara, How can I help you?")


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession()

    await session.start(
        agent=MurfVoiceAgent(),
        room_input_options=room_io.RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
