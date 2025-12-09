# 📦 CHANGELOG

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue as convenções do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/), e este projeto adota o versionamento semântico.

---

## [1.0.4] - 2025-12-09

### Adicionado
- Atualização das classes `GPTModel` e `GPTFileMixin`, permitindo o recebimento e processamento de arquivos `.pdf`.

### Correções
- Corrigido o uso fixo do modelo `gpt-5` em todos os usos da classe `SimpleAgent` que utilizavam o método `generate` da classe `GPTModel`.

---

## [1.0.3] - 2025-11-18

### Adicionado
- Novo parâmetro opcional `response_template` na classe `GPTModel`, permitindo definir um template de resposta diretamente via API da OpenAI (`responses`).
- O campo aceita instâncias de `ResponseTextConfigParam` (`openai.types.responses`), utilizando o parâmetro `text` conforme previsto na especificação oficial da OpenAI para resposta estruturada.

---

## [1.0.2] - 2025-09-15

### Adicionado
- Adicionada a lógica de `reasoning` e `effort` também no `ComplexAgent` ao utilizar o `GPTModel`, garantindo paridade com o comportamento do `SimpleAgent`.

### Correções
- Corrigida uma lógica interna no `ComplexAgent` com uso do `GPTModel`, que em alguns casos gerava falhas ao lidar com interações que não envolviam execução de função.

---

## [1.0.1] - 2025-09-14

### Adicionado
- Suporte aprimorado à OpenAI com compatibilidade para modelos mais recentes, como `gpt-5` e variantes futuras.
- Atualização da lógica de execução de funções nos modelos `GPTModel` e `GeminiModel`, permitindo que os agentes identifiquem e executem funções assíncronas (`async def`) de forma nativa.

### Alterado
- Otimização na comunicação com a API da OpenAI, melhorando a compatibilidade e estabilidade em modelos avançados.

---

## [1.0.0] - 2025-07-20

### Adicionado
- Introduzida a lógica de **modelos desacoplados**, com as classes `GeminiModel` e `GPTModel`, permitindo que os agentes funcionem com **Gemini** ou **GPT (OpenAI)**.
- Suporte nativo a parâmetros de configuração dos modelos:
  - `temperature` (padrão: `0.4`)
  - `max_tokens` (padrão: `600`)
- Nova lógica de histórico e chamada de funções, agora utilizando estruturas nativas dos modelos (ex.: `roles`, `parts`, `tool_calls`, `tool_parts`), proporcionando respostas mais precisas e uso reduzido de tokens.
- Variáveis de ambiente suportadas para configuração automática:
  - `GEMINI_KEY` para modelos Gemini.
  - `OPENAI_API_KEY` para modelos OpenAI (GPT).
- Criação de facilitadores no `GPTModel`:
  - Nome `"economy"` seleciona automaticamente o modelo `gpt-3.5-turbo`.
  - Nome `"quality"` seleciona automaticamente o modelo `gpt-4o`.
- Diversos métodos utilitários adicionados para controle avançado de:
  - Histórico
  - Armazenamento
  - Execuções de função
  - Prompt pós-execução
- Nova forma simplificada de passar funções para os agentes: basta fornecer uma lista de funções puras (sem necessidade de dicionário com `name`).

### Alterado
- **Substituição completa da biblioteca `google-generativeai` pela `google-genai`**, a nova SDK oficial do Google.
- **Refatoração da estrutura do arquivo `.json` de histórico**, adaptando o formato para compatibilidade com as estruturas nativas dos modelos (`Content`, `Part`, etc).
- Os agentes `SimpleAgent`, `ComplexAgent` e `ManagerAgent` agora utilizam as novas classes de modelo, com configuração encapsulada. O uso de `configure_gemini()` tornou-se obsoleto.
- Remoção dos prompts massivos antigos do `SimpleAgent` e `ComplexAgent`, que lidavam com histórico e funções de forma manual.
- Refatoração completa do prompt do `ManagerAgent`, reduzido de **743 tokens para 336 tokens**, com ganhos significativos em eficiência e clareza.

### Correções
- Correções e ajustes gerais na comunicação dos agentes com os modelos, otimizando consumo de tokens e legibilidade das interações.
- Simplificação e padronização interna de diversas estruturas de código.

Esta é a primeira versão **estável** e **modular** do Tyr Agent. Um marco importante no amadurecimento da biblioteca como ferramenta flexível, extensível e pronta para múltiplos modelos.

---

## [0.0.6] - 2025-06-05

### Adicionado
- Introduzido o conceito de `score` nas interações armazenadas no histórico dos agentes.
- Novos parâmetros na criação dos agentes:
  - `use_score`: define se o histórico deve ser filtrado por score (padrão: `True`).
  - `score_average`: valor mínimo (de 0 a 5) para que uma interação seja utilizada no histórico do agente (padrão: `3`).
- Nova propriedade `score` atribuída às interações. Inicialmente `None`, pode ser atualizada com avaliação posterior.
- Novos métodos utilitários adicionados aos agentes (`SimpleAgent`, `ComplexAgent`, `ManagerAgent`) para gerenciar avaliações:
  - `rate_interaction()` – avalia uma interação já registrada.
  - `delete_interaction()` – remove manualmente uma interação específica do histórico.
  - `get_score_by_id()` – retorna o score de uma interação específica.
  - `get_average_score()` – calcula a média dos scores avaliados.
  - `get_all_scores()` – retorna todos os scores registrados pelo agente.

### Alterado
- Otimização dos prompts internos dos agentes (`SimpleAgent`, `ComplexAgent`, `ManagerAgent`) para maior clareza, menor consumo de tokens e melhor entendimento do histórico.

### Correções
- Pequenos bugs corrigidos relacionados à lógica de armazenamento e leitura do histórico.

Agradecimento especial ao **Kayky Rodrigues** pela sugestão do sistema de avaliação por score, que agora faz parte da lógica central dos agentes.

---

## [0.0.5] - 2025-06-03

### Adicionado
- Nova flag `use_history` na criação dos agentes, permitindo definir se o histórico será considerado durante a execução.
- Nova flag `save_history` no método `.chat()` dos agentes, permitindo controle por interação sobre o salvamento do histórico.
- Novos métodos utilitários adicionados a todos os agentes (`SimpleAgent`, `ComplexAgent`, `ManagerAgent`) para controle total do histórico:
  - `create_agent_history()` – conecta ou cria um histórico para o agente.
  - `remove_agent_history()` – desconecta o histórico da instância atual.
  - `clear_agent_history()` – limpa o histórico carregado (em memória).
  - `clear_agent_storage()` – remove o conteúdo do arquivo físico do histórico.

### Alterado
- Reformulação completa do formato de histórico para os agentes `SimpleAgent`, `ComplexAgent` e `ManagerAgent`, com dados mais objetivos, padronizados e leves.
- O `ManagerAgent` teve sua estrutura de histórico otimizada, eliminando redundância e reduzindo o uso de espaço.
- Prompts internos otimizados para maior clareza e menor consumo de tokens, resultando em respostas mais fluídas e consistentes.

### Correções
- Correção de pequenos bugs relacionados ao histórico e consistência de respostas.
- Ajustes pontuais de performance e simplificação de trechos de código.

---

## [0.0.4] - 2025-05-29

### Adicionado
- Suporte expandido para diferentes tipos de arquivos além de imagens JPG, JPEG e PNG. Agora os agentes `SimpleAgent` e `ComplexAgent` também podem receber e processar arquivos como PDF, TXT e outros formatos compatíveis.
- Novas formas de envio de arquivos adicionadas: agora é possível fornecer arquivos via **path**, **base64** ou **BytesIO**.
- Criada a classe `FileMixin` em `mixins/file_mixins.py` para padronizar e reutilizar a lógica de leitura de arquivos entre os agentes.

---

## [0.0.3] - 2025-05-28

### Correções
- Corrigida a ausência de uma importação obrigatória no módulo `agent.py`, que impedia o registro correto do histórico em `SimpleAgent`, `ComplexAgent` e `ManagerAgent`.

---

## [0.0.2] - 2025-05-26

### Adicionado
- Criação do `ManagerAgent`: responsável por orquestrar múltiplos agentes simultaneamente, com suporte a roteamento dinâmico de mensagens.
- Diretório `entities/` com `entities.py`: adicionado para centralizar e tipar estruturas auxiliares utilizadas pelo `ManagerAgent`.
- Inclusão do arquivo `py.typed` para habilitar type hints com suporte a verificação estática.
- Adição das URLs do projeto no `pyproject.toml` para melhorar indexação no PyPI:
  - Homepage
  - Source
  - Issues

---

## [0.0.1] - 2025-05-23
### Adicionado
- Estrutura inicial do projeto com layout baseado em `src/`
- Classe `SimpleAgent` com suporte a:
  - Geração de resposta com ou sem streaming
  - Histórico persistente por agente via `InteractionHistory`
- Classe `ComplexAgent` com:
  - Execução de múltiplas funções com retorno via JSON
  - Ciclo de chamada de função + segunda rodada com resposta final
  - Suporte a envio de imagens codificadas em base64
- Suporte a múltiplos arquivos base64 por prompt
- Integração com Google Gemini API (`google-generativeai`)
- Modularização em subpacotes:
  - `core`, `storage`, `utils`
- Prompt dinâmico adaptado a presença ou não de funções
- Compatível com publicação como pacote via `pyproject.toml`

### Alterado
- Prompt ajustado para instruir o modelo a usar o histórico e a gerar JSON quando apropriado
- Refatoração para uso de `inspect.signature` nas definições de função

### Correções
- Corrigido encoding UTF-8 com `ensure_ascii=False` para salvar histórico

---

## [0.0.1-pre] - 2025-05-21
### Protótipo
- Primeira versão funcional dos agentes com suporte ao Gemini
- Armazenamento de histórico em JSON sem controle de tamanho
- Suporte a apenas uma função por agente
- Prompt estático
- Sem empacotamento
