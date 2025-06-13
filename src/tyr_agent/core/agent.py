import json
import asyncio
import google.generativeai as genai
from typing import List, Dict, Optional, Callable, Union
from datetime import datetime
from tyr_agent.entities.entities import ManagerCallManyAgents, AgentCallInfo
from tyr_agent.models.gemini_model import GeminiModel
from tyr_agent.models.gpt_model import GPTModel
from tyr_agent.storage.interaction_history import InteractionHistory
import uuid


class SimpleAgent:
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: Union[GeminiModel, GPTModel], storage: Optional[InteractionHistory] = None, max_history: int = 20, use_history: bool = True, use_score: bool = True, score_average: Union[int, float] = 3):
        self.prompt_build: str = prompt_build
        self.agent_name: str = agent_name

        self.storage: Optional[InteractionHistory] = None
        self.history: Optional[List[dict]] = None
        self.use_history: bool = use_history

        self.use_score: bool = use_score
        self.score_average: Union[int, float] = score_average if self._is_valid_score(score_average) else 3

        if use_history:
            self.storage = storage or InteractionHistory(f"{agent_name.lower()}_history.json")
            self.history = self.storage.load_history(agent_name)

            if use_score:
                self._filter_history_by_score()

        self.agent_model: Union[GeminiModel, GPTModel] = model

        self.MAX_HISTORY = min(max_history, self.MAX_ALLOWED_HISTORY)
        self.PROMPT_TEMPLATE = ""

    async def chat(self, user_input: str, streaming: bool = False, files: Optional[List[dict]] = None, save_history: bool = True) -> Optional[str]:
        try:
            agent_response: str = self.agent_model.generate(user_input, files, self.prompt_build, self.history, self.use_history)

            if self.use_history and save_history:
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

            self.history.append(actual_conversation)
            self.history = self.history[-self.MAX_HISTORY:]  # -> Mantendo apenas os N itens no histórico.
            self.storage.save_history(self.agent_name, actual_conversation)
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro duração a atualização do histórico: {e}')

    def get_agent_history(self) -> List[dict]:
        return self.history

    def create_agent_history(self, storage: Optional[InteractionHistory] = None) -> None:
        """
        Cria uma instância para de histórico o agente atual.
        Caso já exista um histórico para o agente atual, apenas conecta o histórico com o agente.
        :param storage: Histórico a ser carregado, caso não seja passado será criado/procurado um.
        :return: Não retorna nada.
        """
        self.storage: InteractionHistory | None = storage or InteractionHistory(f"{self.agent_name.lower()}_history.json")
        self.history: List[dict] | None = self.storage.load_history(self.agent_name)
        self.use_history: bool = True

    def remove_agent_history(self) -> None:
        """
        Remove o histórico carregado da instância atual.
        Não exclui o arquivo físico do histórico no disco.
        :return: None
        """
        self.storage: InteractionHistory | None = None
        self.history: List[dict] | None = None
        self.use_history: bool = False

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
        Realmente limpa o arquivo do histórico no disco.
        :return: None
        """
        if self.storage is not None:
            self.storage.clear_history()

    def rate_interaction(self, interaction_id: str, score: Union[int, float]) -> bool:
        """
        Define o score de uma interação específica do histórico.
        Atualiza o histórico atual do agente baseado no score_average do agente.
        :param interaction_id: ID da interação.
        :param score: Nota definida para a interação, indo apenas de 0 a 5.
        :return: True caso tenha dado certo | False caso tenha dado errado.
        """
        try:
            if not self.use_history or not self.storage:
                return False

            if not self._is_valid_score(score):
                return False

            response_update: bool = self.storage.update_score(self.agent_name, interaction_id, score)

            self.history = self.storage.load_history(self.agent_name)

            if self.use_score:
                if not self._is_valid_score(self.score_average):
                    self.score_average = 3
                self._filter_history_by_score()

            return response_update
        except Exception as e:
            print(e)
            return False

    def delete_interaction(self, interaction_id: str) -> bool:
        """
        Deleta a interação com o id informado.
        :param interaction_id: ID da interação que será deletada.
        :return: True caso tenha dado certo | False caso tenha dado errado.
        """
        try:
            self.history = list(filter(lambda x: x["id"] != interaction_id, self.history))
            response_delete_storage = self.storage.delete_history(self.agent_name, interaction_id)

            return response_delete_storage
        except Exception as e:
            return False

    def get_score_by_id(self, interaction_id: str) -> Union[int, float]:
        """
        Pega o score da interação procurada.
        :return: Retorna o score de uma interação.
        """
        try:
            if not self.storage:
                return 0.0

            data = self.storage.load_all()

            for interaction in data.get(self.agent_name, []):
                if interaction.get("id") == interaction_id:
                    return interaction.get("score")

            return 0.0
        except Exception as e:
            print(f"[ERROR] - get_score_by_id: {e}")
            return 0.0

    def get_average_score(self) -> float:
        """
        Pega a média do score no histórico.
        :return: Média do score.
        """
        try:
            if not self.storage:
                return 0.0

            data = self.storage.load_all()

            sum_interactions: Union[int, float] = 0
            count_interactions: int = 0

            for interaction in data.get(self.agent_name, []):
                if isinstance(interaction.get("score"), (int, float)):
                    sum_interactions += interaction.get("score")
                    count_interactions += 1

            if count_interactions == 0:
                return 0.0

            return sum_interactions / count_interactions
        except Exception as e:
            return 0.0

    def get_all_scores(self) -> List[dict]:
        """
        Pega todos os scores de um agente.
        :return: Retorna uma lista de dicionários contendo todos os ids e scores.
        """
        try:
            if not self.storage:
                return []

            data = self.storage.load_all()

            return [
                {"id": i.get("id"), "score": i.get("score")}
                for i in data.get(self.agent_name, [])
                if "id" in i
            ]
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


class ComplexAgent(SimpleAgent):
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: Union[GeminiModel, GPTModel], functions: Optional[List[Callable]] = None, storage: Optional[InteractionHistory] = None, max_history: int = 20, use_history: bool = True, use_score: bool = True, score_average: Union[int, float] = 3):
        super().__init__(prompt_build, agent_name, model, storage, max_history, use_history, use_score, score_average)
        self.functions: Optional[List[Callable]] = functions or {}

        self.PROMPT_TEMPLATE = ""

    async def chat(self, user_input: str, streaming: bool = False, files: Optional[List[dict]] = None, save_history: bool = True) -> str | None:
        try:
            agent_response = self.agent_model.generate_with_functions(user_input, files, self.prompt_build, self.history, self.use_history, self.functions)

            if self.use_history and save_history:
                self._update_history(user_input, [agent_response], "complex")

            return agent_response
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a comunicação com o agente: {e}')
            return None

    def __extract_function_calls(self, response_text: str) -> Optional[dict]:
        try:
            response_text = response_text.removeprefix('```json\n').removesuffix("\n```")
            response_text = response_text.replace("\n", "").replace("`", "").replace("´", "")
            data = json.loads(response_text)
            if isinstance(data, dict):
                return data if data.get("call_functions") else []
            return None
        except json.JSONDecodeError:
            return None

    def __execute_function(self, call: dict) -> str:
        name = call.get("function_name")
        params = call.get("parameters", {})
        func = self.functions.get(name)

        if not func:
            return f"Função '{name}' não encontrada."

        try:
            result = func(**params)
            return f"O resultado é: {result}"
        except Exception as e:
            return f"Erro ao executar '{name}': {e}"

    def __generate_prompt_with_functions(self, prompt_text: str) -> str:
        import inspect

        try:
            if not self.use_history or not self.history:
                formatted_history = False
            else:
                def insert_score(score: Union[int, float, float]):
                    if self.use_score:
                        return f" - Score: {str(score)+'/5' if score is not None else 'Não consta'}"
                    else:
                        return ''

                formatted_history = "\n".join(
                    f"{item['timestamp']}{insert_score(item['score'])}\nUser: {item['interaction']['user']}\nAgent: {' | '.join(item['interaction']['agent'])}"
                    for item in self.history
                )

            function_list = "\n".join(
                f"- {name}{inspect.signature(f)}"
                for name, f in self.functions.items()
            )

            call_function_explanation = """
{
    "call_functions": true, 
    "functions_to_execute": 
        [
            {
                "function_name": "nome_da_funcao", 
                "parameters": {"parametro_1": "valor_parametro_1", "parametro_n": "valor_parametro_n"}
            },
        ],
    "message_to_user": "texto explicativo amigável"
}"""

            first_prompt_template: str = f"{self.prompt_build}\n"

            if self.functions:
                second_prompt_template: str = f"""
Você tem acesso às seguintes funções que podem ser utilizadas para responder perguntas do usuário:
{function_list}

Sempre que identificar que precisa executar uma ou mais funções para responder corretamente, gere uma resposta no formato JSON no seguinte formato:
{call_function_explanation}
                """
            else:
                second_prompt_template: str = ""

            if self.use_history and formatted_history:
                third_prompt_template: str = f"""
Você pode usar o histórico de conversas abaixo para responder perguntas relacionadas a interações anteriores com o usuário.
Se o usuário perguntar sobre algo que já foi dito anteriormente, procure a informação no histórico.
{
'''\nCada resposta do agente no histórico pode conter uma nota de 0 a 5, representando o quanto ela foi útil para o usuário. 
Use essas notas como um indicativo da qualidade da resposta anterior. Priorize informações com notas mais altas e busque manter esse nível de qualidade em sua resposta atual.\n''' if self.use_score else ''
}
Histórico de Conversas:
{formatted_history if formatted_history else "Não Consta."}
                """
            else:
                third_prompt_template: str = ""

            fourth_prompt_template: str = f"""
Mensagem atual:
{prompt_text}"""

            final_prompt_template = first_prompt_template + second_prompt_template + third_prompt_template + fourth_prompt_template

            return final_prompt_template
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""

    def __generate_final_prompt(self, prompt_text: str, results: Dict[str, str], save_history: bool = True) -> str:
        # Segunda rodada: prompt enriquecido com resultados
        enriched_prompt = f"""
Você é um agente capaz de executar algumas funções.

O usuário fez a seguinte pergunta inicialmente:
{prompt_text}

Como um agente você solicitou a execução das funções abaixo e recebeu o retorno, veja:
{json.dumps(results, indent=2, ensure_ascii=False)}

Com base nos resultados das funções, gere uma resposta natural para o usuário.
        """

        return enriched_prompt


class ManagerAgent(SimpleAgent):
    MAX_ALLOWED_HISTORY = 100

    def __init__(self, agent_name: str, model: genai.GenerativeModel, agents: Dict[str, Union[SimpleAgent, ComplexAgent]], storage: Optional[InteractionHistory] = None, max_history: int = 100, use_history: bool = True, use_score: bool = True, score_average: Union[int, float] = 3):
        super().__init__("", agent_name, model, storage, max_history, use_history, use_score, score_average)
        self.prompt_build: str = ""

        self.agents: Dict[str, Union[SimpleAgent, ComplexAgent]] = agents

        self.PROMPT_TEMPLATE: str = ""

    async def chat(self, user_input: str, streaming: bool = False, files: Optional[List[dict]] = None, save_history: bool = True) -> Optional[str]:
        # Gera o prompt com base no input e nos agentes disponíveis
        prompt: str = self.__generate_prompt(user_input)

        if not prompt:
            print(f"[ERRO] Não foi possível montar o prompt.")
            return None

        try:
            response = await self.agent_model.generate_content_async(prompt, stream=True)
            await response.resolve()
            response_text: str = response.text.strip()

            extracted_agents = self.__extract_agent_call(response_text)

            if not extracted_agents:
                if self.use_history and save_history:
                    self.__update_history(user_input, response_text, False, [])
                return response_text

            # Encontrando os Agentes solicitados:
            delegated_agents = self.__find_correct_agents(extracted_agents)

            if len(delegated_agents) == 0:
                agentes_requisitados = extracted_agents if isinstance(extracted_agents, str) else json.dumps(extracted_agents, ensure_ascii=False)
                print(f"[ERRO] Nenhum dos agentes requisitados foi encontrado: {agentes_requisitados}")
                return None

            response_delegated_agents = await self.__execute_agents_calls(delegated_agents)

            final_prompt: str = self.__generate_final_prompt(user_input, response_delegated_agents)

            if not final_prompt:
                return "\n".join(f"{k}: {v}" for agent in response_delegated_agents for k, v in agent.items())

            response = await self.agent_model.generate_content_async(final_prompt, stream=True)
            await response.resolve()
            final_response_text: str = response.text.strip()

            if self.use_history and save_history:
                self.__update_history(user_input, final_response_text, True, response_delegated_agents)

            return final_response_text

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

    def __generate_prompt(self, user_input: str) -> str:
        try:
            if not self.use_history or not self.history:
                formatted_history = False
            else:
                def insert_score(score: Union[int, float, float]):
                    if self.use_score:
                        return f" - Score: {str(score)+'/5' if score is not None else 'Não consta'}"
                    else:
                        return ''

                formatted_history = "\n\n".join(
                    f"{item['timestamp']}{insert_score(item['score'])}\nUser: {item['interaction'].get('user', '')}\n"
                    + f"Agent: {item['interaction']['agent']}"
                    for item in self.history
                )

            formatted_agents = "\n".join(
                f"Nome do Agente: {agent_name} - Definição do Agente: {agent.prompt_build}" for agent_name, agent in
                self.agents.items())

            call_agent_explanation = """Com base na descrição dos agentes, decida se precisa chamar 0, 1 ou mais agentes.
Para chamar algum agente responda APENAS com um JSON no formato:

{
    "call_agents": true,
    "agents_to_call":
        [
            {
                "agent_to_call": "<nome_do_agente>",
                "agent_message": "<mensagem que deve ser enviada ao agente>"
            },
            ...
        ],
}"""

            first_prompt_template: str = f"""Você é um agente gerente responsável por coordenar uma equipe de agentes especializados. Cada agente possui uma função bem definida, e você deve delegar partes da pergunta do usuário para o(s) agente(s) mais adequados.
Se nenhum agente for adequado, **responda diretamente você mesmo** com um texto comum (sem JSON).

Abaixo está a descrição dos agentes disponíveis:

{formatted_agents}

O usuário fez a seguinte pergunta:

"{user_input}"

Sua tarefa é:
- Analisar a pergunta do usuário.
- Dividir a pergunta em partes, se necessário.
- Escolher o(s) agente(s) corretos para cada parte.
- Informar qual mensagem deve ser enviada a cada agente.

{call_agent_explanation}

**Importante:**
- Se a pergunta do usuário puder ser dividida entre vários agentes, crie um item para cada agente.
- Se apenas um agente for necessário, retorne o JSON contendo apenas um agente.
            """

            if self.use_history and formatted_history:
                second_prompt_template: str = f"""
Você pode usar o histórico de conversas abaixo para responder perguntas relacionadas a interações anteriores com o usuário. 
Se o usuário perguntar sobre algo que já foi dito anteriormente, procure a informação no histórico.
{
'''\nCada resposta do agente no histórico pode conter uma nota de 0 a 5, representando o quanto ela foi útil para o usuário. 
Use essas notas como um indicativo da qualidade da resposta anterior. Priorize informações com notas mais altas e busque manter esse nível de qualidade em sua resposta atual.\n''' if self.use_score else ''
}
Histórico de Conversas:
{formatted_history if formatted_history else "Não Consta."}"""
            else:
                second_prompt_template = ""

            return first_prompt_template + second_prompt_template
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""

    def __generate_final_prompt(self, user_input: str, agents_response: List[dict]) -> str:
        try:
            combined: str = "\n".join(f"{k}: {v}" for agent in agents_response for k, v in agent.items())
            enriched_prompt: str = f"""
Você é um agente gerente que tem sob sua responsabilidade alguns agentes especializados.

O usuário fez a seguinte pergunta inicialmente:
"{user_input}"

Os seguintes agentes responderam individualmente:
{combined}

Com base nessas respostas, gere uma única resposta unificada e natural para o usuário final.
        """

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
                    "user": user_input
                },
                "type_agent": "manager",
                "score": score,
                "called_agents": called_delegated_agents
            }

            if called_delegated_agents:
                for agent in response_delegated_agents:
                    for agente_name, agente_response in agent.items():  # -> Esse for é sempre fixo em 1 item.
                        actual_conversation["interaction"][agente_name] = agente_response

            actual_conversation["interaction"]['agent'] = agent_response

            self.history.append(actual_conversation)
            self.history = self.history[-self.MAX_HISTORY:]  # -> Mantendo apenas os N itens no histórico.
            self.storage.save_history(self.agent_name, actual_conversation)
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro duração a atualização do histórico: {e}')
