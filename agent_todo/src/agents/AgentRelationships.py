from datetime import timedelta

from pydantic import BaseModel
from restack_ai.agent import (
    NonRetryableError,
    agent,
    import_functions,
    log,
)

with import_functions():
    from openai import pydantic_function_tool

    from src.functions.llm_chat import (
        LlmChatInput,
        Message,
        llm_chat,
    )


class MessagesEvent(BaseModel):
    messages: list[Message]


class EndEvent(BaseModel):
    end: bool


@agent.defn()
class AgentRelationships:
    def __init__(self) -> None:
        self.end = False
        self.messages = [Message(
            role="system",
            content="You are an AI assistant that helps the user improve their relationships, giving advice about family, friendships, dating, and communication."
        )]

    @agent.event
    async def messages(self, messages_event: MessagesEvent) -> list[Message]:
        try:
            self.messages.extend(messages_event.messages)

            try:
                completion = await agent.step(
                    function=llm_chat,
                    function_input=LlmChatInput(messages=self.messages),
                    start_to_close_timeout=timedelta(seconds=120),
                )
            except Exception as e:
                raise NonRetryableError(f"Error during llm_chat: {e}") from e
            else:
                self.messages.append(
                    Message(
                        role="assistant",
                        content=completion.choices[0].message.content or "",
                    )
                )
        except Exception as e:
            log.error(f"Error during message event: {e}")
            raise
        else:
            return self.messages

    @agent.event
    async def end(self) -> EndEvent:
        self.end = True
        return {"end": True}

    @agent.run
    async def run(self, function_input: dict) -> None:
        await agent.condition(lambda: self.end)