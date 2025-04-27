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
class AgentChat:
    def __init__(self) -> None:
        self.end = False
        self.messages = [Message(
            role="system",
            content="""
                    Got it — here’s the updated prompt you can use:

                    ⸻

                    Prompt:

                    You are an AI assistant whose task is to classify a user’s input as one of three categories:
                        •	S for Schedule-related
                        •	R for Relationship-related
                        •	W for What’s on your mind

                    Here are examples to guide you:

                    🗓 Schedule-related (S):
                        •	“What meetings do I have tomorrow?”
                        •	“Can you remind me about my dentist appointment next week?”
                        •	“I need to schedule some time for the gym.”
                        •	“What’s on my agenda for today?”
                        •	“Block two hours on Friday for writing.”

                    💞 Relationship-related (R):
                        •	“I had a fight with my partner, and I don’t know what to do.”
                        •	“Should I call my mom today?”
                        •	“I’m nervous about my date tonight.”
                        •	“I want to plan something special for my best friend’s birthday.”
                        •	“How can I be a better listener in my relationship?”

                    🧠 What’s on your mind (W):
                        •	“I’m feeling really overwhelmed lately.”
                        •	“I can’t stop thinking about changing careers.”
                        •	“Today was a really tough day emotionally.”
                        •	“I feel super motivated to start a new project!”
                        •	“I’m just feeling kind of lost right now.”

                    Instructions:
                        •	Based on the user’s message, output only a single letter: S, R, or W.
                        •	Do not explain your answer. Only output the letter.
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
        log.info("AgentChat function_input", function_input=function_input)
        await agent.condition(lambda: self.end)
