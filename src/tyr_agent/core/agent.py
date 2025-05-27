import json
import base64
import google.generativeai as genai
from typing import List, Dict, Optional, Callable, Union
from tyr_agent.entities.entities import ManagerCallManyAgents, AgentCallInfo
from tyr_agent.storage.interaction_history import InteractionHistory
from tyr_agent.core.ai_config import configure_gemini
from io import BytesIO
from PIL import Image, ImageFile


class SimpleAgent:
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: genai.GenerativeModel, storage: Optional[InteractionHistory] = None, max_history: int = 20):
        self.prompt_build: str = prompt_build
        self.agent_name: str = agent_name
        self.storage: InteractionHistory = storage or InteractionHistory(f"{agent_name.lower()}_history.json")
        self.historic: List[dict] = self.storage.load_history(agent_name)

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

    async def chat(self, user_input: str, streaming: bool = False, base64_files: Optional[List[str]] = None, print_messages: bool = False) -> Optional[str]:
        try:
            prompt = self.__generate_prompt(user_input)

            if not prompt:
                raise Exception("[ERROR] - Erro ao gerar o prompt.")

            if base64_files:
                files: List[ImageFile] = [self.convert_base64_to_image(b64) for b64 in base64_files]
                prompt = [prompt] + files[:10]

            response = await self.agent_model.generate_content_async(prompt, stream=True)
            await response.resolve()
            final_text: str= response.text.strip()
            self._update_historic(user_input, final_text)

            return final_text
        except Exception as e:
            print(f"❌ [SimpleAgent.chat] {type(e).__name__}: {e}")
            return None

    def __generate_prompt(self, prompt_text: str) -> str:
        try:
            formatted_history = "\n".join(
                f"{item['Data']} - Usuário: {item['Mensagem']['Usuario']}\n{self.agent_name}: {item['Mensagem'][self.agent_name]}"
                for item in self.historic
            )

            return self.PROMPT_TEMPLATE.format(
                role=self.prompt_build,
                history=formatted_history if self.historic else 'Não consta.',
                current=prompt_text
            )
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""

    def _update_historic(self, user_input: str, agent_response: str):
        try:
            actual_conversation = {
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Mensagem": {
                    "Usuario": user_input,
                    self.agent_name: agent_response,
                }
            }

            self.historic.append(actual_conversation)
            self.historic = self.historic[-self.MAX_HISTORY:]  # -> Mantendo apenas os N itens no histórico.
            self.storage.save_history(self.agent_name, actual_conversation)
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro duração a atualizaão do histórico: {e}')

    def convert_base64_to_image(self, base64_file: str) -> Optional[ImageFile]:
        try:
            if base64_file.startswith('data:image'):
                base64_file = base64_file.split(',')[1]

            bytes_image = base64.b64decode(base64_file)
            buffer = BytesIO(bytes_image)
            image = Image.open(buffer)

            return image
        except Exception as e:
            print(f"[ERROR] - Erro ao converter base64 para imagem: {e}")
            return None


class ComplexAgent(SimpleAgent):
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: genai.GenerativeModel, functions: Optional[dict[str, Callable]] = None, storage: Optional[InteractionHistory] = None, max_history: int = 20):
        super().__init__(prompt_build, agent_name, model, storage, max_history)
        self.functions: dict[str, Callable] = functions or {}

        self.PROMPT_TEMPLATE = ""

    async def chat(self, user_input: str, streaming: bool = False, base64_files: Optional[List[str]] = None, print_messages: bool = False) -> str | None:
        # Primeira rodada:
        prompt = self.__generate_prompt_with_functions(user_input)

        if not prompt:
            raise Exception("[ERROR] - Erro ao gerar o prompt.")

        try:

            if base64_files:
                files: List[ImageFile] = [self.convert_base64_to_image(b64) for b64 in base64_files]
                prompt = [prompt] + files[:10]

            response = await self.agent_model.generate_content_async(prompt, stream=True)
            await response.resolve()
            response_text = response.text.strip()

            func_calls = self.__extract_function_calls(response_text)

            if not func_calls:
                self._update_historic(user_input, response_text)
                return response_text

            if print_messages:
                print(func_calls["mensagem_ao_usuario"])

            # Executa as múltiplas funções solicitadas:
            results = {}
            for call in func_calls["functions_to_execute"]:
                result = self.__execute_function(call)
                results[call['function_name']] = result

            # Criando o prompt final com o resultado da execução da função:
            return await self.__generate_and_execute_final_prompt(user_input, results)
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
            formatted_history = "\n".join(
                f"{item['Data']} - Usuário: {item["Mensagem"]['Usuario']}\n{self.agent_name}: {item["Mensagem"][self.agent_name]}"
                for item in self.historic
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

    async def __generate_and_execute_final_prompt(self, prompt_text: str, results: Dict[str, str]) -> str:
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

        self._update_historic(prompt_text, final_text)
        return final_text


class ManagerAgent:
    MAX_ALLOWED_HISTORY = 100

    def __init__(self, prompt_build: str, agent_name: str, model: genai.GenerativeModel, agents: Dict[str, Union[SimpleAgent, ComplexAgent]], storage: Optional[InteractionHistory] = None, max_history: int = 100):
        self.prompt_build: str = prompt_build
        self.agent_name: str = agent_name
        self.agents: Dict[str, Union[SimpleAgent, ComplexAgent]] = agents
        self.storage: InteractionHistory = storage or InteractionHistory(f"{agent_name.lower()}_history.json")
        self.historic: List[dict] = self.storage.load_history(agent_name)

        self.agent_model: genai.GenerativeModel = model

        self.MAX_HISTORY: int = min(max_history, self.MAX_ALLOWED_HISTORY)
        self.PROMPT_TEMPLATE: str = ""

    async def chat(self, user_input: str) -> Optional[str]:
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
                self.__update_historic(user_input, response_text, self.agent_name)
                return response_text

            # Encontrando os Agentes solicitados:
            delegated_agents = self.__find_correct_agents(extracted_agents)

            if len(delegated_agents) == 0:
                agentes_requisitados = extracted_agents if isinstance(extracted_agents, str) else json.dumps(extracted_agents, ensure_ascii=False)
                print(f"[ERRO] Nenhum dos agentes requisitados foi encontrado: {agentes_requisitados}")
                return None

            delegated_agents_name = " | ".join([agent["agent"].agent_name for agent in delegated_agents])
            self.__update_historic(user_input, "Direcionado ao(s) agente(s)", delegated_agents_name)

            response_delegated_agents = await self.__execute_agents_calls(delegated_agents)

            return await self.__generate_and_execute_final_prompt(prompt, response_delegated_agents)

        except Exception as e:
            print(f"[ERRO] Falha ao interpretar a resposta do manager: {e}")
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

    async def __execute_agents_calls(self, delegated_agents: List[AgentCallInfo]) -> List[str]:
        # agents_response: List[str] = []
        # for agent_info in delegated_agents:
        #     response = await agent_info["agent"].chat(agent_info["message"], streaming=True)
        #     agents_response.append(f"{agent_info["agent"].agent_name}: {response}")
        #     self.update_historic(agent_info["message"], response, agent_info["agent"].agent_name)

        # Execução paralela dos agentes:
        coroutines = [
            delegated_agent["agent"].chat(delegated_agent["message"], streaming=True)
            for delegated_agent in delegated_agents
        ]

        results = await asyncio.gather(*coroutines, return_exceptions=True)

        agents_response: List[str] = []

        for agent_info, result in zip(delegated_agents, results):
            agent_name = agent_info["agent"].agent_name

            if isinstance(result, Exception):
                print(f"[ERRO] Agente '{agent_name}' falhou: {type(result).__name__} - {result}")
                agents_response.append(f"{agent_name}: [Erro ao gerar resposta]")
            else:
                if isinstance(result, str):
                    self.__update_historic(agent_info["message"], result, agent_name)
                    agents_response.append(f"{agent_name}: {result}")

        return agents_response

    def __generate_prompt(self, prompt_text: str) -> str:
        try:
            formatted_history = "\n\n".join(
                f"{item['Data']} - Usuário: {item['Mensagem'].get('Usuario', '')}\n"
                + "\n".join(
                    f"{agent_name}: {resposta}"
                    for agent_name, resposta in item["Mensagem"].items()
                    if agent_name != "Usuario"
                )
                for item in self.historic
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

Abaixo está a descrição dos agentes disponíveis:

{formatted_agents}

O usuário fez a seguinte pergunta:

"{prompt_text}"

Sua tarefa é:
- Analisar a pergunta do usuário.
- Dividir a pergunta em partes, se necessário.
- Escolher o(s) agente(s) corretos para cada parte.
- Informar qual mensagem deve ser enviada a cada agente.

{call_agent_explanation}

**Importante:**
- Se a pergunta do usuário puder ser dividida entre vários agentes, crie um item para cada agente.
- Se apenas um agente for necessário, retorne o JSON contendo apenas um agente.
- Se nenhum agente for adequado, responda diretamente você mesmo com um texto comum (sem JSON).

Você pode usar o histórico de conversas abaixo para responder perguntas relacionadas a interações anteriores com o usuário. 
Se o usuário perguntar sobre algo que já foi dito anteriormente, procure a informação no histórico.

Histórico de Conversas:
{formatted_history if formatted_history else "Não Consta."}
            """

            return full_prompt
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""

    async def __generate_and_execute_final_prompt(self, prompt_text: str, agents_response: List[str]) -> str:
        try:
            combined = "\n".join(agents_response)
            prompt = f"""
Você é um agente gerente que tem sob sua responsabilidade alguns agentes especializados.

O usuário fez a seguinte pergunta:

"{prompt_text}"

Os seguintes agentes responderam individualmente:

{combined}

Com base nessas respostas, gere uma única resposta unificada e natural para o usuário.
        """
            response = await self.agent_model.generate_content_async(prompt, stream=True)
            await response.resolve()
            return response.text.strip()

        except Exception as e:
            print(f"[ERRO] - Falha ao gerar resposta final do Manager: {e}")
            return "\n".join(agents_response)

    def __update_historic(self, user_input: str, agent_response: str, agent_name: str):
        try:
            actual_conversation = {
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Mensagem": {
                    "Usuario": user_input,
                    agent_name: agent_response,
                }
            }

            self.historic.append(actual_conversation)
            self.historic = self.historic[-self.MAX_HISTORY:]  # -> Mantendo apenas os N itens no histórico.
            self.storage.save_history(self.agent_name, actual_conversation)
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro duração a atualizaão do histórico: {e}')


if __name__ == '__main__':
    import asyncio
    from datetime import datetime

    inicio = datetime.now()

    configure_gemini()
    model_test = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    weather_agent = SimpleAgent("Você é um agente responsável por fornecer apenas informações sobre o clima.", "WeatherAgent", model_test)
    # response_test = asyncio.run(weather_agent.chat("Qual o clima atualmente no São Paulo?"))
    # print(response_test)

    functions_test = {
        "sum_numbers": lambda nums: f"A soma de {nums} é igual a {sum(nums)}",
    }
    sum_agent = ComplexAgent("Você é um agente responsável por fornecer apenas informações de soma de números.", "SumAgent", model_test, functions_test)
    # response_test = asyncio.run(sum_agent.chat("Quanto é 10+20?"))
    # print(response_test)

    manager = ManagerAgent(
        prompt_build="",
        agent_name="ManagerAgent1",
        model=model_test,
        agents={"clima": weather_agent, "soma": sum_agent},
    )

    response_test = asyncio.run(manager.chat("Qual é a temperatura atual de Fortaleza? E quanto é 87+23?"))
    print(response_test)

    fim = datetime.now()

    print(f"Tempo Percorrido: {fim-inicio}")

    # Tempo Percorrido com pool: 0:00:09.265001 | Tempo Percorrido: 0:00:15.954875 | Tempo Percorrido: 0:00:10.745561
    # Tempo Percorrido sem pool: 0:00:14.454556 | Tempo Percorrido: 0:00:11.398759 | Tempo Percorrido: 0:00:12.940998
