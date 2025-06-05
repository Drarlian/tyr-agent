# 🤖 Tyr Agent

[![PyPI version](https://badge.fury.io/py/tyr-agent.svg)](https://pypi.org/project/tyr-agent/)
[![Python version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

TyrAgent é uma biblioteca para criação de agentes inteligentes com histórico, function-calling, suporte a arquivos e orquestração de múltiplos agentes. Ideal para aplicações com modelos generativos como Gemini, GPT e similares.

- 💬 Conversas com ou sem `streaming`
- 🧠 `Memória` persistente de interações (por agente), com controle total de uso e armazenamento
- 📊 Sistema de `score` por interação para qualificar e filtrar o histórico
- ⚙️ Execução de funções python durante a conversa, com suporte a `function calling`
- 🧑🏻‍💼 `Orquestração` de múltiplos agentes com roteamento automático de mensagens
- 🖼️ Interpretação de múltiplos tipos de `arquivo`
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
│   ├── agent.py  # SimpleAgent, ComplexAgent e ManagerAgent
│   └── ai_config.py  # configure_gemini
└── storage/
    └── interaction_history.py  # InteractionHistory

```

---

## 💡 Exemplos de uso

### 📘 Criando um agente simples

```python
import asyncio
import google.generativeai as genai
from tyr_agent import SimpleAgent, configure_gemini

configure_gemini()
agent = SimpleAgent(
    prompt_build="Você é um assistente de clima.",
    agent_name="WeatherAgent",
    model=genai.GenerativeModel("gemini-2.5-flash-preview-04-17"),
    use_history=True,  # É um parâmetro opicional e pode ser True ou False.
    use_score=True,    # É um parâmetro opicional e pode ser True ou False.,
    score_average=3    # É um parâmetro opicional e pode variar de 0 a 5.,
)

# O parâmetro "save_history" também é opicional e pode ser True ou False.
response = asyncio.run(agent.chat("Qual o clima em Salvador?", save_history=True))
```

### ⚙️ Criando um agente com funções

```python
import asyncio
import google.generativeai as genai
from tyr_agent import ComplexAgent, configure_gemini

def somar(a: float, b: float): return a + b

def pegar_clima(cidade: str): return f"Clima em {cidade}: Ensolarado 28°C"

configure_gemini()
agent = ComplexAgent(
    prompt_build="Você pode fazer cálculos e responder sobre o clima.",
    agent_name="WeatherSumBot",
    model=genai.GenerativeModel("gemini-2.5-flash-preview-04-17"),
    functions={"somar": somar, "pegar_clima": pegar_clima},
    use_history=False,  # É um parâmetro opicional e pode ser True ou False.
    use_score=False,    # É um parâmetro opicional e pode ser True ou False.,
    score_average=1     # É um parâmetro opicional e pode variar de 0 a 5.,
)

# O parâmetro "save_history" também é opicional e pode ser True ou False.
response = asyncio.run(agent.chat("Me diga quanto é 10+5 e o clima de São Paulo", save_history=False))
```

### 🧑🏻‍💼 Criando um orquestrador de agentes

```python
import asyncio
import google.generativeai as genai
from tyr_agent import ManagerAgent, ComplexAgent, SimpleAgent, configure_gemini

configure_gemini()
model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")

weather_agent = SimpleAgent(
    prompt_build="Você é um assistente de clima.",
    agent_name="WeatherAgent",
    model=model
)

def somar(a: float, b: float): return a + b

def subtrair(a: float, b: float): return a - b

math_agent = ComplexAgent(
    prompt_build="Você pode fazer cálculos matemáticos.",
    agent_name="MathAgent",
    model=model,
    functions={"somar": somar, "subtrair": subtrair}
)

configure_gemini()
manager_agent = ManagerAgent(
    agent_name="ManagerAgent",
    model=model,
    agents={"weather": weather_agent, "math": math_agent},
    use_history=True,  # É um parâmetro opicional e pode ser True ou False.,
    use_score=True,    # É um parâmetro opicional e pode ser True ou False.,
    score_average=4    # É um parâmetro opicional e pode variar de 0 a 5.,

)

# O parâmetro "save_history" também é opicional e pode ser True ou False.
response = asyncio.run(manager_agent.chat("Me diga clima de São Paulo e quanto é 10+5", save_history=False))
```

---

## 🧠 Principais recursos

- `SimpleAgent`: Conversa com contexto e histórico;
- `ComplexAgent`: Capaz de sugerir e executar funções, processar os resultados e entregar uma resposta final;
- `ManagerAgent`: Orquestra múltiplos agentes e delega tarefas automaticamente;
- `InteractionHistory`: Armazena o histórico individual de cada agente em JSON;
- Suporte a múltiplos tipos de arquivo via path, base64 ou BytesIO;
- Sistema de score por interação (0 a 5) com média configurável (`score_average`) para decidir o que deve ou não ser utlizado no histórico;
- Histórico totalmente gerenciável com métodos para criar, remover, limpar ou apagar os dados persistidos;
- Estrutura modular e extensível para expansão futura (benchmark, visão computacional, execução de código etc.).

---

## 📄 Licença

Este repositório está licenciado sob os termos da MIT License.

---

## 📬 Contato

Criado por **Witor Oliveira**  
🔗 [LinkedIn](https://www.linkedin.com/in/witoroliveira/)  
📫 [Contato por e-mail](mailto:witoredson@gmail.com)