def configure_gemini(api_key: str | None = None):
    import os
    from dotenv import load_dotenv
    from google import genai

    load_dotenv()
    key = api_key or os.getenv("GEMINI_KEY")
    if not key:
        raise EnvironmentError("API key não definida.")
    return genai.Client(api_key=key)


def configure_gpt(api_key: str | None = None):
    import os
    from openai import OpenAI
    from dotenv import load_dotenv

    load_dotenv()
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError("OPENAI_API_KEY não definida.")
    return OpenAI(api_key=key)
