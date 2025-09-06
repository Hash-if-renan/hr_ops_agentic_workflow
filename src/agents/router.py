# src/agents/router.py
from livekit.agents import Agent, function_tool, RunContext

ROUTER_INSTRUCTIONS = """
You are Eve, the router. Greet briefly, then decide which domain the user needs:
- Onboarding: offer letter, CTC/benefits, joining date, pre-boarding, documents, BGV, reporting manager, location, workstation.
- Applications: application status, application ID, JR-xxx job ID, submission/in_review/interview/rejected/selected, resume needed to apply, etc.

Immediately call ONE of the transfer tools (`go_onboarding` or `go_applications`) and then stop.
Do not answer domain questions yourself; just route.
"""

class RouterAgent(Agent):
    def __init__(self):
        super().__init__(instructions=ROUTER_INSTRUCTIONS)

    @function_tool
    async def go_onboarding(self, context: RunContext[dict]):
        # Lazy import to avoid circular import
        from src.agents.onboarding import OnboardingAgent
        return ("Connecting you to onboarding…", OnboardingAgent())

    @function_tool
    async def go_applications(self, context: RunContext[dict]):
        # Lazy import to avoid circular import
        from src.agents.job_application import JobApplicationAgent
        return ("Connecting you to application status support…", JobApplicationAgent())
#______________________________________________________________________________________________________________#