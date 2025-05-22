import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega a chave da API
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))

# Modelos a usar (tem que suportar os dois modos)
MODEL_ID = "gemini-1.5-flash"
model = genai.GenerativeModel(MODEL_ID)

# Prompt de teste
prompt = """
Quero que você me explique de forma detalhada como funciona o ciclo da água, incluindo evaporação, condensação, precipitação e infiltração. 
Por favor, seja didático como se estivesse explicando para um estudante do ensino fundamental.
"""


def benchmark_stream_false():
    print("🚫 Modo sem streaming (stream=False)")
    start = time.perf_counter()
    response = model.generate_content(prompt, stream=False)
    end = time.perf_counter()
    print(f"Tempo total: {end - start:.2f} segundos")
    print("-" * 30)
    print(response.text[:500] + "...")
    print("-" * 30)


def benchmark_stream_resolve():
    print("✅ Modo com streaming + resolve()")
    start = time.perf_counter()
    response = model.generate_content(prompt, stream=True)
    response.resolve()
    end = time.perf_counter()
    print(f"Tempo total: {end - start:.2f} segundos")
    print("-" * 30)
    print(response.text[:500] + "...")
    print("-" * 30)


if __name__ == "__main__":
    benchmark_stream_false()
    print("\n\n")
    benchmark_stream_resolve()

    """
    Resultado:
    
    🚫 Modo sem streaming (stream=False)
    Tempo total: 5.41 segundos
    ------------------------------
    Imagine a água como uma grande aventureira que viaja pelo mundo todo o tempo!  Essa viagem é chamada de **ciclo da água**, e é super importante para toda a vida na Terra.  Ele funciona como um círculo sem começo nem fim, com a água mudando de estado constantemente. Vamos acompanhar a aventura da água gota a gota:
    
    **1. Evaporação: A Água Vira Vapor!**
    
    O sol, nosso grande astro, esquenta a água dos rios, lagos, mares e até mesmo das poças d'água.  Quando o sol esquenta a água bastante, ela vira ...
    ------------------------------
    
    
    
    ✅ Modo com streaming + resolve()
    Tempo total: 4.63 segundos
    ------------------------------
    Imagine a Terra como uma grande bola azul e branca, cheia de água!  Essa água não fica parada no mesmo lugar o tempo todo. Ela viaja constantemente, subindo para o céu e voltando para a terra num ciclo incrível chamado **Ciclo da Água**.  É como um grande círculo mágico que nunca para!
    
    Vamos entender cada parte dessa viagem:
    
    **1. Evaporação:**  Imagine o sol brilhando forte em um lago, rio ou até mesmo uma poça d'água. O calor do sol faz com que a água se transforme em gás invisível, chamado *...
    """
