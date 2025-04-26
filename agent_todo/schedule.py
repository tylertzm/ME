import asyncio
import sys
import time

from restack_ai import Restack
from src.agents.agent_todo import AgentTodo
from src.agents.AgentRelationships import AgentRelationships
from src.agents.AgentMind import AgentMind
from src.agents.AgentSchedule import AgentSchedule


async def run_agent(client, agent_class):
    agent_id = f"{int(time.time() * 1000)}-{agent_class.__name__}"
    run_id = await client.schedule_agent(
        agent_name=agent_class.__name__,
        agent_id=agent_id,
        input=agent_class(),
    )
    await client.get_agent_result(agent_id=agent_id, run_id=run_id)


async def main() -> None:
    client = Restack()

    agents = [
        AgentTodo,
        AgentRelationships,
        AgentMind,
        AgentSchedule,
    ]

    # Run all agents in parallel
    await asyncio.gather(*(run_agent(client, agent) for agent in agents))

    sys.exit(0)


def run_schedule() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run_schedule()