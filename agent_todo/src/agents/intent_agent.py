from pydantic import BaseModel
from restack_ai.agent import agent, Message, log, NonRetryableError

class MessagesEvent(BaseModel):
    messages: list[Message]

class EndEvent(BaseModel):
    end: bool

@agent.defn()
class IntentAgent:
    def __init__(self) -> None:
        self.end = False
        self.messages = [Message(
            role="system",
            content="You are an AI assistant recognizing if the input is related to the schedule, relationship, or thoughts section.",
        )]

    @agent.event
    async def messages(self, messages_event: MessagesEvent) -> list[Message]:
        try:
            self.messages.extend(messages_event.messages)

            # Placeholder: Recognize intent in the input
            # You can replace this with a logic to classify inputs into the desired categories
            recognized_intent = "schedule"  # Placeholder, replace with actual classification logic

            response_content = f"Recognized intent: {recognized_intent}"

            self.messages.append(
                Message(
                    role="assistant",
                    content=response_content,
                )
            )
        except Exception as e:
            log.error(f"Error during intent recognition: {e}")
            raise NonRetryableError(str(e))
        return self.messages

    @agent.event
    async def end(self) -> EndEvent:
        log.info("IntentAgent received end")
        self.end = True
        return {"end": True}