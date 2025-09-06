# src/agents/router.py
from livekit.agents import Agent, function_tool, RunContext
from livekit import rtc
from src.agents.job_application import JobApplicationAgent
from src.agents.onboarding import OnboardingAgent
from livekit.plugins import assemblyai, elevenlabs,openai

ROUTER_INSTRUCTIONS = """
You are Eve, a friendly HR assistant on a phone call. Your role is to act like the first point of contact:
- Greet warmly and sound natural, like a human assistant. 
- Listen to the user, ask light clarifying questions if their request is vague.
- Once you understand their intent, transition smoothly without revealing you are transferring them.

Domains you cover:
- Onboarding: offer letter, CTC/benefits, joining date, pre-boarding, documents, BGV, reporting manager, location, workstation.
- Applications: application status, application ID, JR-xxx job ID, submission/in_review/interview/rejected/selected, resume needed to apply, etc.

Guidelines:
- Speak as if continuing the same conversation, not handing off. 
- Do not mention tools, agents, or routing. 
- Dont say anything specific during this process
- Then silently call the correct tool (`go_onboarding` or `go_applications`).

You are never supposed to answer detailed onboarding or application queries yourself. 
Your job is to make the transition feel seamless and human.
"""



class RouterAgent(Agent):
    def __init__(self,room:rtc.Room):
        self.room=room
        super().__init__(instructions=ROUTER_INSTRUCTIONS,
                         stt=assemblyai.STT(),
                        llm=openai.LLM(model="gpt-4.1"),
                         tts=elevenlabs.TTS(
                voice_id="wlmwDR77ptH6bKHZui0l",
                model="eleven_multilingual_v2",
            )

                         )

    @function_tool
    async def go_onboarding(self, context: RunContext[dict]):
        agent = context.session.current_agent
        # Generic, smooth transition
        return (
            "Sure, let me take care of that for you.",
            OnboardingAgent(room=agent.room, chat_ctx=context.session._chat_ctx),
        )

    @function_tool
    async def go_applications(self, context: RunContext[dict]):
        agent = context.session.current_agent
        return (
            "Alright, I’ll help you with that now.",
            JobApplicationAgent(room=agent.room, chat_ctx=context.session._chat_ctx),
        )

#______________________________________________________________________________________________________________#