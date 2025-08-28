# Using Murf Voice with LiveKit

This guide explains how to integrate **Murf AI** voices with **LiveKit** using a custom plugin.

## 1. Add Murf API key In Environment Variable 
Add MURFAI_API_KEY to environment variable along with other environment variable. (e.g. LIVEKIT_API_KEY)
```
MURFAI_API_KEY="your-api-key"
```

## 2. Add the Custom Plugin Package

Ensure the custom package is included in your Python project (similar to how it is shared with this sample project).

## 3. Use the Murf Plugin for voice agent

Import the `murfai` module from the custom LiveKit plugins and use it

```python
import logging
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession, room_io
from livekit.plugins import openai, silero, assemblyai
from custom.livekit.plugins import  murfai
from livekit.plugins import noise_cancellation

logger = logging.getLogger("murf-voice-agent")
logger.setLevel(logging.INFO)


class MurfVoiceAgent(Agent):
    def __init__(self) -> None:

        murf_voice_id = "en-US-amara" # voice
        murf_voice_style = "Conversational" # style
        murf_locale = "en-US" # multi-native locale

        super().__init__(
            instructions="""
                You are a friendly and helpful Agent
            """,
            stt=assemblyai.STT(),
            llm=openai.LLM(model="gpt-4o-2024-08-06"), # evaluate latency
            tts=murfai.TTS(voice=murf_voice_id, style=murf_voice_style, locale=murf_locale),
            vad=silero.VAD.load(min_speech_duration=0.1)
        )

    async def on_enter(self):
        await self.session.say(
            f"Hello! I'm Amara, How can I help you?")

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession()

    await session.start(
        agent=MurfVoiceAgent(),
        room_input_options=room_io.RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
        room=ctx.room
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

## Options with Murf Plugin 
You can pass voice, style and multi-native locale to Murf TTS plugin and generate voices.

Visit [Murf Voice Options](https://murf.ai/api/docs/api-reference/text-to-speech/get-voices) to get all available voices.