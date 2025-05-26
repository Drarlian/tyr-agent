from typing import TypedDict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from tyr_agent import SimpleAgent, ComplexAgent


class ManagerCallAgent(TypedDict):
    agent_to_call: str
    agent_message: str


class ManagerCallManyAgents(TypedDict):
    call_agents: bool
    agents_to_call: List[ManagerCallAgent]


class AgentCallInfo(TypedDict):
    agent: "SimpleAgent | ComplexAgent"
    message: str
