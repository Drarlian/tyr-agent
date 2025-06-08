from typing import List, Optional, Union
import google.generativeai as genai
from tyr_agent.mixins.file_mixins import FileMixin
from tyr_agent.core.ai_config import configure_gemini


class GeminiModel(FileMixin):
    def __init__(self, model_name: str, api_key: Optional[str] = None):
        configure_gemini(api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate(self, user_input: str, files: Optional[List[dict]], prompt_build: str, history: Optional[List[dict]], use_history: bool, use_score: bool) -> str:
        prompt = self.__generate_prompt(user_input, prompt_build, history, use_history, use_score)

        if files:
            files_formated: List[dict] = [self.convert_item_to_gemini_file(item["file"], item["file_name"]) for item in files]
            files_valid: List[dict] = [file for file in files_formated if file]
            prompt = [prompt] + files_valid[:10]

        if not prompt:
            raise Exception("[ERROR] - Erro ao gerar o prompt do GEMINI.")

        response = self.model.generate_content(prompt, stream=True)
        response.resolve()
        return response.text.strip()

    async def async_generate(self, user_input: str, prompt_build: str, history: Optional[List[dict]], use_history: bool, use_score: bool) -> str:
        prompt = self.__generate_prompt(user_input, prompt_build, history, use_history, use_score)

        response = await self.model.generate_content_async(prompt, stream=True)
        await response.resolve()
        return response.text.strip()

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
