from pathlib import Path

from transcritor.ia import Enriquecimento
from transcritor.markdown import (
    bloco_resumo,
    hms,
    montar,
    paragrafos,
    status_resumo,
    texto_transcricao,
    trocar_resumo,
)
from transcritor.transcricao import Resultado, Trecho


def _res(*trechos: Trecho) -> Resultado:
    return Resultado("pt", 0.98, 125.0, list(trechos))


def test_hms():
    assert hms(0) == "00:00:00"
    assert hms(3725.9) == "01:02:05"


def test_paragrafos_quebra_em_pausa():
    t = [Trecho(0, 2, "Olá."), Trecho(2.5, 4, "Tudo bem?"), Trecho(10, 12, "Outro assunto.")]
    assert paragrafos(t) == [(0, "Olá. Tudo bem?"), (10, "Outro assunto.")]


def test_paragrafos_quebra_em_fim_de_frase_quando_longo():
    t = [Trecho(i, i + 1, "x" * 50 + ".") for i in range(20)]
    pars = paragrafos(t, max_chars=200)
    assert len(pars) > 1
    assert all(len(p) <= 260 for _, p in pars)


def test_montar_e_refazer_resumo():
    md = montar(
        Path("C:/Users/voce/videos/reuniao.mp4"),
        _res(Trecho(0, 3, "Bom dia a todos."), Trecho(65, 70, "Vamos começar.")),
        "small",
        bloco_resumo("pendente", erro="offline"),
    )
    assert md.startswith("# reuniao\n")
    assert "**[00:01:05]** Vamos começar." in md
    assert status_resumo(md) == "pendente"
    assert texto_transcricao(md) == "Bom dia a todos.\n\nVamos começar."

    enr = Enriquecimento(titulo="Abertura", resumo="Saudação inicial.", topicos=["abertura"])
    novo = trocar_resumo(md, bloco_resumo("ok", enr, "qwen2.5:7b"))
    assert status_resumo(novo) == "ok"
    assert "Saudação inicial." in novo and "pendente" not in novo
    assert texto_transcricao(novo) == texto_transcricao(md)


def test_sem_fala():
    md = montar(Path("a.mp3"), _res(), "small", bloco_resumo("desligada"))
    assert "_Nenhuma fala detectada._" in md
    assert texto_transcricao(md) == ""
