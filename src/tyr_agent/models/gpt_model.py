from openai import OpenAI
from typing import Optional, Union, Callable, List, Dict, Any
from tyr_agent.core.ai_config import configure_gpt
from tyr_agent.mixins.gpt_file_mixins import GPTFileMixin
from tyr_agent.utils.gpt_function_format_utils import to_openai_tool
import json


class GPTModel(GPTFileMixin):
    def __init__(self, model_name: str, temperature: Union[int, float] = 0.4, max_tokens: int = 600, effort: str = "medium", api_key: Optional[str] = None):
        self.client: OpenAI = configure_gpt(api_key)

        if model_name == "economy":
            self.model_name = "gpt-3.5-turbo"
        elif model_name == "quality":
            self.model_name = "gpt-4o"
        else:
            self.model_name = model_name

        if effort not in ["low", "medium", "high"]:
            self.effort = "medium"

        self.temperature = temperature
        self.max_tokens = max_tokens
        self.effort = effort

    def generate(self, prompt_build: str, user_input: str, files: Optional[List[dict]], history: Optional[List[dict]], use_history: bool) -> str:
        messages = self.__create_messages(prompt_build, user_input, files, history, use_history)

        if self.model_name == 'gpt-5':
            response = self.client.responses.create(
                model="gpt-5",
                reasoning={"effort": self.effort},
                max_output_tokens=self.max_tokens,
                input=messages,
            )

            return response.output_text
        else:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False
            )

            return response.choices[0].message.content.strip()

    async def async_generate(self, prompt_build: str, user_input: str, files: Optional[List[dict]], history: Optional[List[dict]], use_history: bool) -> str:
        pass

    def generate_with_functions(self, prompt_build: str, user_input: str, files: Optional[List[dict]], history: Optional[List[dict]], use_history: bool, functions: Optional[List[Callable]], final_prompt: Optional[str]):
        messages = self.__create_messages(prompt_build, user_input, files, history, use_history)

        # Criando um array com as funções no formato que o GPT precisa:
        tools = []
        for f in functions:
            tools.append(to_openai_tool(f))

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=False,
            tools=tools if tools else None
        )

        # Pegando as funções chamadas pelo modelo:
        calls = response.choices[0].message.tool_calls

        # Validando se teve alguma chamada de função:
        if not calls:
            return response.choices[0].message.content.strip()  # Nenhuma função chamada, retorna direto

        new_messages = self.__execute_functions(calls, messages, functions)

        # Alterando o prompt "system" das mensagens pra o prompt especial definido na inicialização do agente:
        if final_prompt:
            new_messages[0]["content"] = final_prompt

        # Parte 5 - Segunda chamada: modelo continua raciocínio com base na resposta da função
        response_answer_functions = self.client.chat.completions.create(
            model=self.model_name,
            messages=new_messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=False,
        )

        return response_answer_functions.choices[0].message.content.strip()

    def __create_messages(self, prompt_build, user_input: str, files: Optional[List[dict]], history: Optional[List[dict]], use_history: bool) -> List[Any]:
        messages = self.__build_messages(prompt_build, user_input, history, use_history)

        if files:
            files_formated = [self.convert_item_to_gpt_model(item["file"], item["file_name"]) for item in files]
            files_valid = [{"type": "image_url", "image_url": {"url": file}} for file in files_formated if file]

            # Adicionando os arquivos identificados dentro da pergunta atual do usuário:
            if files_valid:
                messages[-1] = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_input},
                        *files_valid[:10]
                    ]
                }

        if not messages:
            raise Exception("[ERROR] - Erro ao gerar o prompt do GPT.")

        return messages

    def __build_messages(self, prompt_build: str, user_input: str, history: Optional[List[dict]], use_history: bool) -> List[Any]:
        messages: List[dict] = [{"role": "system", "content": prompt_build}]

        if history and use_history:
            for interaction in history:
                user_text = interaction["interaction"]["user"]

                messages.append({"role": "user", "content": user_text})

                for agent_text in interaction["interaction"]["agent"]:
                    messages.append({"role": "assistant", "content": agent_text})

        messages.append({"role": "user", "content": user_input})

        return messages

    def __execute_functions(self, calls, messages, functions: List[Callable]):
        # Parte 1: Criando um dicionário com o nome das funções e as funções:
        dict_functions: Dict[str, Callable] = {fn.__name__: fn for fn in functions}

        # Parte 2: Adicionando a mensagem do GPT solicitando a execução das funções no histórico:
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [call.model_dump() for call in calls]
        })

        # Parte 3: Executando as funções solicitadas pelo GPT:
        for call in calls:
            fn = dict_functions.get(call.function.name)
            if fn is None:
                raise Exception(f"[ERROR] - Função '{call.name}' não encontrada.")
            try:
                result = fn(**json.loads(call.function.arguments))
            except Exception as e:
                result = {"error": "Ocorreu um erro durante a execução da função!"}

            # Parte 4: Adicionando a resposta da função executada ao histórico de mensagens:
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)})

        return messages
