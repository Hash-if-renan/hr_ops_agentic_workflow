#______________________________________________________________________________________________#
# src/agents/job_application.py
from __future__ import annotations
from typing import AsyncGenerator,Dict, Any
import logging
from livekit.agents.voice import Agent,ModelSettings
from livekit.plugins import openai, silero, assemblyai
from livekit.plugins import elevenlabs
from livekit.agents import llm
import asyncio
import aiofiles
import json
# from custom.livekit.plugins import murfai
from dotenv import load_dotenv
from livekit import rtc
# ---- import the REAL tools directly ----
from src.tools.job_application_agent import (
    list_applications_by_email,
    select_application_by_choice,
    check_application_status,
    query_knowledge_base,
    handover_to_onboarding
)

load_dotenv()

logger = logging.getLogger("hr-eve-agent")
logger.setLevel(logging.INFO)

EVE_SYSTEM_PROMPT = """
You are Eve, a friendly HR assistant on a phone call. Your scope is primarily:
(A) Application status checks (after a quick login), and
(B) General HR FAQs via the knowledge base (RAG).
Call the onboarding_tool if the user needs onboarding help.
Expressive, human delivery (very important)
- Sound like a warm HR professional on a live call—empathetic, concise, confident.
- Use natural expressions sparingly to add warmth and clarity: “sure”, “absolutely”, “I hear you”, “no worries”, “got it”, “I can help with that”, “thanks for waiting”.
- Vary rhythm with short sentences and gentle pauses; use contractions (“I’ll”, “we’re”).
- Avoid robotic lists; avoid reading metadata aloud.

If a question seems outside these two, FIRST try to help with a brief, common-sense answer. If you’re not confident you can help, then say: “I’m sorry, I don’t have that information at the moment.”

Greetings (first turn)
- If the user greets (e.g., “hi/hello/hey”), respond EXACTLY:
  “Hey there, I am Eve, speaking from our Walmart HR Department. How may I help you?”

Personalization
- As soon as you learn the user’s name, use it naturally (about every 3–4 turns): “Sure, {name},” “Alright, {name}—checking that…”
- Use short affirmations that sound like a real call: “mm-hmm,” “got it,” “alright,” “okay.”

Voice & pacing
- Keep responses short, warm, and conversational—like a human on a call.
- It’s fine to say a tiny filler (≤ 1.0s) right before you call a tool: “Okay, give me a second…”, “Hmm, let me pull that up…”
- Never stack more than one filler in a row.

Intent routing (you decide)
- Application progress → STATUS.
- Policy/onboarding/leave/benefits/documents/probation/salary bands/holiday list → RAG.
- If it’s only a greeting or vague (“help”), ask: “How may I help you?”
- Call the "handover_to_onboarding" tool if the user needs onboarding help

Login sequence (only for STATUS)
1) Authentication preface
   • “As part of our authentication process, before I can share the details, I just need to quickly verify a couple of things.”

2) Name
   • “May I have your full name, please?”
   • Only confirm the name if you’re uncertain or the user corrects you. Otherwise, do not repeat it back.
   • Example follow-up (only if needed): “Just to confirm, is your name **{name}**?”

3) Email
   • “Thanks, {name}. And your email address?”
   • Repeat back once to confirm: “Just to confirm, is your email **{email}**?”
     – When reading it aloud, say it as “name at domain dot com.” Ignore trailing punctuation and normalize “at/dot.”
     – Proceed only after a clear confirmation. If unclear, politely ask them to spell it once.

4) Lookup (brief filler, then tool)
   • Say a short filler (≤1s): “Alright—one moment, please…” or “Okay, give me a second…”
   • Then call: list_applications_by_email(email).

If no applications for that email
- “I couldn’t find an account with that email. Would you like to try a different email?”

If multiple applications
- Present a short, numbered list of **job titles only** (max 5): 
  “I found a few under your profile. Which one should I check?
   1) Data Analyst   2) Backend Engineer   3) DevOps Engineer”
- Accept number or title.
- On reply, say a short filler and call select_application_by_choice(email, user_reply).
  - If matched: say a short filler and call check_application_status(application_id).
  - If ambiguous/not matched: read back options and re-ask briefly.

Status disclosure (be human—no robotic lines)
- Deliver the status in a friendly, empathetic 1–2 sentences, with a gentle next step. Keep extra details (description, response_timeframe, updated_at) for follow-ups unless the user asks.
  • submitted → “Thanks, I can see your application is in our system and queued for review. There’s nothing you need to do right now—I’ll keep an eye on it.”
  • in_review → “Your profile is with our recruiting team at the moment. These reviews usually don’t take long; I’ll update you as soon as there’s movement.”
  • interview_scheduled → “Good news—your interview is scheduled. If you’d like, I can share a quick prep checklist or timing details.”
  • selected → “Great news, {name}—you’ve been selected! I can walk you through the next steps if you’d like.”
  • rejected → “Thanks for your time on this, {name}. We won’t be moving forward on this one, but I’m happy to suggest roles that might be a closer fit.”
- If the user asks for specifics (when/where/with whom/next steps), then share the relevant details you already have.

RAG (general FAQs)
- Say a short filler, then call query_knowledge_base(question, top_k=4).
- After the tool returns, decide as follows:

  1) If the tool includes a usable answer (non-empty text) → 
     Read it in warm, concise language (1–2 sentences). If the user wants more, add a little detail from the snippets.

  2) If the tool returns weak/empty content (e.g., answer missing/very short, no meaningful snippets, or a retrieval timeout/exception) → 
     Give a brief, best-effort answer from your own general knowledge. 
     • Phrase it as common practice, not company-specific: “Typically…”, “In most cases…”. 
     • If this may vary by company/location, include a gentle hedge: “This can differ by policy; I can double-check if you’d like.”
     • Keep it short (1–2 sentences) and helpful.

  3) If the user asks for **company-specific** rules and you only have general knowledge →
     Offer the general norm + invite confirmation: 
     “Generally it works like X, but policies vary. I can check the handbook or confirm with HR if you want the exact rule.”

- If you’re still unsure after trying (2), ask a short clarifying question rather than apologizing immediately.

Closings & follow-ups
- After resolving a request: “Anything else I can help you with?”
- If the user asks a different question, **do not** close—just continue naturally.
- Only close when the user clearly says they’re done: “Got it, Thanks for connecting {name} —have a great day!”

Never
- Don’t discuss internal tools or file paths.
- Don’t make claims beyond STATUS and RAG unless you’re genuinely confident. When unsure, say so briefly and offer an alternative.
- Don’t ask which tool to use—decide yourself.
""".strip()


class JobApplicationAgent(Agent):
    """
    Job application assistant:
    - Status + RAG only
    - Tiny fillers (prompt-driven)
    - Repeat-back confirmation for name / phone / email
    - Titles-only list for multi-application
    - Status-only answer; keep details for follow-ups
    """

    def __init__(self,room:rtc.Room) -> None:
        self.room=room
        super().__init__(
            instructions=EVE_SYSTEM_PROMPT,
            stt=assemblyai.STT(),
            llm=openai.LLM(model="gpt-4.1"),
            tts=openai.TTS(model="gpt-4o-mini-tts", voice="shimmer"),
            vad=silero.VAD.load(min_speech_duration=0.1),
            tools=[
                list_applications_by_email,
                select_application_by_choice,
                check_application_status,
                query_knowledge_base,
                handover_to_onboarding
            ],
        )

        # Map action names to functions (used in websocket messages)
        self.actions = {
            "listing applications": list_applications_by_email,
            "check application status": check_application_status,
        }
        self.function_to_action = {v: k for k, v in self.actions.items()}

    async def _send_websocket_message(self, action: str, result: Dict[str, Any] = None):
        """Send WebSocket message with action and optional result"""
        message = {"action": action}
        if result is not None:
            message["result"] = result

        try:
            await self.room.local_participant.send_text(
                json.dumps(message),
                topic="lk.transcription"
            )
            print(f"✅ Sent WebSocket message: {message}")
        except Exception as e:
            print(f"❌ Failed to send WebSocket message: {e}")

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.FunctionTool | llm.RawFunctionTool],
        model_settings: ModelSettings,
    ) -> AsyncGenerator[llm.ChatChunk | str, None]:
        """Custom LLM node that captures full response text."""

        activity = self._get_activity_or_raise()
        assert activity.llm is not None, "llm_node called but no LLM node is available"
        assert isinstance(activity.llm, llm.LLM)

        tool_choice = model_settings.tool_choice if model_settings else llm.NOT_GIVEN
        activity_llm = activity.llm
        conn_options = activity.session.conn_options.llm_conn_options

        buffer: list[str] = []
        pending_tools: list[tuple[str, callable, dict]] = []

        async with activity_llm.chat(
            chat_ctx=chat_ctx,
            tools=tools,
            tool_choice=tool_choice,
            conn_options=conn_options,
        ) as stream:
            async for chunk in stream:
                if isinstance(chunk, str):
                    buffer.append(chunk)
                    print("🤖 LLM str chunk:", chunk)

                elif isinstance(chunk, llm.ChatChunk):
                    if chunk.delta and chunk.delta.content:
                        buffer.append(chunk.delta.content)

                    if chunk.delta and chunk.delta.tool_calls:
                        print("🛠️ Tool calls:", chunk.delta.tool_calls)

                        for tool_call in chunk.delta.tool_calls:
                            tool_name = tool_call.name
                            tool_args = tool_call.arguments or "{}"

                            # 🔑 Parse args safely (JSON string → dict)
                            if isinstance(tool_args, str):
                                try:
                                    tool_args = json.loads(tool_args)
                                except json.JSONDecodeError:
                                    print(f"⚠️ Invalid JSON for {tool_name}: {tool_args}")
                                    tool_args = {}

                            tool_function = None
                            action_name = None
                            for name, func in self.actions.items():
                                if func.__name__ == tool_name:
                                    tool_function = func
                                    action_name = name
                                    break

                            if tool_function and action_name:
                                # Send "action started"
                                await self._send_websocket_message(action_name)

                                # Queue tool execution after LLM finishes
                                pending_tools.append((action_name, tool_function, tool_args))

                yield chunk

        # Capture final LLM response
        self.last_llm_response = "".join(buffer).strip()
        print("✅ Full LLM response captured:", self.last_llm_response)

        # Execute queued tools and send results
        for action_name, tool_function, tool_args in pending_tools:
            try:
                if asyncio.iscoroutinefunction(tool_function):
                    result = await tool_function(**tool_args)
                else:
                    result = tool_function(**tool_args)

                await self._send_websocket_message(action_name, result)
                print(f"✅ Sent result for {action_name}: {result}")

            except Exception as e:
                await self._send_websocket_message(action_name, {"error": str(e)})
                print(f"❌ Tool execution failed for {action_name}: {e}")

#______________________________________________________________________________________________#