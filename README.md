# 🤖 Agent Protocol

Agente inteligente baseado em Gemini, com suporte a:

- Respostas conversacionais com ou sem streaming;
- Memória de interações (histórico persistente por agente);
- Execução de funções dinâmicas via JSON (function-calling);
- Interpretação de imagens (base64);
- Modularização para uso como biblioteca privada.

---

## 🧩 Estrutura do projeto

```
agent-project/
├── .env
├── pyproject.toml
├── requirements.txt
├── src/
│   └── agent_protocol/
│       ├── __init__.py
│       ├── ai_functions/
│       │   ├── gemini_config.py
│       │   └── gemini_manipulation.py  # SimpleAgent e ComplexAgent
│       ├── storage_functions/
│       │   └── history_storage.py  # HistoryStorage
│       └── utilities_functions/
│           └── convert_image_to_base64.py
```

---

## 🚀 Como usar

### 1. Instalação (modo dev)

```bash
  pip install -e .
```

### 2. Defina sua chave no `.env`

```
GEMINI_KEY=your-key-here
```

---

## 💡 Exemplos de uso

### 📘 Criando um agente simples

```python
import google.generativeai as genai
from agent_protocol.ai_functions.gemini_manipulation import SimpleAgent
from agent_protocol.ai_functions.gemini_config import configure_gemini

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
from agent_protocol.ai_functions.gemini_manipulation import ComplexAgent

def somar(a: float, b: float): return a + b

def pegar_clima(cidade: str): return f"Clima em {cidade}: Ensolarado 28°C"

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
- `HistoryStorage`: Armazena histórico por agente em JSON;
- Suporte a arquivos base64 e imagens;
- Modular para expansão com novas capacidades (benchmark, visão, execução, etc.).

---

## 🔐 Distribuição como pacote privado

Este projeto segue estrutura para instalação via `pip` diretamente de repositório GitHub:

```bash
  pip install git+https://<TOKEN>@github.com/Drarlian/agent-protocol.git
```

---

## 📄 Licença

Este repositório está licenciado sob os termos da MIT License.
