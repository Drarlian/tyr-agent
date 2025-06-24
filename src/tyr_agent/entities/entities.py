from typing import TypedDict, List, Optional, Union, TYPE_CHECKING

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


class AgentInteraction(TypedDict):
    user: str
    agent: List[str]


class AgentHistory(TypedDict):
    timestamp: Optional[str]
    interaction: AgentInteraction
    score: Optional[Union[int, float]]
    type_agent: str
