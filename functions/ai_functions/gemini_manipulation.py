import time
import google.generativeai as genai
from typing import List, Optional
from functions.ai_functions.history_storage import HistoryStorage
from datetime import datetime
from functions.ai_functions.gemini_config import configure_gemini  # Configurando a conexão com Gemini.

# genai.configure(api_key=GEMINI_KEY)
# basic_model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
# real_time_model = genai.GenerativeModel("gemini-1.5-flash")  # -> Modelo com suporte a streaming.


class GeminiAgent:
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


def check_models():
    models = genai.list_models()
    for model in models:
        print(model)


if __name__ == '__main__':
    configure_gemini()
    model_test = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    weather_agent = GeminiAgent("Você é um agente responsável por fornecer apenas informações sobre o clima.", "WeatherAgent", model_test)
    teste = weather_agent.chat("Me fale sobre o clima de Miami atualmente.", True)
    print('-' * 30)
    print(teste)
    print(weather_agent.historic)
