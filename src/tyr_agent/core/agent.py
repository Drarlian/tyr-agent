import json
import asyncio
import google.generativeai as genai
from typing import List, Dict, Optional, Callable, Union
from datetime import datetime
from tyr_agent.entities.entities import ManagerCallManyAgents, AgentCallInfo
from tyr_agent.storage.interaction_history import InteractionHistory
from tyr_agent.mixins.file_mixins import FileMixin


class SimpleAgent(FileMixin):
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: genai.GenerativeModel, storage: Optional[InteractionHistory] = None, max_history: int = 20, use_history: bool = True):
        self.prompt_build: str = prompt_build
        self.agent_name: str = agent_name

        self.storage: InteractionHistory | None = None
        self.history: List[dict] | None = None
        self.use_history: bool = use_history

        if use_history:
            self.storage = storage or InteractionHistory(f"{agent_name.lower()}_history.json")
            self.history = self.storage.load_history(agent_name)

        self.agent_model: genai.GenerativeModel = model

        self.MAX_HISTORY = min(max_history, self.MAX_ALLOWED_HISTORY)
        self.PROMPT_TEMPLATE = """
        {role}
        
        Você pode usar o histórico de conversas abaixo para responder perguntas relacionadas a interações anteriores com o usuário. 
        Se o usuário perguntar sobre algo que já foi dito anteriormente, procure a informação no histórico.

        Histórico de Conversas:
        {history}

        Mensagem atual:
        {current}
        """

    async def chat(self, user_input: str, streaming: bool = False, files: Optional[List[dict]] = None, save_history: bool = True) -> Optional[str]:
        try:
            prompt: Union[str, list] = self.__generate_prompt(user_input)

            if not prompt:
                raise Exception("[ERROR] - Erro ao gerar o prompt.")

            if files:
                files_formated: List[dict] = [self.convert_item_to_gemini_file(item["file"], item["file_name"]) for item in files]
                files_valid: List[dict] = [file for file in files_formated if file]
                prompt = [prompt] + files_valid[:10]

            response = await self.agent_model.generate_content_async(prompt, stream=True)
            await response.resolve()
            final_text: str= response.text.strip()

            if self.use_history and save_history:
                self._update_history(user_input, final_text)

            return final_text
        except Exception as e:
            print(f"❌ [SimpleAgent.chat] {type(e).__name__}: {e}")
            return None

    def __generate_prompt(self, prompt_text: str) -> str:
        try:
            if not self.use_history or not self.history:
                return self.PROMPT_TEMPLATE.format(
                    role=self.prompt_build,
                    history='Não consta.',
                    current=prompt_text
                )

            formatted_history = "\n".join(
                f"{item['Data']} - Usuário: {item['Mensagem']['Usuario']}\n{self.agent_name}: {item['Mensagem'][self.agent_name]}"
                for item in self.history
            )

            return self.PROMPT_TEMPLATE.format(
                role=self.prompt_build,
                history=formatted_history if self.history else 'Não consta.',
                current=prompt_text
            )
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""

    def _update_history(self, user_input: str, agent_response: str):
        try:
            actual_conversation = {
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Mensagem": {
                    "Usuario": user_input,
                    self.agent_name: agent_response,
                }
            }

            self.history.append(actual_conversation)
            self.history = self.history[-self.MAX_HISTORY:]  # -> Mantendo apenas os N itens no histórico.
            self.storage.save_history(self.agent_name, actual_conversation)
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro duração a atualização do histórico: {e}')

    def create_history(self, storage: Optional[InteractionHistory] = None) -> None:
        self.storage: InteractionHistory | None = storage or InteractionHistory(f"{self.agent_name.lower()}_history.json")
        self.history: List[dict] | None = self.storage.load_history(self.agent_name)
        self.use_history: bool = True

    def remove_history(self) -> None:
        """
        Remove o histórico carregado da instância atual.
        Não exclui o arquivo físico do histórico no disco.
        :return: Não retorna nada.
        """
        self.storage: InteractionHistory | None = None
        self.history: List[dict] | None = None
        self.use_history: bool = False

class ComplexAgent(SimpleAgent, FileMixin):
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: genai.GenerativeModel, functions: Optional[dict[str, Callable]] = None, storage: Optional[InteractionHistory] = None, max_history: int = 20, use_history: bool = True):
        super().__init__(prompt_build, agent_name, model, storage, max_history, use_history)
        self.functions: dict[str, Callable] = functions or {}

        self.PROMPT_TEMPLATE = ""

    async def chat(self, user_input: str, streaming: bool = False, files: Optional[List[dict]] = None, save_history: bool = True) -> str | None:
        # Primeira rodada:
        prompt: Union[str, list] = self.__generate_prompt_with_functions(user_input)

        if not prompt:
            raise Exception("[ERROR] - Erro ao gerar o prompt.")

        try:
            if files:
                files_formated: List[dict] = [self.convert_item_to_gemini_file(item["file"], item["file_name"]) for item in files]
                files_valid: List[dict] = [file for file in files_formated if file]
                prompt = [prompt] + files_valid[:10]

            response = await self.agent_model.generate_content_async(prompt, stream=True)
            await response.resolve()
            response_text = response.text.strip()

            func_calls = self.__extract_function_calls(response_text)

            if not func_calls:
                if self.use_history and save_history:
                    self._update_history(user_input, response_text)
                return response_text

            # Executa as múltiplas funções solicitadas:
            results = {}
            for call in func_calls["functions_to_execute"]:
                result = self.__execute_function(call)
                results[call['function_name']] = result

            # Criando o prompt final com o resultado da execução da função:
            return await self.__generate_and_execute_final_prompt(user_input, results, save_history)
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
            return f"❌ Função '{name}' não encontrada."

        try:
            result = func(**params)
            return f"✅ Resultado da função '{name}': {result}"
        except Exception as e:
            return f"❌ Erro ao executar '{name}': {e}"

    def __generate_prompt_with_functions(self, prompt_text: str) -> str:
        import inspect

        try:
            if not self.use_history or not self.history:
                formatted_history = False
            else:
                formatted_history = "\n".join(
                    f"{item['Data']} - Usuário: {item["Mensagem"]['Usuario']}\n{self.agent_name}: {item["Mensagem"][self.agent_name]}"
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
    "mensagem_ao_usuario": "texto explicativo amigável"
}
            """

            first_prompt_template: str = f"""
{self.prompt_build}
            """

            if self.functions:
                second_prompt_template: str = f"""
Você tem acesso às seguintes funções que podem ser utilizadas para responder perguntas do usuário:
{function_list}

Sempre que identificar que precisa executar uma ou mais funções para responder corretamente, gere uma resposta no formato JSON no seguinte formato:
{call_function_explanation}
                """
            else:
                second_prompt_template: str = ""

            third_prompt_template: str = f"""
Você pode usar o histórico de conversas abaixo para responder perguntas relacionadas a interações anteriores com o usuário. 
Se o usuário perguntar sobre algo que já foi dito anteriormente, procure a informação no histórico.

Histórico de Conversas:
{formatted_history if formatted_history else "Não Consta."}

Mensagem atual:
{prompt_text}
            """

            final_prompt_template = first_prompt_template + second_prompt_template + third_prompt_template

            return final_prompt_template
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""

    async def __generate_and_execute_final_prompt(self, prompt_text: str, results: Dict[str, str], save_history: bool = True) -> str:
        # Segunda rodada: prompt enriquecido com resultados
        enriched_prompt = f"""
{self.prompt_build}

O agente solicitou a execução das seguintes funções:
{json.dumps(results, indent=2, ensure_ascii=False)}

Mensagem original do usuário:
{prompt_text}

Agora gere uma resposta final ao usuário com base nos resultados das funções.
        """

        final_response = await self.agent_model.generate_content_async(enriched_prompt, stream=True)
        await final_response.resolve()
        final_text: str = final_response.text.strip()

        if self.use_history and save_history:
            self._update_history(prompt_text, final_text)
        return final_text


class ManagerAgent(SimpleAgent):
    MAX_ALLOWED_HISTORY = 100

    def __init__(self, agent_name: str, model: genai.GenerativeModel, agents: Dict[str, Union[SimpleAgent, ComplexAgent]], storage: Optional[InteractionHistory] = None, max_history: int = 100, use_history: bool = True):
        super().__init__("", agent_name, model, storage, max_history, use_history)
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
                formatted_history = "\n\n".join(
                    f"{item['Data']} - Usuário: {item['Mensagem'].get('Usuario', '')}\n"
                    + "\n".join(
                        f"{agent_name}: {resposta}"
                        for agent_name, resposta in item["Mensagem"].items()
                        if agent_name != "Usuario"
                    )
                    for item in self.history
                )

            formatted_agents = "\n".join(
                f"Nome do Agente: {agent_name} - Definição do Agente: {agent.prompt_build}" for agent_name, agent in
                self.agents.items())

            call_agent_explanation = """
Com base na descrição dos agentes, decida se precisa chamar 0, 1 ou mais agentes.
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
}
            """

            full_prompt = f"""
Você é um agente gerente responsável por coordenar uma equipe de agentes especializados. Cada agente possui uma função bem definida, e você deve delegar partes da pergunta do usuário para o(s) agente(s) mais adequados.
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
- Se nenhum agente for adequado, **responda diretamente você mesmo** com um texto comum (sem JSON).

Você pode usar o histórico de conversas abaixo para responder perguntas relacionadas a interações anteriores com o usuário. 
Se o usuário perguntar sobre algo que já foi dito anteriormente, procure a informação no histórico.

Histórico de Conversas:
{formatted_history if formatted_history else "Não Consta."}
            """

            return full_prompt
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""

    def __generate_final_prompt(self, user_input: str, agents_response: List[dict]) -> str:
        try:
            combined: str = "\n".join(f"{k}: {v}" for agent in agents_response for k, v in agent.items())
            prompt: str = f"""
Você é um agente gerente que tem sob sua responsabilidade alguns agentes especializados.

O usuário fez a seguinte pergunta:

"{user_input}"

Os seguintes agentes responderam individualmente:

{combined}

Com base nessas respostas, gere uma única resposta unificada e natural para o usuário.
        """

            return prompt

        except Exception as e:
            print(f"[ERROR] - Falha ao gerar o prompt final do Manager: {e}")
            return ""

    def __update_history(self, user_input: str, agent_response: str, called_delegated_agents: bool, response_delegated_agents: List[dict]) -> None:
        try:
            actual_conversation: Dict[str, str | dict[str, str] | bool] = {
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Mensagem": {
                    "Usuario": user_input
                }
            }

            if called_delegated_agents:
                for agent in response_delegated_agents:
                    for agente_name, agente_response in agent.items():  # -> Esse for é sempre fixo em 1 item.
                        actual_conversation["Mensagem"][agente_name] = agente_response

            actual_conversation["Mensagem"][self.agent_name] = agent_response
            actual_conversation["ChamouAgentes"] = called_delegated_agents

            self.history.append(actual_conversation)
            self.history = self.history[-self.MAX_HISTORY:]  # -> Mantendo apenas os N itens no histórico.
            self.storage.save_history(self.agent_name, actual_conversation)
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro duração a atualização do histórico: {e}')
