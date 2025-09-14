# 🤖 Tyr Agent

[![PyPI version](https://badge.fury.io/py/tyr-agent.svg)](https://pypi.org/project/tyr-agent/)
[![Python version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

TyrAgent é uma biblioteca para criação de agentes inteligentes com histórico, function-calling, suporte a arquivos e orquestração de múltiplos agentes. Compatível com os modelos **Gemini** (Google) e **GPT** (OpenAI), com integração nativa para ambos.

- 💬 Conversas com ou sem `streaming`
- 🧠 `Memória` persistente de interações (por agente), com controle total de uso e armazenamento
- 📊 Sistema de `score` por interação para qualificar e filtrar o histórico
- ⚙️ Execução de funções Python com suporte a `function calling`
- 🧑🏻‍💼 `Orquestração` de múltiplos agentes com roteamento automático de mensagens
- 🖼️ Suporte a múltiplos tipos de `arquivo`
- 🧩 Estrutura modular e extensível

---

## 📦 Instalação via PyPI

```bash
pip install tyr-agent
```

> 🔐 É necessário definir as variáveis de ambiente:
> - `GEMINI_KEY` para uso com modelos Gemini
> - `OPENAI_API_KEY` para uso com modelos GPT (OpenAI)

---

## 💡 Exemplos de uso

### 📘 SimpleAgent

```python
from tyr_agent import SimpleAgent, GeminiModel, GPTModel
import asyncio

agent = SimpleAgent(
    prompt_build="Você é um agente especializado em ações brasileiras.",
    agent_name="FinanceAgent",
    model=GeminiModel("gemini-2.5-flash"),  # ou GPTModel("modelo_desejado")
    use_storage=True,
    use_history=True,
    use_score=True,
)

response = asyncio.run(agent.chat("Me fale sobre a WEGE3.", save_history=True))
print(response)
```

### ⚙️ ComplexAgent com funções

```python
from tyr_agent import ComplexAgent, GeminiModel, GPTModel
from typing import List
import asyncio

def somar(nums: List[float]) -> float: return sum(nums)
def subtrair(nums: List[float]) -> float: return nums[0] - sum(nums[1:])

agent = ComplexAgent(
    prompt_build="Você faz cálculos precisos com base nas funções disponíveis.",
    agent_name="MathAgent",
    model=GeminiModel("gemini-2.5-flash"),  # ou GPTModel("modelo_desejado")
    functions=[somar, subtrair],
    use_storage=True,
    use_history=True,
    use_score=True,
)

response = asyncio.run(agent.chat("Quanto é 14+18+24 e 18-6-2?", save_history=True))
print(response)
```

### 🧑🏻‍💼 ManagerAgent (Orquestrador)

```python
from tyr_agent import SimpleAgent, ComplexAgent, ManagerAgent, GPTModel, GeminiModel
import asyncio

def get_clima(cidade: str) -> str: return f"O clima na cidade {cidade} é de 25ºC e esta ensolarado."

finance_agent = SimpleAgent(
    prompt_build="Você é um agente especializado em ações brasileiras.",
    agent_name="FinanceAgent",
    model=GeminiModel("gemini-2.5-flash"),  # ou GPTModel("modelo_desejado")
    use_storage=True,
    use_history=True,
    use_score=True,
)

weather_agent = ComplexAgent(
    prompt_build="Você é um agente do clima.",
    agent_name="WeatherAgent",
    model=GPTModel("gpt-4o"),  # ou GeminiModel("modelo_desejado")
    functions=[get_clima],
)

manager = ManagerAgent(
    agent_name="Manager",
    model=GPTModel("quality"),
    agents=[finance_agent, weather_agent],
    use_history=True
)

response = asyncio.run(manager.chat("Quanto é 10+10? E o clima no Rio?", save_history=True))
print(response)
```

### 📎 Envio de arquivos

```python
from tyr_agent import SimpleAgent, GeminiModel, GPTModel
import asyncio

agent = SimpleAgent(
    prompt_build="Você é um agente especializado em leitura de documentos.",
    agent_name="FileAgent",
    model=GeminiModel("gemini-2.5-flash"),  # ou GPTModel("modelo_desejado")
    use_storage=True,
    use_history=True,
    use_score=True,
)

files_info = [
    {
        "file": "D:\\caminho\\para\\meu_arquivo1.png",  # Pode ser um path, base64 ou BytesIO
        "file_name": "Documento1.png"
    },
    {
        "file": "D:\\caminho\\para\\meu_arquivo2.png",  # Pode ser um path, base64 ou BytesIO
        "file_name": "Documento2.png"
    },
]

response = asyncio.run(agent.chat("Sobre o que é esses documentos?", save_history=True, files=files_info))
print(response)
```

---

## 🔧 Modelos disponíveis

- `GeminiModel(model_name: str, temperature=0.4, max_tokens=600)`
- `GPTModel(model_name: str, temperature=0.4, max_tokens=600)`
- `GPTModel("economy")` → usa `gpt-3.5-turbo`
- `GPTModel("quality")` → usa `gpt-4o`
- Ambos assumem as chaves das variáveis `GEMINI_KEY` ou `OPENAI_API_KEY` automaticamente.

---

## 🧠 Principais recursos

- `SimpleAgent`: Respostas simples com ou sem histórico
- `ComplexAgent`: Permite execução de funções e resposta final combinada
- `ManagerAgent`: Gerencia e delega perguntas entre múltiplos agentes
- Suporte completo a arquivos (path, base64, BytesIO)
- Sistema de notas (score 0 a 5) para filtrar interações úteis
- Histórico persistente e controlável por agente

---

## 📄 Licença

Este repositório está licenciado sob os termos da MIT License.

---

## 📬 Contato

Criado por **Witor Oliveira**  
🔗 [LinkedIn](https://www.linkedin.com/in/witoroliveira/)  
📫 [Contato por e-mail](mailto:witoredson@gmail.com)