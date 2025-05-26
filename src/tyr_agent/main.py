from tyr_agent import SimpleAgent, ComplexAgent, configure_gemini
import google.generativeai as genai
from typing import List

configure_gemini()
# agent1 = SimpleAgent(
#     prompt_build="Você é um agente reponsável apenas por informar os usuários se determinadas empresas da bolsa de valores são boas ou não para se investir.",
#     agent_name="NewFinanceAgent",
#     model=genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
# )
#
# agent1.chat("Você acha que WEG é uma boa empresa para se investir? Estou na duvida se devo ou não comprar ações dessa empresa.", streaming=True)


def somar(nums: List[float]) -> float:
    return sum(nums)


def subtrair(nums: List[float]) -> float:
    return 0


agent2 = ComplexAgent(
    prompt_build="Você é um agente responsável apenas por realizar calculos matemáticos.",
    agent_name="MathAgent",
    model=genai.GenerativeModel('gemini-2.5-flash-preview-04-17'),
    functions={"somar": somar, "subtrair": subtrair}
)

agent2.chat_with_functions("Me diga quanto é 10+14+20 e quanto é 19-7-4", streaming=True)
