from livekit.agents import function_tool, RunContext

@function_tool
async def handover_to_onboarding(context: RunContext[dict]):
    from src.agents.onboarding import OnboardingAgent
    agent = context.session.current_agent
    onboarding_agent = OnboardingAgent(chat_ctx=context.session._chat_ctx, room=agent.room)
    return onboarding_agent, "wait for a moment"

@function_tool
async def handover_to_applications(context: RunContext[dict]):
    from src.agents.job_application import JobApplicationAgent
    agent = context.session.current_agent
    job_application_agent = JobApplicationAgent(chat_ctx=context.session._chat_ctx, room=agent.room)
    return job_application_agent, "wait for a moment"
