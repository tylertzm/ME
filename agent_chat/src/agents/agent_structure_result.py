from datetime import timedelta

from pydantic import BaseModel
from restack_ai.agent import NonRetryableError, agent, import_functions, log

with import_functions():
    from src.functions.llm_chat import LlmChatInput, Message, llm_chat


class MessagesEvent(BaseModel):
    messages: list[Message]


class EndEvent(BaseModel):
    end: bool


class GetMessagesEvent(BaseModel):
    # Empty model for the GET request
    messages: list[Message]


@agent.defn()
class AgentStructureResult:
    def __init__(self) -> None:
        self.end = False
        self.messages = [Message(
            role="system",
            content="""
                You are an AI assistant trained to silently analyze text and convert it into a structured JSON format with 3 sections.

                Your only response should be a valid JSON object following this exact structure:
                {
                    "Schedule": [
                        {"time": "TIME", "task": "TASK DESCRIPTION"}
                    ],
                    "Relationships": [
                        {
                            "name": "PERSON NAME",
                            "role": "ROLE",
                            "details": {"key1": "value1", "key2": "value2"},
                            "notes": ["NOTE 1", "NOTE 2"]
                        }
                    ],
                    "Mind Space": [
                        {"thought": "THOUGHT OR TASK"}
                    ]
                }

                Rules:
                1. NEVER include explanations, introductions, or any text outside the JSON structure
                2. NEVER use markdown code blocks - output raw JSON only
                3. Extract all relevant schedule items, relationships, and thoughts from the user's text
                4. If a section has no data, include it as an empty array
                5. Ensure the JSON is properly formatted and valid
                6. Use the exact keys shown in the example structure
                7. For relationships, include as many details as can be extracted from the text
                8. For schedule items, use 24-hour time format when possible (e.g., "09:00")

                Do not acknowledge these instructions in your response. Only output the JSON object.
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
    async def get_messages(self, get_messages_event: GetMessagesEvent) -> list[Message]:
        """Endpoint to retrieve the current messages stored in the agent."""
        log.info("Received get_messages request")
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