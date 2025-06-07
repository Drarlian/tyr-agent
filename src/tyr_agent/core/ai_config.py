def configure_gemini(api_key: str | None = None):
    import os
    from google.generativeai import configure
    from dotenv import load_dotenv

    load_dotenv()
    key = api_key or os.getenv("GEMINI_KEY")
    if not key:
        raise EnvironmentError("API key não definida.")
    configure(api_key=key)


def configure_gpt(api_key: str | None = None):
    import os
    import openai
    from dotenv import load_dotenv

    load_dotenv()
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError("OPENAI_API_KEY não definida.")
    openai.api_key = key
