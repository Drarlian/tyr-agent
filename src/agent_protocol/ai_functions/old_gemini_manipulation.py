import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv('GEMINI_KEY')

genai.configure(api_key=GEMINI_KEY)
basic_model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
real_time_model = genai.GenerativeModel("gemini-1.5-flash")  # -> Modelo com suporte a streaming.


def generate_prompt(promp_text: str, historic: str = "Não consta.") -> str:
    return f"""
    Você é um agente responsável por auxiliar o usuário em suas duvidas sobre o clima, informações referente ao histórico dele sobre perguntas do clima e nada mais.
    Interaja com o usuário baseado no histórico de mensagens abaixo.
    Responda a mensagem atual do usuário.
    {historic}

    Mensagem atual:
    {promp_text}
    """


def basic_conversation(promp_text: str, historic: str) -> str:
    prompt = generate_prompt(promp_text, historic)

    # response = basic_model.generate_content(prompt)
    # return response.text

    response = basic_model.generate_content(prompt, stream=True)
    response.resolve()
    # Quando usamos o stream=True, a resposta (response) é um iterador de chunks, cada um com um pedaço do texto.
    # O .resolve() percorre todos esses chunks internamente, concatena os textos e gera o conteúdo final completo.
    # Usar stream=True com .resolve() é naturalmente mais rápido para se obter a resposta que o stream=False.
    # É mais rápido em todos os cenários.
    # • Tanto para conversa em tempo real (só é uma opção com o stream=True)
    # • Quanto para apenas entregar a resposta final.

    print('-' * 30)
    print(response)
    print('-' * 30)

    return response.text


def real_time_conversation(prompt: str):
    print("🧠 Gemini está digitando:\n")

    try:
        response = real_time_model.generate_content(generate_prompt(prompt), stream=True)

        for chunk in response:
            print(chunk.text, end='', flush=True)
            time.sleep(0.03)  # Só pra dar um efeito "digitando".

        print("\n\n✅ Fim da resposta.")

    except Exception as e:
        print(f"\n❌ Erro: {e}")


def check_models():
    models = genai.list_models()
    for model in models:
        print(model)


if __name__ == '__main__':
    test_historic = """
    Mensagem Usuário: Olá eu me chamo Teste! 

    Resposta do agente anterior: Olá, Teste!
    Estou funcionando perfeitamente, obrigado por perguntar! 😊
    Prazer em te conhecer! Como posso te ajudar hoje?"))

    Mensagem Usuário: Queria saber como esta o clima em Paris

    Resposta do agente anterior: 
    Certo, Teste! Posso te informar sobre o clima em Paris agora.

    Em Paris, a temperatura é de aproximadamente 15°C, com céu parcialmente nublado. A sensação térmica é similar. A umidade está em torno de 70% e o vento sopra fraco.
    """
    print(basic_conversation("Me diga como esta o clima nos lugares que eu costumo perguntar", test_historic))
