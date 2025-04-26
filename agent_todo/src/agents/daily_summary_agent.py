from pydantic import BaseModel
from restack_ai.agent import agent, Message, log, NonRetryableError

class MessagesEvent(BaseModel):
    messages: list[Message]

class EndEvent(BaseModel):
    end: bool

@agent.defn()
class DailySummaryAgent:
    def __init__(self) -> None:
        self.end = False
        self.messages = [Message(
            role="system",
            content="You are an AI assistant summarizing daily activities and sections from the schedule, relationship, and thoughts.",
        )]

    @agent.event
    async def messages(self, messages_event: MessagesEvent) -> list[Message]:
        try:
            self.messages.extend(messages_event.messages)

            # Placeholder: Summarize all sections of the day
            summary = "Today's Summary:\n- Schedule: Meeting at 10AM\n- Relationship: Dinner with partner\n- Thoughts: Feeling productive!"

            self.messages.append(
                Message(
                    role="assistant",
                    content=summary,
                )
            )
        except Exception as e:
            log.error(f"Error during daily summary: {e}")
            raise NonRetryableError(str(e))
        return self.messages

    @agent.event
    async def end(self) -> EndEvent:
        log.info("DailySummaryAgent received end")
        self.end = True
        return {"end": True}