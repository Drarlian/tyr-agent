import os
import time
import google.generativeai as genai
from dotenv import load_dotenv
from typing import List, Optional
from functions.ai_functions.history_storage import HistoryStorage

load_dotenv()

GEMINI_KEY = os.getenv('GEMINI_KEY')

genai.configure(api_key=GEMINI_KEY)
basic_model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
real_time_model = genai.GenerativeModel("gemini-1.5-flash")  # -> Modelo com suporte a streaming.

# PROMPT_TEMPLATE = """
# {role}
#
# Histórico:
# {history}
#
# Mensagem atual:
# {current}
# """

class GeminiAgent:
    def __init__(self, prompt_build: str, agent_name: str, is_real_time_model: bool = False, storage: Optional[HistoryStorage] = None):
        self.is_real_time_model: bool = is_real_time_model
        self.prompt_build: str = prompt_build
        self.agent_name: str = agent_name
        self.storage: HistoryStorage = storage or HistoryStorage()
        self.historic: List[str] = self.storage.load_history(agent_name)

        if is_real_time_model:
            self.agent_model: genai.GenerativeModel = real_time_model
        else:
            self.agent_model: genai.GenerativeModel = basic_model

    def chat(self, user_input: str, streaming: bool = False) -> str | None:
        prompt = self.generate_prompt(user_input)

        try:
            if streaming:
                print("🧠 Gemini está digitando:\n")
                response = self.agent_model.generate_content(prompt, stream=True)
                for chunk in response:
                    print(chunk.text, end='', flush=True)
                    time.sleep(0.04)  # -> "Efeito" de digitando.
                print("\n\n✅ Fim da resposta.")
                self.update_historic(user_input, response.text)
                return response.text
            else:
                response = self.agent_model.generate_content(prompt, stream=True)
                response.resolve()
                self.update_historic(user_input, response.text)
                return response.text

        except Exception as e:
            print(f"❌ Erro: {e}")
            return None

    def update_historic(self, user_input: str, agent_response: str):
        self.historic.append(f"Usuário: {user_input}")
        self.historic.append(f"{self.agent_name}: {agent_response}")
        self.storage.save_history(self.agent_name, self.historic)

    def generate_prompt(self, promp_text: str) -> str:
        # return PROMPT_TEMPLATE.format(
        #     role=self.prompt_build,
        #     history=' | '.join(self.historic) if self.historic else 'Não consta.',
        #     current=promp_text
        # )

        return f"""
        {self.prompt_build}

        Interaja com o usuário baseado no histórico de mensagens abaixo.
        Responda a mensagem atual do usuário.
        {' | '.join(self.historic[:10]) if len(self.historic) > 0 else 'Não consta.'}

        Mensagem atual:
        {promp_text}
        """


def check_models():
    models = genai.list_models()
    for model in models:
        print(model)


if __name__ == '__main__':
    storage = HistoryStorage()
    weather_agent = GeminiAgent("Você é um agente responsável por fornecer apenas informações sobre o clima.", "WeatherAgent", False, storage)
    teste = weather_agent.chat("Me fale sobre o clima de Roma dos proximos 3 dias.", True)
    print('-' * 30)
    # print(teste)
    print(weather_agent.historic)
