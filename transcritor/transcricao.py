"""Speech-to-text local com faster-whisper (decodifica áudio e vídeo via PyAV)."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from transcritor.config import Whisper


@dataclass
class Trecho:
    inicio: float
    fim: float
    texto: str


@dataclass
class Resultado:
    idioma: str
    prob_idioma: float
    duracao: float
    trechos: list[Trecho]


@lru_cache(maxsize=1)
def _modelo(nome: str, dispositivo: str, tipo: str):
    from faster_whisper import WhisperModel  # import pesado: só quando precisa

    return WhisperModel(nome, device=dispositivo, compute_type=tipo)


def carregar_modelo(cfg: Whisper) -> None:
    """Carrega (e na 1ª vez baixa) o modelo. Reaproveitado entre arquivos."""
    _modelo(cfg.modelo, cfg.dispositivo, cfg.tipo_computo)


def transcrever(
    arquivo: Path, cfg: Whisper, progresso: Callable[[float, float], None] | None = None
) -> Resultado:
    modelo = _modelo(cfg.modelo, cfg.dispositivo, cfg.tipo_computo)
    segmentos, info = modelo.transcribe(
        str(arquivo), language=cfg.idioma or None, vad_filter=True, beam_size=5
    )
    trechos: list[Trecho] = []
    for s in segmentos:  # gerador: a transcrição acontece aqui
        if texto := s.text.strip():
            trechos.append(Trecho(s.start, s.end, texto))
        if progresso:
            progresso(s.end, info.duration)
    return Resultado(info.language, info.language_probability, info.duration, trechos)
