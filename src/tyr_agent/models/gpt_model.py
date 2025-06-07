# tyr_agent/models/gpt_model.py

import openai
from typing import Optional
from typing import List


class GPTModel:
    def __init__(self, model_name: str, temperature: Optional[int, float] = 0.7, max_tokens: int = 1000):
        self.model_name = model_name
        self.temperature = temperature
        self._max_tokens = max_tokens

    def generate(self, prompt_build: str, user_input: str, history: Optional[List[dict]]) -> str:
        messages = self.__build_messages(prompt_build, user_input, history)

        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self._max_tokens,
            stream=False
        )

        return response.choices[0].message.content.strip()

    async def async_generate(self, prompt_build: str, user_input: str, history: Optional[List[dict]]) -> str:
        pass

    def __build_messages (self, prompt_build: str, user_input: str, history: Optional[List[dict]]) -> List[dict]:
        messages: List[dict] = [{"role": "system", "content": prompt_build}]

        if history is not None:
            for interaction in history:
                messages.append({"role": "user", "content": interaction["interaction"]["user"]})
                messages.append({"role": "assistant", "content": interaction["interaction"]["agent"]})

        messages.append({"role": "user", "content": user_input})

        return messages
