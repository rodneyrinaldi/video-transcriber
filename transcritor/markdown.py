"""Monta o .md de saída. O bloco de resumo fica entre marcadores para ser refeito depois."""

import re
from datetime import datetime
from pathlib import Path

from transcritor.ia import Enriquecimento
from transcritor.transcricao import Resultado, Trecho

TITULO_TRANSCRICAO = "## Transcrição"
_BLOCO = re.compile(r"<!-- resumo status=(\w+) -->.*?<!-- /resumo -->", re.S)
_CARIMBO = re.compile(r"^\*\*\[\d\d:\d\d:\d\d\]\*\*\s*", re.M)


def hms(seg: float) -> str:
    s = int(seg)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def paragrafos(
    trechos: list[Trecho], pausa: float = 2.0, max_chars: int = 600
) -> list[tuple[float, str]]:
    """Agrupa trechos em parágrafos: quebra em pausa longa ou fim de frase após `max_chars`."""
    saida: list[tuple[float, str]] = []
    buf: list[str] = []
    inicio = fim = 0.0
    for t in trechos:
        tamanho = sum(len(x) + 1 for x in buf)
        if buf and (t.inicio - fim > pausa or (tamanho > max_chars and buf[-1][-1:] in ".?!…")):
            saida.append((inicio, " ".join(buf)))
            buf = []
        if not buf:
            inicio = t.inicio
        buf.append(t.texto)
        fim = t.fim
    if buf:
        saida.append((inicio, " ".join(buf)))
    return saida


def bloco_resumo(
    status: str, enr: Enriquecimento | None = None, modelo: str = "", erro: str | None = None
) -> str:
    """status: ok | pendente | erro | desligada."""
    if status == "ok" and enr:
        topicos = " · ".join(t.strip() for t in enr.topicos if t.strip())
        corpo = (
            f"## Resumo\n\n**{enr.titulo.strip()}**\n\n{enr.resumo.strip()}\n\n"
            f"**Tópicos:** {topicos}\n\n"
            f"<sub>Gerado por IA ({modelo}) em {agora()}. Confira com a transcrição.</sub>"
        )
    elif status == "pendente":
        corpo = f"> Resumo pendente: IA indisponível ({erro}). Reprocesse com `transcrever -r`."
    elif status == "erro":
        corpo = f"> Resumo não gerado: {erro}"
    else:
        corpo = ""
    return f"<!-- resumo status={status} -->\n{corpo}\n<!-- /resumo -->"


def montar(arquivo: Path, res: Resultado, modelo_whisper: str, resumo: str) -> str:
    linhas = [
        f"# {arquivo.stem}",
        "",
        "| | |",
        "|---|---|",
        f"| Arquivo | `{arquivo.name}` |",
        f"| Duração | {hms(res.duracao)} |",
        f"| Idioma | {res.idioma} ({res.prob_idioma:.0%}) |",
        f"| Modelo | whisper `{modelo_whisper}` |",
        f"| Transcrito em | {agora()} |",
        "",
        resumo,
        "",
        TITULO_TRANSCRICAO,
        "",
    ]
    pars = paragrafos(res.trechos)
    if not pars:
        linhas.append("_Nenhuma fala detectada._")
    for inicio, texto in pars:
        linhas += [f"**[{hms(inicio)}]** {texto}", ""]
    return "\n".join(linhas).rstrip() + "\n"


def status_resumo(md: str) -> str | None:
    m = _BLOCO.search(md)
    return m.group(1) if m else None


def trocar_resumo(md: str, novo: str) -> str:
    if _BLOCO.search(md):
        return _BLOCO.sub(lambda _: novo, md, count=1)
    return md.replace(TITULO_TRANSCRICAO, f"{novo}\n\n{TITULO_TRANSCRICAO}", 1)


def texto_transcricao(md: str) -> str:
    """Texto corrido da seção de transcrição (sem carimbos de tempo)."""
    _, _, resto = md.partition(TITULO_TRANSCRICAO)
    texto = _CARIMBO.sub("", resto).strip()
    return "" if texto == "_Nenhuma fala detectada._" else texto
