# 🤖 Tyr Agent

[![PyPI version](https://badge.fury.io/py/tyr-agent.svg)](https://pypi.org/project/tyr-agent/)
[![Python version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

TyrAgent é uma biblioteca para criação de agentes inteligentes com histórico, function-calling e suporte a arquivos. Ideal para aplicações com modelos generativos como o Gemini da Google.

- 💬 Conversas com ou sem streaming
- 🧠 Memória persistente de interações (por agente)
- ⚙️ Execução de múltiplas funções via JSON
- 🖼️ Interpretação de imagens base64
- 🧩 Estrutura modular e extensível

---

## 📦 Instalação via PyPI

```bash
  pip install tyr-agent
```

> 🔒 Lembre-se de configurar sua variável `GEMINI_KEY` no `.env`

---

## 🧩 Estrutura do projeto

```
tyr_agent/
├── core/
│   ├── agent.py  # SimpleAgent e ComplexAgent
│   └── ai_config.py  # configure_gemini
├── storage/
│   └── interaction_history.py  # InteractionHistory
└── utils/
   └── image_utils.py  # image_to_base64
```

---

## 💡 Exemplos de uso

### 📘 Criando um agente simples

```python
import google.generativeai as genai
from tyr_agent import SimpleAgent, configure_gemini

configure_gemini()
agent = SimpleAgent(
    prompt_build="Você é um assistente de clima.",
    agent_name="WeatherBot",
    model=genai.GenerativeModel("gemini-2.5-flash-preview-04-17")
)
response = agent.chat("Qual o clima em Salvador?", streaming=True)
```

### ⚙️ Criando um agente com funções

```python
import google.generativeai as genai
from tyr_agent import ComplexAgent, configure_gemini

def somar(a: float, b: float): return a + b

def pegar_clima(cidade: str): return f"Clima em {cidade}: Ensolarado 28°C"

configure_gemini()
agent = ComplexAgent(
    prompt_build="Você pode fazer cálculos e responder sobre o clima.",
    agent_name="WeatherSumBot",
    model=genai.GenerativeModel("gemini-2.5-flash-preview-04-17"),
    functions={"somar": somar, "pegar_clima": pegar_clima}
)

response = agent.chat_with_functions("Me diga quanto é 10+5 e o clima de São Paulo", streaming=True)
```

---

## 🧠 Principais recursos

- `SimpleAgent`: Conversa com contexto e histórico;
- `ComplexAgent`: Pode sugerir funções a serem chamadas, recebe resultados e finaliza a resposta;
- `InteractionHistory`: Armazena histórico por agente em JSON;
- Suporte a arquivos base64 e imagens;
- Modular para expansão com novas capacidades (benchmark, visão, execução, etc.).

---

## 📄 Licença

Este repositório está licenciado sob os termos da MIT License.

---

## 📬 Contato

Criado por **Witor Oliveira**  
🔗 [LinkedIn](https://www.linkedin.com/in/witoroliveira/)  
📫 [Contato por e-mail](mailto:witoredson@gmail.com)