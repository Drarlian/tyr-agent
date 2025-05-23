import time
import json
import google.generativeai as genai
from typing import List, Optional, Callable
from functions.ai_functions.history_storage import HistoryStorage
from datetime import datetime
from functions.ai_functions.gemini_config import configure_gemini  # Configurando a conexão com Gemini.

# genai.configure(api_key=GEMINI_KEY)
# basic_model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
# real_time_model = genai.GenerativeModel("gemini-1.5-flash")  # -> Modelo com suporte a streaming.


class SimpleAgent:
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: genai.GenerativeModel, storage: Optional[HistoryStorage] = None, max_history: int = 20):
        self.prompt_build: str = prompt_build
        self.agent_name: str = agent_name
        self.storage: HistoryStorage = storage or HistoryStorage(f"{agent_name.lower()}_history.json")
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

    def chat(self, user_input: str, streaming: bool = False) -> str | None:
        prompt = self.generate_prompt(user_input)

        try:
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

    def generate_prompt(self, promp_text: str) -> str:
        formatted_history = "\n".join(
            f"{item['Data']} - Usuário: {item['Mensagem']['Usuario']}\n{self.agent_name}: {item['Mensagem'][self.agent_name]}"
            for item in self.historic
        )

        return self.PROMPT_TEMPLATE.format(
            role=self.prompt_build,
            history=formatted_history if self.historic else 'Não consta.',
            current=promp_text
        )


class ComplexAgent(SimpleAgent):
    MAX_ALLOWED_HISTORY = 20

    def __init__(self, prompt_build: str, agent_name: str, model: genai.GenerativeModel, functions: Optional[dict[str, Callable]], storage: Optional[HistoryStorage] = None, max_history: int = 20):
        super().__init__(prompt_build, agent_name, model, storage, max_history)
        self.functions: dict[str, Callable] = functions or {}

        self.PROMPT_TEMPLATE = """
        {role}

        Você tem acesso às seguintes funções que podem ser utilizadas para responder perguntas do usuário:
        {function_list}

        Sempre que identificar que precisa executar uma ou mais funções para responder corretamente, gere uma resposta no formato JSON no seguinte formato:
        {call_function_explanation}

        Você pode usar o histórico de conversas abaixo para responder perguntas relacionadas a interações anteriores com o usuário. 
        Se o usuário perguntar sobre algo que já foi dito anteriormente, procure a informação no histórico.

        Histórico de Conversas:
        {history}

        Mensagem atual:
        {current}
        """

    def chat_with_functions(self, user_input: str, streaming: bool = False) -> str | None:
        # Primeira rodada: input original
        prompt = self.__generate_prompt_with_functions(user_input)

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

    def __extract_function_calls(self, response_text: str) -> dict | None:
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
        formatted_history = "\n".join(
            f"{item['Data']} - Usuário: {item["Mensagem"]['Usuario']}\n{self.agent_name}: {item["Mensagem"][self.agent_name]}"
            for item in self.historic
        )

        function_list = "\n".join(
            f"- {name}({', '.join(f.__code__.co_varnames[:f.__code__.co_argcount])})" for name, f in
            self.functions.items())

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

        return self.PROMPT_TEMPLATE.format(
            role=self.prompt_build,
            function_list=function_list,
            call_function_explanation= call_function_explanation,
            history=formatted_history if self.historic else 'Não consta.',
            current=promp_text
        )


def check_models():
    models = genai.list_models()
    for model in models:
        print(model)


# Exemplo de uso das funções
def somar(a: float, b: float) -> float:
    return a + b


def pegar_clima(cidade: str) -> str:
    return f"Clima em {cidade}: Ensolarado 28°C"


if __name__ == '__main__':
    configure_gemini()
    model_test = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    # weather_agent = SimpleAgent("Você é um agente responsável por fornecer apenas informações sobre o clima.", "WeatherAgent", model_test)
    # teste = weather_agent.chat("Me fale sobre o clima de Miami atualmente.", True)
    # print('-' * 30)
    # print(teste)
    # print(weather_agent.historic)

    functions_test = {
        "pegar_clima": pegar_clima,
        "somar": somar
    }
    test_complext = ComplexAgent("Você é um agente responsável por fornecer apenas informações sobre o clima e sobre soma de numeros.", "WeatherSumAgent", model_test, functions_test)
    test_response = test_complext.chat_with_functions("Me fale quais foram as ultimas somas que eu pedi para voce fazer para mim.", True)
    print()
    print('-' * 30)
    print(test_response)
    print('-' * 30)
    print(test_complext.historic)
