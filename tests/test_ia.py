import json

import httpx
import pytest

from transcritor.ia import (
    MAX_TEXTO,
    ClienteOllama,
    Indisponivel,
    RespostaInvalida,
    amostra,
    enriquecer,
)

OK = {"titulo": "Reunião", "resumo": "Resumo.", "topicos": ["a", "b"]}


def _cliente(respostas: list) -> tuple[ClienteOllama, list[dict]]:
    corpos: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        corpos.append(json.loads(req.content))
        r = respostas.pop(0)
        if isinstance(r, int):
            return httpx.Response(r)
        return httpx.Response(200, json={"message": {"content": r}})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    return ClienteOllama("http://192.168.0.10:11434/", "qwen2.5:7b", 120, http), corpos


def test_ok_e_corpo_da_requisicao():
    c, corpos = _cliente([json.dumps(OK)])
    assert enriquecer(c, "texto").titulo == "Reunião"
    corpo = corpos[0]
    assert corpo["stream"] is False and corpo["options"] == {"temperature": 0}
    assert set(corpo["format"]["required"]) == {"titulo", "resumo", "topicos"}


def test_invalida_faz_um_retry():
    c, corpos = _cliente(["nao é json", json.dumps(OK)])
    assert enriquecer(c, "texto").resumo == "Resumo."
    assert len(corpos) == 2


def test_invalida_duas_vezes_vira_erro():
    c, _ = _cliente(["{}", "{}"])
    with pytest.raises(RespostaInvalida):
        enriquecer(c, "texto")


@pytest.mark.parametrize("status", [502, 503, 504])
def test_gateway_indisponivel(status):
    c, _ = _cliente([status])
    with pytest.raises(Indisponivel):
        enriquecer(c, "texto")


def test_conexao_recusada_indisponivel():
    def handler(req):
        raise httpx.ConnectError("recusada")

    c = ClienteOllama("http://x", "m", 1, httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(Indisponivel):
        enriquecer(c, "texto")


def test_amostra_limita_e_cobre_inicio_meio_fim():
    texto = "A" * 5000 + "M" * 5000 + "Z" * 5000
    a = amostra(texto)
    assert len(a) <= MAX_TEXTO
    assert a.startswith("A") and "M" in a and a.endswith("Z")
    assert amostra("curto") == "curto"
