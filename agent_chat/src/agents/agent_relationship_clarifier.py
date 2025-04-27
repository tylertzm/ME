# agent_relationship_clarifier.py
from datetime import timedelta

from pydantic import BaseModel
from restack_ai.agent import NonRetryableError, agent, import_functions, log

with import_functions():
    from src.functions.llm_chat import LlmChatInput, Message, llm_chat


class ClarifyEvent(BaseModel):
    """Single event: {"name": "...", "options": ["opt A", "opt B"]}"""
    ambiguities: list[dict]


class EndEvent(BaseModel):
    end: bool


@agent.defn()
class AgentRelationshipClarifier:
    """
    Produces ONE short multiple-choice question per ambiguous person.
    Expects ClarifyEvent → returns list[Message] where assistant asks questions.
    """

    def __init__(self) -> None:
        self.end = False
        self.system = Message(
            role="system",
            content="""
You are an AI assistant that helps disambiguate people with the same name.
Take a JSON input like:
[
  {"name":"John","options":["collaborator | project: exciting project",
                            "dentist | location: Berlin"]},
  ...
]

For EACH object output **exactly one question**:

John – which person do you mean?
1. collaborator | project: exciting project
2. dentist | location: Berlin
3. Someone new

Separate questions with a blank line. Keep it concise; no extra prose.
""",
        )

    @agent.event
    async def clarifications(self, ev: ClarifyEvent) -> list[Message]:
        messages = [
            self.system,
            Message(role="user", content=json.dumps(ev.ambiguities)),
        ]
        try:
            assistant = await agent.step(
                function=llm_chat,
                function_input=LlmChatInput(messages=messages),
                start_to_close_timeout=timedelta(seconds=60),
            )
        except Exception as exc:
            raise NonRetryableError(str(exc)) from exc
        else:
            return [assistant]

    @agent.event
    async def end(self, ev: EndEvent) -> EndEvent:
        self.end = True
        return ev

    @agent.run
    async def run(self, _: dict) -> None:
        await agent.condition(lambda: self.end)
