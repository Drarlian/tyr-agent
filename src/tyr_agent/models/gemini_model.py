from typing import List, Optional, Union
from google.genai import types
from tyr_agent.mixins.file_mixins import FileMixin
from tyr_agent.core.ai_config import configure_gemini


class GeminiModel(FileMixin):
    def __init__(self, model_name: str, temperature: Union[int, float] = 0.7, max_tokens: int = 1000, api_key: Optional[str] = None):
        self.client = configure_gemini(api_key)

        self.model_name = model_name

        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, user_input: str, files: Optional[List[dict]], prompt_build: str, history: Optional[List[dict]], use_history: bool) -> str:
        messages = self.__build_messages(user_input, history, use_history)

        # if files:
        #     files_formated: List[dict] = [self.convert_item_to_gemini_file(item["file"], item["file_name"]) for item in files]
        #     files_valid: List[dict] = [file for file in files_formated if file]
        #     prompt = [prompt] + files_valid[:10]

        if not messages:
            raise Exception("[ERROR] - Erro ao gerar o prompt do GEMINI.")

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=prompt_build,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            )
        )

        return response.text.strip()

    async def async_generate(self, user_input: str, files: Optional[List[dict]], prompt_build: str, history: Optional[List[dict]], use_history: bool) -> str:
        messages = self.__build_messages(user_input, history, use_history)

        if not messages:
            raise Exception("[ERROR] - Erro ao gerar o prompt do GEMINI.")

        final_response: str = ""
        for chunk in self.client.models.generate_content_stream(
                model=self.model_name,
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=prompt_build,
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
            ):
            final_response += chunk.text

        return final_response.strip()

    def __build_messages(self, user_input: str, history: Optional[List[dict]], use_history: bool):
        messages: List = []

        if use_history:
            for interaction in history:
                user_text = interaction["interaction"]["user"]

                messages.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=user_text)]
                    )
                )

                for agent_text in interaction["interaction"]["agent"]:
                    messages.append(
                        types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=agent_text)]
                        )
                    )

        messages.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_input)]
            )
        )

        return messages

    def __generate_prompt(self, user_input: str, prompt_build: str, history: Optional[List[dict]], use_history: bool, use_score: bool) -> str:
        try:
            if not use_history or not history:
                formatted_history = False
            else:
                def insert_score(score: Union[int, float, float]):
                    if use_score:
                        return f" - Score: {str(score) + '/5' if score is not None else 'Não consta'}"
                    else:
                        return ''

                formatted_history = "\n".join(
                    f"{item['timestamp']}{insert_score(item['score'])}\nUser: {item['interaction']['user']}\nAgent: {' | '.join(item['interaction']['agent'])}"
                    for item in history
                )

            first_prompt_template: str = f"{prompt_build}\n"

            if use_history and formatted_history:
                second_prompt_template: str = f"""
Você pode usar o histórico de conversas abaixo para responder perguntas relacionadas a interações anteriores com o usuário. 
Se o usuário perguntar sobre algo que já foi dito anteriormente, procure a informação no histórico.
{
'''\nCada resposta do agente no histórico pode conter uma nota de 0 a 5, representando o quanto ela foi útil para o usuário. 
Use essas notas como um indicativo da qualidade da resposta anterior. Priorize informações com notas mais altas e busque manter esse nível de qualidade em sua resposta atual.\n''' if use_score else ''
}
Histórico de Conversas:
{formatted_history if formatted_history else "Não Consta."}
"""
            else:
                second_prompt_template: str = ""

            third_prompt_template: str = f"""
Gere uma resposta natural para o usuário com base na mensagem atual:
{user_input}"""

            final_prompt_template: str = first_prompt_template + second_prompt_template + third_prompt_template

            return final_prompt_template
        except Exception as e:
            print(f'[ERROR] - Ocorreu um erro durante a geração do prompt: {e}')
            return ""
