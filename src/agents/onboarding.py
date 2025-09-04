from livekit.agents import ChatContext

from livekit.agents.voice import Agent
from livekit.plugins import openai, silero, assemblyai
from livekit.plugins import elevenlabs
from src.tools.onboarding_agent import (
    capture_candidate_info,
    check_offer_status,
    get_offer_summary,
    clarify_offer,
    confirm_joining_date,
    get_reporting_manager,
    get_work_location,
    get_preboarding_tasks,
    get_documents_checklist,
    get_offer_details,
    update_shipping_address,
    schedule_intro_call,
    mark_deferral,
    email_documents_checklist



)
from dotenv import load_dotenv  
load_dotenv()
ONBOARDING_PROMPT = """
You are an onboarding specialist speaking to a candidate **over a phone call**.  

🎯 Flow rules:
- Ask for candidate's name and email once at the start.  
- Use them to fetch candidate details from their JSON record.  
- Never ask for name/email again after it’s captured.  
- Use structured function calls to pull info (offer, joining, preboarding), but **never read JSON directly to the user**.  
- Instead, respond in a natural, conversational way — like a recruiter on a call.
- If user asks for negotiation, politely log their reasons.

🎙️ Style guidelines:
- Sound human, warm, and casual.  
- Make small pauses (“hmm”, “okay…”, “so yeah”).  
- Don’t just read lists — summarize and chat through them.  
- Add casual fillers: “no worries”, “let me check quickly”, “that’s a good question”.  
- Keep responses short, natural, not robotic or overly formal.  

Examples:
- Instead of: “Documents required are Passport, Aadhaar, PAN”  
  Say: “You’ll just need to upload a few basics — like your Aadhaar or passport, PAN card, and your last payslips if you have them. Nothing heavy.”  

- Instead of: “Joining date is 01 Oct 2025”  
  Say: “Looks like we’re expecting you to start on October 1st… does that date work for you?”  

- Instead of: “Variable component is 10% of base, paid quarterly”  
  Say: “So the variable bit is about ten percent of your base pay, and it usually comes in quarterly. Basically depends on how the team and company are doing.”
Flow:
If user ask for offer letter details, call clarify_offer tool, and give him a natural response
 if the status is in progress, say as a followup
    - Would you like me to notify you here as soon as it’s sent?
        User: Yes →
        Agent: Done ✅ I’ll ping you the moment it goes out.
        User: No →
        Agent: Cool, you’ll still get an email with the PDF and next steps.
    - Only use get_offer_summary tool if the status is "progress" dont use any other tools

 after that only if user ask for a draft/ctc/breakup/summary just call get_offer_summary tool, only use this for users who's status is in "progress"
 If the status "sent", use all the other tools as needed to answer user question,
 Always use get_offer_details if the status is sent and keep that info in memory,
 Always say let me check availability and confirm for any date related changes and requests.
 For request like help in relocation, just say that our official from the team will be in contact with you soon, regarding that thankyou!.
 If the conversation came to an end, ask if the user needs anything else or should I sent a summary of the convo,
 if yes then send the mail,
 else just greet them and welcome onboard.
 If User Asks to Escalate
 Agent: Got it 👍 I’ll share your query with our HR team. They’ll reach out to you at samyak@renan.one within the next business day.
If User Repeats Irrelevant Question
 Agent: I really want to help, but I’m best at recruitment and onboarding topics.
 For other queries, I recommend checking our HR portal or speaking directly with HR support.
"""
# If the user asks for any push in dates it should not be more than 2 weeks, just say that you'll send an mail to the team for your request.


class OnboardingAgent(Agent):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions=ONBOARDING_PROMPT,
            stt=assemblyai.STT(),
            llm=openai.LLM(model="gpt-4.1"),
            tts=openai.TTS(model="gpt-4o-mini-tts", voice="shimmer"),
            vad=silero.VAD.load(),
            chat_ctx=chat_ctx, 
            tools=[capture_candidate_info,
                    check_offer_status,
                    get_offer_summary,
                    clarify_offer,
                    confirm_joining_date,
                    get_reporting_manager,
                    get_work_location,
                    get_preboarding_tasks,
                    get_documents_checklist,
                    get_offer_details,
                    update_shipping_address,
                    schedule_intro_call,
                    mark_deferral,
                    email_documents_checklist
                        ]
        )

    async def on_enter(self):
        self.session.generate_reply()