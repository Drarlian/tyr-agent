# 📦 CHANGELOG

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue as convenções do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/), e este projeto adota o versionamento semântico.

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
