# video-transcriber

Console Python que transcreve áudio/vídeo e grava, **na mesma pasta**, um `.md` de mesmo nome
com a transcrição (parágrafos com carimbo de tempo) e um resumo opcional feito por IA.

- **Transcrição:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper), 100% local (CPU ou GPU).
  Decodifica áudio e vídeo via PyAV, sem precisar de ffmpeg instalado.
  Formatos listados: mp3, wav, m4a, aac, ogg, opus, flac, wma, amr, mp4, mkv, mov, avi, webm,
  wmv, **asf**, m4v, 3gp, mpeg, mpg, ts, mts, flv. Outras extensões são tentadas com aviso.
  ASF/WMA/WMV com DRM não são suportados.
- **Resumo (opcional):** Ollama em outra máquina da rede local (`config.json` → `ollama`).
  Só título/resumo/tópicos; a IA nunca decide caminho nem fluxo. Ver [.specs/ia.md](.specs/ia.md).
- **Nada sai da rede.** A única coisa baixada da internet são os pesos do Whisper, na 1ª execução
  (Hugging Face, cache em `%USERPROFILE%\.cache\huggingface`). Nenhum áudio é enviado.

## Uso

```powershell
.\transcrever.ps1                       # interativo: pede arquivo ou pasta
.\transcrever.ps1 "D:\videos\aula.mp4"  # direto (vários arquivos aceitos)
.\transcrever.ps1 -f *.mp3              # sobrescreve .md existentes
.\transcrever.ps1 -r aula.mp4           # refaz só o resumo (ex.: IA estava offline)
```

Ou dê duplo clique em `transcrever.cmd`, ou arraste arquivos sobre ele.

### Executável (sem Python instalado)

`dist\video-transcriber.exe` é um arquivo único de cerca de 100 MB e aceita os mesmos argumentos.
Coloque o `config.json` ao lado dele: sem esse arquivo, o resumo fica desligado.
Duplo clique abre o modo interativo. Arrastando arquivos sobre o .exe, ele transcreve e espera
um Enter antes de fechar. Abre em cerca de 3 s, tempo de descompactar o executável.

No modo interativo:
- Cole o caminho (aspas do "Copiar como caminho" do Explorer são aceitas).
- Informe uma **pasta** para listar os áudios/vídeos e escolher pelo número ou pelo nome.
- Se o `.md` já existir: `s` sobrescreve, `r` refaz só o resumo, `c` cancela.
- `Ctrl+C` cancela o arquivo atual; `Enter` vazio sai.

Saída (`aula.md`):

```markdown
# aula
| Arquivo | `aula.mp4` | Duração | 00:42:10 | Idioma | pt (99%) | ...
<!-- resumo status=ok -->
## Resumo
...
<!-- /resumo -->
## Transcrição
**[00:00:03]** Bom dia a todos...
```

## Desenvolvimento

| Rotina | Comando |
|---|---|
| Iniciar (setup) | `py -3.12 -m venv .venv; .venv\Scripts\pip install -e ".[dev]"`. O `transcrever.ps1` faz isso sozinho na 1ª vez, mas sem as dependências de dev. |
| Configurar | `copy config.example.json config.json` e ajustar `ollama.url` |
| Executar | `.\transcrever.ps1` ou `.venv\Scripts\python -m transcritor` |
| Parar | `Ctrl+C` (cancela o arquivo atual), `Enter` vazio no prompt ou `Ctrl+C` no prompt (sai) |
| Testes | `.venv\Scripts\python -m pytest` |
| Build | `.\build.ps1` → `dist\video-transcriber.exe` (PyInstaller onefile; precisa do `.[dev]`). Depois `copy config.json dist\` |

Estrutura:

```
transcritor/
  __main__.py     console (rich): prompts, progresso, relatório
  transcricao.py  faster-whisper → trechos com tempo
  markdown.py     monta o .md, parágrafos, troca do bloco de resumo
  ia.py           ClienteOllama + enriquecimento (schema Pydantic, retry)
  config.py       config.json (Pydantic)
.specs/ia.md      regras da IA
```

## Configuração

`config.json` na raiz (não versionado, com cópia em `D:\Sincronizado\tecnologia\envs\video-transcriber\`).
Modelo em `config.example.json`. Outro caminho: variável `TRANSCRITOR_CONFIG`.

| Chave | Padrão | Notas |
|---|---|---|
| `whisper.modelo` | `small` | `tiny`/`base` (rápidos), `small` (bom em CPU), `medium`, `large-v3`, `turbo` (melhor, pesado) |
| `whisper.idioma` | `pt` | `null` detecta automaticamente |
| `whisper.dispositivo` | `auto` | `cpu` ou `cuda` (GPU NVIDIA requer CUDA/cuDNN) |
| `whisper.tipo_computo` | `auto` | `int8` em CPU, `float16` em GPU |
| `ollama.habilitado` | `false` sem config | `false` desliga o resumo |
| `ollama.url` / `modelo` / `timeout_s` | `qwen2.5:7b`, 120 s | |

Sem Docker: o programa precisa ler caminhos locais quaisquer digitados pelo usuário, e montar volumes
para isso só atrapalha. O `.venv` já isola as dependências.

## Licenças

faster-whisper (MIT), pesos Whisper (MIT), rich (MIT), httpx (BSD), pydantic (MIT).
`qwen2.5:7b` é Apache-2.0 (as variantes 3B e 72B têm licença Qwen própria): confira antes de uso não pessoal.
