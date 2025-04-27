from datetime import timedelta

from pydantic import BaseModel
from restack_ai.agent import NonRetryableError, agent, import_functions, log

with import_functions():
    from src.functions.llm_chat import LlmChatInput, Message, llm_chat


class MessagesEvent(BaseModel):
    messages: list[Message]


class EndEvent(BaseModel):
    end: bool


@agent.defn()
class AgentDailySummary:
    def __init__(self) -> None:
        self.end = False
        self.messages = [Message(
            role="system",
            content="""
                    You are an AI assistant tasked with summarizing a user’s day across three key areas:
                    
                    🗓 Schedule
                    💞 Relationships
                    🧠 What’s on their mind

                    Instructions:
                    • Given a set of notes, updates, and reflections from the user, create a **short, friendly, and clear daily summary**.
                    • The summary should mention key highlights from each of the three categories (even if one category is missing, just skip it gracefully).
                    • Write in a warm and supportive tone, like a helpful companion.
                    
                    Example:

                    Summary:
                    "Today you managed your schedule by completing your work meetings and planning tomorrow’s lunch with Sarah. In your relationships, you had a great talk with your brother about career plans. Mentally, you reflected on feeling excited for new opportunities ahead. Good progress!"

                    Keep it short (~3-5 sentences).
                    """
        )]

    @agent.event
    async def messages(self, messages_event: MessagesEvent) -> list[Message]:
        log.info(f"Received messages: {messages_event.messages}")
        self.messages.extend(messages_event.messages)

        log.info(f"Calling llm_chat with messages: {self.messages}")
        try:
            assistant_message = await agent.step(
                function=llm_chat,
                function_input=LlmChatInput(messages=self.messages),
                start_to_close_timeout=timedelta(seconds=120),
            )
        except Exception as e:
            error_message = f"Error during llm_chat: {e}"
            raise NonRetryableError(error_message) from e
        else:
            self.messages.append(assistant_message)
            return self.messages

    @agent.event
    async def end(self, end: EndEvent) -> EndEvent:
        log.info("Received end")
        self.end = True
        return end

    @agent.run
    async def run(self, function_input: dict) -> None:
        log.info("AgentDailySummary function_input", function_input=function_input)
        await agent.condition(lambda: self.end)