from functions.ai_functions.gemini_manipulation import basic_conversation, real_time_conversation

prompt_text = "Qual é o clima na cidade do Rio de Janeiro historicamente?"

response_ai_basic = basic_conversation(prompt_text, "Não consta.")
response_ai_real_time = real_time_conversation(prompt_text)

print(response_ai_basic)
print(response_ai_real_time)
