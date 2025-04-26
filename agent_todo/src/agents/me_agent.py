from pydantic import BaseModel
from restack_ai.agent import agent, Message, log, NonRetryableError

class MessagesEvent(BaseModel):
    messages: list[Message]

class EndEvent(BaseModel):
    end: bool

@agent.defn()
class MeAgent:
    def __init__(self) -> None:
        self.end = False
        self.messages = [Message(
            role="system",
            content="You are an AI assistant that communicates in the way the user would. You reflect their tone and preferences.",
        )]

    @agent.event
    async def messages(self, messages_event: MessagesEvent) -> list[Message]:
        try:
            self.messages.extend(messages_event.messages)

            # Placeholder: Mimic user tone, can be expanded based on user-specific data
            user_tone_response = "Sure, I can handle that! Let me get on it."

            self.messages.append(
                Message(
                    role="assistant",
                    content=user_tone_response,
                )
            )
        except Exception as e:
            log.error(f"Error in MeAgent: {e}")
            raise NonRetryableError(str(e))
        return self.messages

    @agent.event
    async def end(self) -> EndEvent:
        log.info("MeAgent received end")
        self.end = True
        return {"end": True}