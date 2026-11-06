# IA (resumo)

Ollama remoto (outra máquina da rede local). URL e modelo no `config.json` (bloco `ollama`:
`habilitado, url, modelo, timeout_s`). Nada de IA no projeto além do Whisper local; nenhum dado sai da rede.

## Regras
- A IA só enriquece: grava o bloco `<!-- resumo status=... -->` do `.md`. Nunca decide caminho, nome ou fluxo.
- `POST {url}/api/chat`, `stream: false`, `temperature: 0`, `format` = JSON Schema de
  `Enriquecimento {titulo, resumo, topicos}` com todos os campos em `required`.
- Resposta validada por Pydantic; inválida → 1 retry → status `erro`.
- Conexão falhou / timeout / HTTP 502-503-504 → `pendente`. A sessão para de chamar a IA
  (os demais arquivos já saem `pendente`). Também checa `/api/tags` (3 s) ao iniciar.
- Chamadas sequenciais, timeout de 120 s.
- Entrada ≤ 3000 chars: texto inteiro ou início + meio + fim, separados por `[...]`.

## Status do bloco
`ok` · `pendente` · `erro` · `desligada`. Reprocessar: `transcrever -r <arquivo>` ou opção `r` no
modo interativo. Lê a seção `## Transcrição` do próprio `.md`, sem retranscrever.
