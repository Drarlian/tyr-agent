import json
import asyncio
from typing import List, Dict, Tuple, Optional, Callable, Union
from datetime import datetime
from tyr_agent.entities.entities import ManagerCallManyAgents, AgentCallInfo, AgentHistory, AgentInteraction
from tyr_agent.models.gemini_model import GeminiModel
from tyr_agent.models.gpt_model import GPTModel
from tyr_agent.storage.interaction_history import InteractionHistory
import uuid


class SimpleAgent:
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: Union[GeminiModel, GPTModel], storage: Optional[InteractionHistory] = None, max_history: int = 20, use_storage: bool = True, use_history: bool = True, use_score: bool = True, score_average: Union[int, float] = 3):
        self.prompt_build: str = prompt_build
        self.agent_name: str = agent_name

        self.storage: Optional[InteractionHistory] = None
        self.history: Optional[List[dict]] = None
        self.use_storage: bool = use_storage
        self.use_history: bool = use_history

        self.use_score: bool = use_score
        self.score_average: Union[int, float] = score_average if self._is_valid_score(score_average) else 3

        if use_storage and use_history:
            self.storage = storage or InteractionHistory(f"{agent_name.lower()}_history.json")
            self.history = self.storage.load_history(agent_name)

            if use_score:
                self._filter_history_by_score()

        self.agent_model: Union[GeminiModel, GPTModel] = model

        self.MAX_HISTORY = min(max_history, self.MAX_ALLOWED_HISTORY)
        self.PROMPT_TEMPLATE = ""

    async def chat(self, user_input: str, streaming: bool = False, files: Optional[List[dict]] = None, save_history: bool = True) -> Optional[str]:
        try:
            agent_response: str = self.agent_model.generate(self.prompt_build, user_input, files, self.history, self.use_history)

            if (self.use_history or self.use_storage) and save_history:
                self._update_history(user_input, [agent_response], "simple")

            return agent_response
        except Exception as e:
            print(f"❌ [SimpleAgent.chat] {type(e).__name__}: {e}")
            return None

    def _update_history(self, user_input: str, agent_response: List[str], type_agent: str, called_functions: List[dict] | None = None, score: int | None = None) -> None:
        try:
            actual_conversation = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "interaction": {
                    "user": user_input,
                    "agent": agent_response
                },
                "called_functions": called_functions if called_functions is not None else [],
                "type_agent": type_agent,
                "score": score
            }

            if self.history and self.use_history:
                self.history.append(actual_conversation)
                self.history = self.history[-self.MAX_HISTORY:]  # -> Mantendo apenas os N itens no histórico.

            if self.storage and self.use_storage:
                self.storage.save_history(self.agent_name, actual_conversation)
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro duração a atualização do histórico: {e}')

    def get_agent_history(self) -> List[dict]:
        return self.history

    def create_agent_history_with_storage(self, storage: Optional[InteractionHistory] = None, use_history: bool = True) -> None:
        """
        Cria uma instância de histórico para o agente a partir de um storage.
        Caso já exista um histórico para o agente, apenas conecta o histórico com o agente.
        :param storage: Histórico (Storage) a ser carregado, caso não seja passado será criado/procurado um.
        :param use_history: Define qual o novo valor de use_history do agente, por padrão é True.
        :return: Não retorna nada.
        """
        self.storage: InteractionHistory | None = storage or InteractionHistory(f"{self.agent_name.lower()}_history.json")
        self.history: List[dict] | None = self.storage.load_history(self.agent_name)
        self.use_history: bool = use_history

    def create_agent_history(self, new_history: List[AgentHistory], use_history: bool = True) -> bool:
        """
        Cria um histórico para o agente a patir de uma lista de AgentHistory.
        Caso já exista um histórico para o agente, reescreve o histórico atual.
        Altera o valor use_history para true automaticamente.
        :param new_history: Histórico (History) a ser carregado.
        :param use_history: Define qual o novo valor de use_history do agente, por padrão é True.
        :return: Retorna true caso tudo tenha dado certo e false caso tenha acontecido algum problema.
        """
        try:
            self.history: List[dict] = self._format_history(new_history)
            self.use_history: bool = use_history
            return True
        except Exception as e:
            return False

    def extend_agent_history(self, extended_history: List[AgentHistory]) -> bool:
        """
        Insere novos registros no histórico do agente através de uma lista de AgentHistory.
        Apenas insere os novos registro se o agente tiver um histórico.
        :param extended_history: Histórico (History) a ser carregado.
        :return: Retorna true caso tudo tenha dado certo e false caso tenha acontecido algum problema.
        """
        try:
            if self.history:
                self.history.extend(self._format_history(extended_history))
                return True
            else:
                return False
        except Exception as e:
            return False

    def remove_agent_history(self, use_history: bool = False) -> None:
        """
        Remove o histórico carregado da instância atual.
        Não exclui o arquivo físico do histórico no disco.
        :param use_history: Decide se o histórico vai continuar sendo usado, por padrão é False.
        :return: None
        """
        self.storage: InteractionHistory | None = None
        self.history: List[dict] | None = None
        self.use_history: bool = use_history

    def clear_agent_history(self) -> None:
        """
        Limpa o campo histórico da agente, caso ele exista.
        Não altera o arquivo do histórico no disco.
        :return: None
        """
        if self.history is not None:
            self.history.clear()

    def clear_agent_storage(self) -> None:
        """
        Limpa o campo storage do agente, caso ele exista.
        Limpa o arquivo do histórico no disco.
        :return: None
        """
        if self.storage is not None:
            self.storage.clear_history()

    def rate_interaction(self, interaction_id: str, score: Union[int, float]) -> Tuple[bool, bool]:
        """
        Define o score de uma interação específica do histórico.
        Pode ser feita apenas no history ou através do storage, caso ele esteja sendo usado.
        Atualiza o histórico atual do agente baseado no score_average do agente.
        :param interaction_id: ID da interação.
        :param score: Nota definida para a interação, indo apenas de 0 a 5.
        :return: Retorna uma tupla na seguinte lógica: (response_update_history, response_update_storage)
        """
        try:
            if not self.history and not self.storage:
                return False, False

            if not self._is_valid_score(score):
                return False, False

            response_update_history: bool = False
            response_update_storage: bool = True

            if self.history:
                # Atualizando o history:
                for interaction in self.history:
                    if interaction["id"] == interaction_id:
                        interaction["score"] = score
                        break
                response_update_history = True

            if self.storage:
                # Atualizando o storage:
                response_update_storage = self.storage.update_score(self.agent_name, interaction_id, score)

            if self.use_score:
                # Filtrando o "novo" histórico. (Uma interação foi avaliada, então preciso verificar se ela vai sair)
                if not self._is_valid_score(self.score_average):
                    self.score_average = 3
                self._filter_history_by_score()

            return response_update_history, response_update_storage
        except Exception as e:
            print(e)
            return False, False

    def delete_interaction(self, interaction_id: str) -> Tuple[bool, bool]:
        """
        Deleta a interação com o id informado.
        Caso o agente não utilize o storage, deleta apenas a interação do history.
        :param interaction_id: ID da interação que será deletada.
        :return: Retorna uma tupla na seguinte lógica: (response_delete_from_history, response_delete_from_storage)
        """
        try:
            if not self.history and not self.storage:
                return False, False

            response_delete_from_history: bool = False
            response_delete_from_storage: bool = True

            if self.history:
                self.history = list(filter(lambda x: x["id"] != interaction_id, self.history))
                response_delete_from_history = True

            if self.storage:
                response_delete_from_storage = self.storage.delete_history(self.agent_name, interaction_id)

            return response_delete_from_history, response_delete_from_storage
        except Exception as e:
            return False, False

    def get_score_by_id(self, interaction_id: str, find_by_history: bool) -> Union[int, float]:
        """
        Pega o score da interação procurada.
        Pode ser feita apenas no history ou através do storage, caso ele esteja sendo usado.
        :param interaction_id: Id da interação procurada.
        :param find_by_history: Define se a busca será feita no history ou no storage.
        :return: Retorna o score de uma interação.
        """
        try:
            if not self.history and not self.storage:
                return 0.0

            if find_by_history and self.history:
                # Procurando no history, se ele existir:
                for interaction in self.history:
                    if interaction.get("id") == interaction_id:
                        return interaction.get("score")

            if not find_by_history and self.storage:
                # Procurando no storage, se ele existir:
                data = self.storage.load_all()

                for interaction in data.get(self.agent_name, []):
                    if interaction.get("id") == interaction_id:
                        return interaction.get("score")

            return 0.0
        except Exception as e:
            print(f"[ERROR] - get_score_by_id: {e}")
            return 0.0

    def get_average_score(self, find_by_history: bool) -> float:
        """
        Pega a média do score no histórico.
        :param find_by_history: Define se a busca será feita no history ou no storage.
        :return: Média do score.
        """
        try:
            if not self.history and not self.storage:
                return 0.0

            sum_interactions: Union[int, float] = 0
            count_interactions: int = 0

            if find_by_history and self.history:
                for interaction in self.history:
                    if isinstance(interaction.get("score"), (int, float)):
                        sum_interactions += interaction.get("score")
                        count_interactions += 1

                if count_interactions == 0:
                    return 0.0

                return sum_interactions / count_interactions

            if not find_by_history and self.storage:
                data = self.storage.load_all()

                for interaction in data.get(self.agent_name, []):
                    if isinstance(interaction.get("score"), (int, float)):
                        sum_interactions += interaction.get("score")
                        count_interactions += 1

                if count_interactions == 0:
                    return 0.0

                return sum_interactions / count_interactions

            return 0.0
        except Exception as e:
            return 0.0

    def get_all_scores(self, find_by_history: bool) -> List[dict]:
        """
        Pega todos os scores de um agente.
        :param find_by_history: Define se a busca será feita no history ou no storage.
        :return: Retorna uma lista de dicionários contendo todos os ids e scores.
        """
        try:
            if not self.history and not self.storage:
                return []

            if find_by_history and self.history:
                return [
                    {"id": i.get("id"), "score": i.get("score")}
                    for i in self.history
                    if "id" in i
                ]

            if not find_by_history and self.storage:
                data = self.storage.load_all()

                return [
                    {"id": i.get("id"), "score": i.get("score")}
                    for i in data.get(self.agent_name, [])
                    if "id" in i
                ]

            return []
        except Exception as e:
            return []

    def _is_valid_score(self, score: Union[int, float]) -> bool:
        """
        Verifica se o score informado é válido.
        :param score: Score a ser validado.
        :return: True caso seja válido. | False caso não seja válido.
        """
        return isinstance(score, (int, float)) and 0 <= score <= 5

    def _filter_history_by_score(self) -> None:
        """
        Filtra o histórico atual com base no score_average do agente.
        :return: None
        """
        self.history = list(filter(lambda x: (x.get("score") is None or isinstance(x.get("score"), (int, float))) and (x.get("score") is None or x.get("score") >= self.score_average), self.history))

    def _format_history(self, target_history: List[AgentHistory]) -> List[dict]:
        temp_history: List[dict] = []
        for h in target_history:
            if h.get("timestamp") is None:
                timestamp: str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            else:
                timestamp: str = h.get("timestamp")

            temp_history.append(
                {
                    "id": str(uuid.uuid4()),
                    "timestamp": timestamp,
                    "interaction": {
                        "user": h["interaction"]["user"],
                        "agent": h["interaction"]["agent"]
                    },
                    "called_functions": [],
                    "type_agent": h["type_agent"],
                    "score": h.get("score") if h.get("score", False) else None,
                }
            )
        return temp_history


class ComplexAgent(SimpleAgent):
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: Union[GeminiModel, GPTModel], functions: Optional[List[Callable]] = None, final_prompt: Optional[str] = None, storage: Optional[InteractionHistory] = None, max_history: int = 20, use_storage: bool = True, use_history: bool = True, use_score: bool = True, score_average: Union[int, float] = 3):
        super().__init__(prompt_build, agent_name, model, storage, max_history, use_storage, use_history, use_score, score_average)
        self.functions: Optional[List[Callable]] = functions or {}

        self.final_prompt = final_prompt

    async def chat(self, user_input: str, streaming: bool = False, files: Optional[List[dict]] = None, save_history: bool = True) -> Optional[str]:
        try:
            agent_response = self.agent_model.generate_with_functions(self.prompt_build, user_input, files, self.history, self.use_history, self.functions, self.final_prompt)

            if (self.use_history or self.use_storage) and save_history:
                self._update_history(user_input, [agent_response], "complex")

            return agent_response
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a comunicação com o agente: {e}')
            return None


class ManagerAgent(SimpleAgent):
    MAX_ALLOWED_HISTORY = 100

    def __init__(self, agent_name: str, model: Union[GeminiModel, GPTModel], agents: List[Union[SimpleAgent, ComplexAgent]], storage: Optional[InteractionHistory] = None, max_history: int = 100, use_storage: bool = True, use_history: bool = True, use_score: bool = True, score_average: Union[int, float] = 3):
        super().__init__("", agent_name, model, storage, max_history, use_storage, use_history, use_score, score_average)

        self.agents: Dict[str, Union[SimpleAgent, ComplexAgent]] = {agent.agent_name: agent for agent in agents}

    async def chat(self, user_input: str, streaming: bool = False, files: Optional[List[dict]] = None, save_history: bool = True) -> Optional[str]:
        # Gera o prompt com base nos agentes disponíveis:
        prompt: str = self.__generate_prompt()

        if not prompt:
            print(f"[ERRO] Não foi possível montar o prompt.")
            return None

        try:
            agent_response: str = self.agent_model.generate(prompt, user_input, None, self.history, self.use_history)

            extracted_agents = self.__extract_agent_call(agent_response)

            if not extracted_agents:
                if self.use_history and save_history:
                    self.__update_history(user_input, agent_response, False, [])
                return agent_response

            # Encontrando os Agentes solicitados:
            delegated_agents = self.__find_correct_agents(extracted_agents)

            if len(delegated_agents) == 0:
                agentes_requisitados = extracted_agents if isinstance(extracted_agents, str) else json.dumps(extracted_agents, ensure_ascii=False)
                print(f"[ERRO] Nenhum dos agentes requisitados foi encontrado: {agentes_requisitados}")
                return None

            response_delegated_agents = await self.__execute_agents_calls(delegated_agents)

            final_prompt: str = self.__generate_final_prompt(response_delegated_agents)

            if not final_prompt:
                return "\n".join(f"{k}: {v}" for agent in response_delegated_agents for k, v in agent.items())

            final_agent_response: str = self.agent_model.generate(final_prompt, user_input, None, None, False)

            if (self.use_history or self.use_storage) and save_history:
                self.__update_history(user_input, agent_response, True, response_delegated_agents)

            return final_agent_response

        except Exception as e:
            print(f"[ERROR] - Falha ao interpretar a resposta do manager: {e}")
            return None

    def __extract_agent_call(self, response_text: str) -> Optional[ManagerCallManyAgents]:
        try:
            text_cleaned = (
                response_text.removeprefix("```json\n").removesuffix("\n```").replace("\n", "")
                .replace("`", "").replace("´", "").strip()
            )

            data = json.loads(text_cleaned)
            if isinstance(data, dict) and "call_agents" in data and "agents_to_call" in data:
                return data
            return None
        except json.JSONDecodeError:
            return None

    def __find_correct_agents(self, agents_to_call: ManagerCallManyAgents) -> List[AgentCallInfo]:
        try:
            agents = []
            for agent in agents_to_call.get("agents_to_call", []):
                if agent.get("agent_to_call", "") not in self.agents.keys():
                    raise Exception("Erro ao procurar o agente correspondente.")
                else:
                    agents.append({"agent": self.agents[agent.get("agent_to_call")], "message": agent.get("agent_message")})

            # Encontrando o Agente solicitado:
            return agents
        except Exception as e:
            print(f"[ERROR] - Falha ao encontrar o agente responsável: {e}")
            return []

    async def __execute_agents_calls(self, delegated_agents: List[AgentCallInfo]) -> List[dict]:
        # Execução paralela dos agentes:
        coroutines = [
            delegated_agent["agent"].chat(delegated_agent["message"], streaming=True)
            for delegated_agent in delegated_agents
        ]

        results = await asyncio.gather(*coroutines, return_exceptions=True)

        agents_response: List[dict] = []

        for agent_info, result in zip(delegated_agents, results):
            agent_name = agent_info["agent"].agent_name

            if isinstance(result, Exception):
                print(f"[ERRO] Agente '{agent_name}' falhou: {type(result).__name__} - {result}")
                agents_response.append({agent_name: "[Erro ao gerar resposta]"})
            else:
                if isinstance(result, str):
                    agents_response.append({agent_name: result})

        return agents_response

    def __generate_prompt(self) -> str:
        try:
            formatted_agents = "\n".join(
                f"- Nome do Agente: {agent_name}\n  Definição do Agente: {agent.prompt_build}\n" for agent_name, agent in
                self.agents.items())

            first_prompt_template: str = """Você é um agente **gerente** responsável por coordenar uma equipe de agentes especializados. Sua missão é **analisar perguntas**, **dividir em partes quando necessário** e **delegar as partes apropriadas aos agentes mais adequados**. Caso nenhum agente seja apropriado, **você mesmo deve responder com um texto simples (sem JSON)**.

🚨 INSTRUÇÃO CRÍTICA:

Você DEVE responder **EXCLUSIVAMENTE com um JSON PURO** **quando decidir acionar qualquer agente**.

⛔️ NUNCA misture texto comum com JSON.
⛔️ NUNCA use markdown, blocos de código, ou comentários.
✅ A resposta deve começar com `{` e terminar com `}`.

📌 FORMATO DO JSON:

{
  "call_agents": true,
  "agents_to_call": [
    {
      "agent_to_call": "<nome_do_agente>",
      "agent_message": "<mensagem que deve ser enviada ao agente>"
    }
  ]
}

🧠 INSTRUÇÕES DE USO:

1. Analise a pergunta do usuário.
2. Divida em partes independentes, se necessário.
3. Agrupe todas as partes destinadas ao mesmo agente em **uma única mensagem concatenada**.
4. Escolha os agentes corretos com base na descrição.
5. Retorne um JSON com todos os agentes envolvidos e a mensagem para cada um.
6. Caso nenhum agente possa ajudar, responda diretamente com texto comum (sem JSON).
"""

            second_prompt_template: str = f"""
🤖 AGENTES DISPONÍVEIS:

{formatted_agents}"""

            third_prompt_template: str = """
✅ EXEMPLOS DE RESPOSTA VÁLIDA:

➡️ Chamada de um único agente:
{
  "call_agents": true,
  "agents_to_call": [
    {
      "agent_to_call": "MathAgent",
      "agent_message": "Quanto é 27 vezes 3?"
    }
  ]
}

➡️ Chamada de múltiplos agentes:
{
  "call_agents": true,
  "agents_to_call": [
    {
      "agent_to_call": "MathAgent",
      "agent_message": "Qual é a raiz quadrada de 144?"
    },
    {
      "agent_to_call": "SignAgent",
      "agent_message": "O que significa ser do signo de Peixes?"
    }
  ]
}

➡️ Agrupando múltiplas perguntas para o mesmo agente:
{
  "call_agents": true,
  "agents_to_call": [
    {
      "agent_to_call": "MathAgent",
      "agent_message": "Quanto é 600+600? Quanto é 100-40?"
    }
  ]
}

➡️ Resposta direta (sem agentes):
Claro! Posso te ajudar com isso diretamente. Me diga exatamente o que precisa.

🧷 REGRAS OBRIGATÓRIAS:

- O campo "call_agents" deve ser true quando estiver chamando agentes.
- O campo "agents_to_call" deve ser uma lista com objetos contendo:
    - "agent_to_call": o nome exato do agente.
    - "agent_message": a mensagem específica que ele deve receber.
- Se houver múltiplas mensagens para o mesmo agente, elas DEVEM ser agrupadas em uma só.
- Se nenhuma chamada de agente for necessária, responda com texto comum e NÃO use JSON.
- Nunca responda com um JSON se não for chamar agentes."""

            return first_prompt_template + second_prompt_template + third_prompt_template
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""

    def __generate_final_prompt(self, agents_response: List[dict]) -> str:
        try:
            combined: str = "\n".join(f"{k}: {v}" for agent in agents_response for k, v in agent.items())
            enriched_prompt: str = f"""Você é um agente gerente que tem sob sua responsabilidade alguns agentes especializados.

Você solicitou a chamada de alguns agentes. 
Os seguintes agentes responderam individualmente:
{combined}

Seu papel é responder ao usuário com base nas respostas dos agente. 
Para isso gere uma única resposta unificada e natural para o usuário final."""

            return enriched_prompt

        except Exception as e:
            print(f"[ERROR] - Falha ao gerar o prompt final do Manager: {e}")
            return ""

    def __update_history(self, user_input: str, agent_response: str, called_delegated_agents: bool, response_delegated_agents: List[dict], score: int | None = None) -> None:
        try:
            actual_conversation = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "interaction": {
                    "user": user_input,
                    "agent": []
                },
                "type_agent": "manager",
                "score": score,
                "called_agents": called_delegated_agents
            }

            if called_delegated_agents:
                for agent in response_delegated_agents:
                    for agente_name, response in agent.items():  # -> Esse for é sempre fixo em 1 item.
                        actual_conversation["interaction"][agente_name] = [response]

            actual_conversation["interaction"]['agent'] = [agent_response]

            self.history.append(actual_conversation)
            self.history = self.history[-self.MAX_HISTORY:]  # -> Mantendo apenas os N itens no histórico.
            self.storage.save_history(self.agent_name, actual_conversation)
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro duração a atualização do histórico: {e}')
