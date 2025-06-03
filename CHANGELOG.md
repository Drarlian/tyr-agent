# 📦 CHANGELOG

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue as convenções do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/), e este projeto adota o versionamento semântico.

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
