from datetime import timedelta

from pydantic import BaseModel
from restack_ai.agent import NonRetryableError, agent, import_functions, log

with import_functions():
    from src.functions.llm_chat import LlmChatInput, Message, llm_chat


class MessagesEvent(BaseModel):
    messages: list[Message]


class EndEvent(BaseModel):
    end: bool


class MemoryData(BaseModel):
    schedule: str
    relationships: str
    thoughts: str


@agent.defn()
class AgentAsk:
    def __init__(self) -> None:
        self.end = False
        # Example dummy memory from the "database"
        self.memory_data = MemoryData(
            schedule="Meeting with Alex at 10AM, dentist appointment at 3PM, call with Sarah on Friday.",
            relationships="Talked to mom about vacation, had coffee with John, helped Emily with her move.",
            thoughts="Feeling motivated to start a new fitness routine, a little stressed about project deadlines."
        )
        self.messages = [Message(
            role="system",
            content=f"""
                    You are an AI assistant that knows the user's recent personal data across three areas:
                    
                    🗓 Schedule: {self.memory_data.schedule}
                    💞 Relationships: {self.memory_data.relationships}
                    🧠 Thoughts: {self.memory_data.thoughts}

                    Instructions:
                    • When asked questions, answer using ONLY the memory data provided above.
                    • If the question asks for something not present in the memory, politely say you don't know.
                    • Answer clearly, briefly, and in a friendly tone.

                    Examples:
                    - Q: "What meetings do I have?" → A: "You have a meeting with Alex at 10AM and a dentist appointment at 3PM."
                    - Q: "Who did I talk to recently?" → A: "You talked to your mom about vacation, had coffee with John, and helped Emily move."
                    - Q: "How was I feeling?" → A: "You were feeling motivated to start a new fitness routine but a bit stressed about project deadlines."

                    Important: Only answer based on the provided memory snapshot.
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
        log.info("AgentAsk function_input", function_input=function_input)
        await agent.condition(lambda: self.end)