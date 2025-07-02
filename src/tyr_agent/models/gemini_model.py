from typing import List, Optional, Union, Callable, Dict, Any
from google.genai import types
from tyr_agent.mixins.gemini_file_mixins import GeminiFileMixin
from tyr_agent.core.ai_config import configure_gemini


class GeminiModel(GeminiFileMixin):
    def __init__(self, model_name: str, temperature: Union[int, float] = 0.7, max_tokens: int = 1000, api_key: Optional[str] = None):
        self.client = configure_gemini(api_key)

        self.model_name = model_name

        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, user_input: str, files: Optional[List[dict]], prompt_build: str, history: Optional[List[dict]], use_history: bool) -> str:
        messages = self.__create_messages(user_input, files, history, use_history)

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
        messages = self.__create_messages(user_input, files, history, use_history)

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

    def generate_with_functions(self, user_input: str, files: Optional[List[dict]], prompt_build: str, history: Optional[List[dict]], use_history: bool, functions: Optional[List[Callable]], final_prompt: Optional[str]):
        messages = self.__create_messages(user_input, files, history, use_history)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=messages,
            config=types.GenerateContentConfig(
                system_instruction=prompt_build,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
                tools=functions if functions else None,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            ),
        )

        # Pegando as funções chamadas pelo modelo:
        calls = response.function_calls

        # Validando se teve alguma chamada de função:
        if not calls:
            return response.text.strip()  # Nenhuma função chamada, retorna direto

        tool_content = self.__execute_functions(calls, functions)

        # Parte 5 - Segunda chamada: modelo continua raciocínio com base na resposta da função
        final_response = self.client.models.generate_content(
            model=self.model_name,
            contents=[
                *messages,
                response.candidates[0].content,  # chamada da função pelo modelo
                tool_content  # resposta da função
            ],
            config=types.GenerateContentConfig(
                system_instruction=final_prompt if final_prompt is not None else prompt_build,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature
            ),
        )

        return final_response.text.strip()

    def __create_messages(self, user_input: str, files: Optional[List[dict]], history: Optional[List[dict]], use_history: bool) -> List[Any]:
        messages = self.__build_messages(user_input, history, use_history)

        if files:
            files_formated = [self.convert_item_to_gemini_model(item["file"], item["file_name"]) for item in files]
            files_valid = [file for file in files_formated if file]

            # Adicionando os arquivos identificados dentro do parts da pergunta atual do usuário:
            if files_valid:
                messages[-1].parts.extend(files_valid[:10])

        if not messages:
            raise Exception("[ERROR] - Erro ao gerar o prompt do GEMINI.")

        return messages

    def __build_messages(self, user_input: str, history: Optional[List[dict]], use_history: bool):
        messages: List = []

        if history and use_history:
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

    def __execute_functions(self, calls, functions: List[Callable]):
        # Parte 1: Criando um dicionário com o nome das funções e as funções:
        dict_functions: Dict[str, Callable] = {fn.__name__: fn for fn in functions}

        # Parte 2:
        tool_parts: list = []
        for call in calls:
            fn = dict_functions.get(call.name)
            if fn is None:
                raise Exception(f"[ERROR] - Função '{call.name}' não encontrada.")

            try:
                result = fn(**call.args)
            except Exception as e:
                result = {"error": "Ocorreu um erro durante a execução da função!"}

            part = types.Part.from_function_response(
                name=call.name,
                response={"result": result}
            )
            tool_parts.append(part)

        # Parte 3 - Cria o conteúdo do resultado das funções:
        tool_content = types.Content(role="tool", parts=tool_parts)

        return tool_content
