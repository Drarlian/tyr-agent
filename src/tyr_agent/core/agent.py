import time
import json
import base64
import google.generativeai as genai
from typing import List, Dict, Optional, Callable, Union
from tyr_agent.storage.interaction_history import InteractionHistory
from datetime import datetime
from tyr_agent.core.ai_config import configure_gemini
from io import BytesIO
from PIL import Image, ImageFile
from tyr_agent.utils.image_utils import image_to_base64


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

    def chat(self, user_input: str, streaming: bool = False, base64_files: Optional[List[str]] = None) -> str | None:
        try:
            prompt = self.generate_prompt(user_input)

            if not prompt:
                raise Exception("[ERROR] - Erro ao gerar o prompt.")

            if base64_files:
                files: List[ImageFile] = [self.convert_base64_to_image(b64) for b64 in base64_files]
                prompt = [prompt] + files[:10]

            if streaming:
                print("🧠 Gemini está digitando:\n")
                response = self.agent_model.generate_content(prompt, stream=True)

                final_text: str = ""
                for chunk in response:
                    print(chunk.text, end='', flush=True)
                    final_text += chunk.text
                    time.sleep(0.04)  # -> "Efeito" de digitando.

                print("\n\n✅ Fim da resposta.")

                self.update_historic(user_input, final_text)
                return final_text
            else:
                response = self.agent_model.generate_content(prompt, stream=True)
                response.resolve()
                self.update_historic(user_input, response.text)
                return response.text
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None

    def update_historic(self, user_input: str, agent_response: str):
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

    def generate_prompt(self, promp_text: str) -> str:
        try:
            formatted_history = "\n".join(
                f"{item['Data']} - Usuário: {item['Mensagem']['Usuario']}\n{self.agent_name}: {item['Mensagem'][self.agent_name]}"
                for item in self.historic
            )

            return self.PROMPT_TEMPLATE.format(
                role=self.prompt_build,
                history=formatted_history if self.historic else 'Não consta.',
                current=promp_text
            )
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""


class ComplexAgent(SimpleAgent):
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: genai.GenerativeModel, functions: Optional[dict[str, Callable]] = None, storage: Optional[InteractionHistory] = None, max_history: int = 20):
        super().__init__(prompt_build, agent_name, model, storage, max_history)
        self.functions: dict[str, Callable] = functions or {}

        self.PROMPT_TEMPLATE = ""

    def chat_with_functions(self, user_input: str, streaming: bool = False, base64_files: Optional[List[str]] = None) -> str | None:
        return self.chat(user_input, streaming, base64_files)

    def chat(self, user_input: str, streaming: bool = False, base64_files: Optional[List[str]] = None) -> str | None:
        try:
            # Primeira rodada:
            prompt = self.__generate_prompt_with_functions(user_input)

            if not prompt:
                raise Exception("[ERROR] - Erro ao gerar o prompt.")

            if base64_files:
                files: List[ImageFile] = [self.convert_base64_to_image(b64) for b64 in base64_files]
                prompt = [prompt] + files[:10]

            response = self.agent_model.generate_content(prompt, stream=True)
            response.resolve()
            response_text = response.text.strip()

            func_calls = self.__extract_function_calls(response_text)

            if not func_calls:
                self.update_historic(user_input, response_text)
                return response_text

            print(func_calls["mensagem_ao_usuario"])

            # Executa múltiplas funções solicitadas
            results = {}
            for call in func_calls["functions_to_execute"]:
                result = self.__execute_function(call)
                results[call['function_name']] = result

            # Segunda rodada: prompt enriquecido com resultados
            enriched_prompt = f"""
            {self.prompt_build}
    
            O agente solicitou a execução das seguintes funções:
            {json.dumps(results, indent=2, ensure_ascii=False)}
    
            Mensagem original do usuário:
            {user_input}
    
            Agora gere uma resposta final ao usuário com base nos resultados das funções.
            """

            final_response = self.agent_model.generate_content(enriched_prompt, stream=streaming)

            if streaming:
                final_text = ""
                for chunk in final_response:
                    print(chunk.text, end="", flush=True)
                    final_text += chunk.text
                    time.sleep(0.04)
                self.update_historic(user_input, final_text)
                return final_text.strip()

            final_response.resolve()
            final_text = final_response.text.strip()
            self.update_historic(user_input, final_text)
            return final_text
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

    def __generate_prompt_with_functions(self, promp_text: str) -> str:
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
            {promp_text}
            """

            final_prompt_template = first_prompt_template + second_prompt_template + third_prompt_template

            return final_prompt_template
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""


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

    def chat(self, user_input: str) -> Optional[str]:
        # Gera o prompt com base no input e nos agentes disponíveis
        prompt = self.generate_prompt(user_input)

        try:
            response = self.agent_model.generate_content(prompt, stream=True)
            response.resolve()
            response_text = response.text.strip()

            agent_call = self.__extract_agent_call(response_text)

            if not agent_call:
                self.update_historic(user_input, response_text, self.agent_name)
                return response_text

            # Encontrando o Agente solicitado:
            agent, message = self.__find_correct_agent(agent_call)

            if agent is None:
                print(f"[ERRO] Agente '{agent_call.get('agent_to_call')}' não foi encontrado.")
                return None

            agent_response = agent.chat(message, streaming=True)

            self.update_historic(user_input, agent_response, agent.agent_name)
            return agent_response

        except Exception as e:
            print(f"[ERRO] Falha ao interpretar a resposta do manager: {e}")
            return None

    def __extract_agent_call(self, response_text: str) -> Union[Dict[str, str], None]:
        try:
            text_cleaned = (
                response_text.removeprefix("```json\n").removesuffix("\n```").replace("\n", "")
                .replace("`", "").replace("´", "").strip()
            )

            data = json.loads(text_cleaned)
            if isinstance(data, dict) and "agent_to_call" in data and "agent_message" in data:
                return data
            return None
        except json.JSONDecodeError:
            return None

    def __find_correct_agent(self, agent_call: Dict[str, str]) -> tuple[Union[SimpleAgent, ComplexAgent, None], str]:
        try:
            agent_name = agent_call.get("agent_to_call")
            message = agent_call.get("agent_message")

            if agent_name not in self.agents:
                raise Exception("Erro ao procurar o agente correspondente.")

            # Encontrando o Agente solicitado:
            return self.agents[agent_name], message
        except Exception as e:
            print(f"[ERROR] - Falha ao encontrar o agente responsável: {e}")
            return None, ""

    def update_historic(self, user_input: str, agent_response: str, agent_name: str):
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

    def generate_prompt(self, promp_text: str) -> str:
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

            formatted_agents = "\n".join(f"Nome do Agente: {agent_name} - Definição do Agente: {agent.prompt_build}" for agent_name, agent in self.agents.items())

            call_agent_explanation = """
Com base na descrição dos agentes, decida qual deles é o mais apropriado para responder esta pergunta.
Caso queira chamar um agente responda APENAS com um JSON no formato:

{
  "agent_to_call": "<nome_do_agente>",
  "agent_message": "<mensagem que deve ser enviada ao agente>"
}
            """

            full_prompt = f"""
Você é um agente gerente que tem sob sua responsabilidade os seguintes agentes especializados:

{formatted_agents}

O usuário enviou a seguinte pergunta:

"{promp_text}"

{call_agent_explanation}

Caso nenhum agente pareça corresponder a mensagem, responda você mesmo.

Você pode usar o histórico de conversas abaixo para responder perguntas relacionadas a interações anteriores com o usuário. 
Se o usuário perguntar sobre algo que já foi dito anteriormente, procure a informação no histórico.

Histórico de Conversas:
{formatted_history if formatted_history else "Não Consta."}
            """

            return full_prompt
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""


if __name__ == '__main__':
    configure_gemini()
    model_test = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    weather_agent = SimpleAgent("Você é um agente responsável por fornecer apenas informações sobre o clima.", "WeatherAgent", model_test)

    functions_test = {
        "sum_numbers": lambda nums: f"A soma de {nums} é igual a {sum(nums)}",
    }
    sum_agent  = ComplexAgent("Você é um agente responsável por fornecer apenas informações de soma de números.", "SumAgent", model_test, functions_test)

    manager = ManagerAgent(
        prompt_build="",
        agent_name="ManagerAgent1",
        model=model_test,
        agents={"clima": weather_agent, "soma": sum_agent},
    )

    response_test = manager.chat("Qual é a temperatura atual de São Paulo?")
    print(response_test)
