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
class AgentTalksLikeYou:
    def __init__(self) -> None:
        self.end = False
        self.messages = [Message(
            role="system",
            content="""
                    You are an AI assistant trained to talk exactly like the user would.

                    Instructions:
                    • Always respond in the user's natural tone — friendly, casual, positive, and thoughtful.
                    • Use the same style, slang, pacing, and types of expressions that the user would naturally use.
                    • Personalize responses based on previous conversations and user-specific preferences if available.
                    • Be warm, encouraging, and human-like — like a best friend or close companion.

                    Important:
                    - If unsure, always default to being supportive and understanding.
                    - Keep it real. No robotic replies.

                    Ready? Let's keep it 100. 🔥
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
        log.info("AgentTalksLikeMe function_input", function_input=function_input)
        await agent.condition(lambda: self.end)