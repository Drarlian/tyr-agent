from openai import OpenAI
from typing import Optional, Union
from typing import List
from tyr_agent.core.ai_config import configure_gpt


class GPTModel:
    def __init__(self, model_name: str, temperature: Union[int, float] = 0.7, max_tokens: int = 1000, api_key: Optional[str] = None):
        self.client: OpenAI = configure_gpt(api_key)

        if model_name == "economy":
            self.model_name = "gpt-3.5-turbo"
        elif model_name == "quality":
            self.model_name = "gpt-4o"
        else:
            self.model_name = model_name

        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, user_input: str, files: Optional[List[dict]], prompt_build: str, history: Optional[List[dict]], use_history: bool) -> str:
        messages = self.__build_messages(prompt_build, user_input, history, use_history)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=False
        )

        return response.choices[0].message.content.strip()

    async def async_generate(self, prompt_build: str, files: Optional[List[dict]], user_input: str, history: Optional[List[dict]], use_history: bool) -> str:
        pass

    def __build_messages (self, prompt_build: str, user_input: str, history: Optional[List[dict]], use_history: bool) -> List[dict]:
        messages: List[dict] = [{"role": "system", "content": prompt_build}]

        if use_history:
            for interaction in history:
                user_text = interaction["interaction"]["user"]

                messages.append({"role": "user", "content": user_text})

                for agent_text in interaction["interaction"]["agent"]:
                    messages.append({"role": "assistant", "content": agent_text})

        messages.append({"role": "user", "content": user_input})

        return messages
