"""config.json na raiz do projeto (não versionado). Ausente → padrões, IA desligada."""

import os
import sys
from pathlib import Path

from pydantic import BaseModel

# .exe (PyInstaller): config.json ao lado do executável; fonte: raiz do projeto
RAIZ = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent.parent
)


class Whisper(BaseModel):
    modelo: str = "small"  # tiny | base | small | medium | large-v3 | turbo
    idioma: str | None = "pt"  # None → detecta
    dispositivo: str = "auto"  # auto | cpu | cuda
    tipo_computo: str = "auto"  # auto | int8 | float16 ...


class Ollama(BaseModel):
    habilitado: bool = False
    url: str = "http://localhost:11434"
    modelo: str = "qwen2.5:7b"
    timeout_s: int = 120


class Config(BaseModel):
    whisper: Whisper = Whisper()
    ollama: Ollama = Ollama()


def carregar(caminho: Path | None = None) -> Config:
    p = caminho or Path(os.environ.get("TRANSCRITOR_CONFIG", RAIZ / "config.json"))
    if not p.exists():
        return Config()
    return Config.model_validate_json(p.read_text(encoding="utf-8"))
