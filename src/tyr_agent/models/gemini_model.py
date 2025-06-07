# tyr_agent/models/gemini_model.py

import google.generativeai as genai


class GeminiModel:
    def __init__(self, model_name: str):
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str) -> str:
        response = self.model.generate_content(prompt, stream=True)
        response.resolve()
        return response.text.strip()

    async def async_generate(self, prompt: str) -> str:
        response = await self.model.generate_content_async(prompt, stream=True)
        await response.resolve()
        return response.text.strip()
