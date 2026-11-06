"""Ollama remoto (rede local) enriquece a transcrição: título, resumo, tópicos (.specs/ia.md).

A IA só enriquece. Nunca decide caminho, nome de arquivo ou fluxo.
Fora do ar → status `pendente`, reprocessável depois.
"""

import json

import httpx
from pydantic import BaseModel, ValidationError

from transcritor.config import Ollama

MAX_TEXTO = 3000
TENTATIVAS = 2  # resposta inválida → 1 retry


class Indisponivel(Exception):
    """Ollama fora do ar, sem resposta no prazo ou HTTP 502/503/504."""


class RespostaInvalida(Exception):
    pass


class Enriquecimento(BaseModel):
    titulo: str
    resumo: str
    topicos: list[str]


class ClienteOllama:
    def __init__(self, url: str, modelo: str, timeout_s: int, http: httpx.Client | None = None):
        self.url = url.rstrip("/")
        self.modelo = modelo
        self.http = http or httpx.Client(timeout=timeout_s)

    @classmethod
    def de_config(cls, o: Ollama) -> "ClienteOllama":
        return cls(o.url, o.modelo, o.timeout_s)

    def json(self, sistema: str, usuario: str, esquema: dict) -> str:
        corpo = {
            "model": self.modelo,
            "messages": [
                {"role": "system", "content": sistema},
                {"role": "user", "content": usuario},
            ],
            "format": esquema,
            "stream": False,
            "options": {"temperature": 0},
        }
        try:
            r = self.http.post(f"{self.url}/api/chat", json=corpo)
        except httpx.TransportError as e:
            raise Indisponivel(f"Ollama {self.url}: {e}") from e
        if r.status_code in (502, 503, 504):
            raise Indisponivel(f"Ollama {self.url}: HTTP {r.status_code}")
        r.raise_for_status()
        return r.json()["message"]["content"]

    def fechar(self) -> None:
        self.http.close()


SISTEMA = (
    "Você resume transcrições automáticas de áudio em português (conteúdo pessoal/jurídico, "
    "Brasil). Use apenas o que está no texto, sem inventar fatos. Responda somente com JSON."
)


def amostra(texto: str, limite: int = MAX_TEXTO) -> str:
    """Até `limite` chars: texto inteiro, ou início + meio + fim quando é longo."""
    if len(texto) <= limite:
        return texto
    sep = "\n[...]\n"
    n = (limite - 2 * len(sep)) // 3
    meio = (len(texto) - n) // 2
    return sep.join([texto[:n], texto[meio : meio + n], texto[-n:]])


def _prompt(texto: str) -> str:
    return "\n".join(
        [
            "Campos: titulo (até 10 palavras), resumo (3 a 6 frases), "
            "topicos (3 a 8 itens curtos).",
            "A transcrição pode ter erros de reconhecimento e trechos omitidos marcados [...].",
            "",
            "Transcrição:",
            amostra(texto),
        ]
    )


def enriquecer(cliente: ClienteOllama, texto: str) -> Enriquecimento:
    esquema = Enriquecimento.model_json_schema()
    esquema["required"] = list(esquema["properties"])  # sem isso o modelo omite campos
    ultimo: Exception | None = None
    for _ in range(TENTATIVAS):
        conteudo = cliente.json(SISTEMA, _prompt(texto), esquema)
        try:
            return Enriquecimento.model_validate(json.loads(conteudo))
        except (json.JSONDecodeError, ValidationError) as e:
            ultimo = e
    raise RespostaInvalida(f"resposta inválida do modelo: {str(ultimo)[:200]}")
