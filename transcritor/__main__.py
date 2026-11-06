"""Console: pede o arquivo (ou pasta), transcreve e grava <mesmo nome>.md ao lado."""

import argparse
import sys
import time
from pathlib import Path

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Prompt
from rich.table import Table

from transcritor import __version__
from transcritor.config import Config, carregar
from transcritor.ia import ClienteOllama, Indisponivel, enriquecer
from transcritor.markdown import (
    bloco_resumo,
    hms,
    montar,
    status_resumo,
    texto_transcricao,
    trocar_resumo,
)
from transcritor.transcricao import carregar_modelo, transcrever

MIDIA = {
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".flac", ".wma", ".amr",
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".asf", ".m4v", ".3gp", ".mpeg", ".mpg",
    ".ts", ".mts", ".flv",
}  # fmt: skip

STATUS = {
    "ok": "[green]ok[/]",
    "pendente": "[yellow]pendente (IA indisponível)[/]",
    "erro": "[red]erro[/]",
    "desligada": "[dim]desligada[/]",
}

for _f in (sys.stdout, sys.stderr):  # saída redirecionada no Windows vem cp1252
    if _f and hasattr(_f, "reconfigure") and (_f.encoding or "").lower() != "utf-8":
        _f.reconfigure(encoding="utf-8", errors="replace")

console = Console()


class Sessao:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.cliente = ClienteOllama.de_config(cfg.ollama) if cfg.ollama.habilitado else None
        self.ia_fora: str | None = None  # 1ª falha → não insiste nesta sessão
        if self.cliente:
            try:
                httpx.get(f"{self.cliente.url}/api/tags", timeout=3).raise_for_status()
            except httpx.HTTPError as e:
                self.ia_fora = f"{self.cliente.url}: {type(e).__name__}"

    def banner(self) -> None:
        w, o = self.cfg.whisper, self.cfg.ollama
        if not self.cliente:
            ia = "[dim]desligada[/]"
        elif self.ia_fora:
            ia = f"[red]● offline[/] {o.modelo} [dim]({o.url})[/]"
        else:
            ia = f"[green]● online[/] {o.modelo} [dim]({o.url})[/]"
        console.print(
            Panel.fit(
                f"[bold]Video Transcriber[/] [dim]v{__version__}[/]\n"
                f"Whisper  [cyan]{w.modelo}[/] · idioma {w.idioma or 'auto'} · {w.dispositivo}\n"
                f"Resumo   {ia}",
                border_style="cyan",
            )
        )

    def resumo(self, texto: str) -> str:
        if not self.cliente:
            return bloco_resumo("desligada")
        if self.ia_fora:
            return bloco_resumo("pendente", erro=self.ia_fora)
        if not texto.strip():
            return bloco_resumo("erro", erro="transcrição vazia")
        with console.status(f"[cyan]Resumindo com {self.cliente.modelo}…"):
            try:
                enr = enriquecer(self.cliente, texto)
            except Indisponivel as e:
                self.ia_fora = str(e)
                return bloco_resumo("pendente", erro=self.ia_fora)
            except Exception as e:  # resposta inválida, HTTP 4xx/500…
                return bloco_resumo("erro", erro=str(e)[:300])
        return bloco_resumo("ok", enr, self.cliente.modelo)


# --- passos -------------------------------------------------------------------


def _transcrever(arquivo: Path, sessao: Sessao):
    w = sessao.cfg.whisper
    with console.status(f"[cyan]Carregando whisper {w.modelo}[/] [dim](1ª vez baixa o modelo)[/]"):
        carregar_modelo(w)
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Transcrevendo"),
        BarColumn(),
        TextColumn("{task.fields[pos]}"),
        TimeElapsedColumn(),
        TextColumn("[dim]resta[/]"),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    ) as prog:
        tarefa = prog.add_task("", total=None, pos="")

        def avancar(pos: float, total: float) -> None:
            prog.update(tarefa, total=total, completed=pos, pos=f"{hms(pos)} / {hms(total)}")

        return transcrever(arquivo, w, avancar)


def _relatorio(destino: Path, linhas: dict[str, str]) -> None:
    t = Table.grid(padding=(0, 2))
    for k, v in linhas.items():
        t.add_row(f"[dim]{k}[/]", v)
    console.print(Panel(t, title=f"[green]✔ {destino.name}", border_style="green", expand=False))


def processar(arquivo: Path, sessao: Sessao, so_resumo: bool = False) -> None:
    destino = arquivo.with_suffix(".md")
    inicio = time.monotonic()
    if so_resumo:
        md = destino.read_text(encoding="utf-8")
        md = trocar_resumo(md, sessao.resumo(texto_transcricao(md)))
        destino.write_text(md, encoding="utf-8")
        _relatorio(destino, {"Resumo": STATUS[status_resumo(md) or "erro"]})
        return

    console.print(f"[bold]▶[/] {arquivo.name}")
    res = _transcrever(arquivo, sessao)
    texto = " ".join(t.texto for t in res.trechos)
    md = montar(arquivo, res, sessao.cfg.whisper.modelo, sessao.resumo(texto))
    destino.write_text(md, encoding="utf-8")
    _relatorio(
        destino,
        {
            "Duração": hms(res.duracao),
            "Idioma": f"{res.idioma} ({res.prob_idioma:.0%})",
            "Palavras": f"{len(texto.split()):,}".replace(",", "."),
            "Tempo": hms(time.monotonic() - inicio),
            "Resumo": STATUS[status_resumo(md) or "erro"],
            "Saída": str(destino),
        },
    )


# --- modo interativo ----------------------------------------------------------


def _limpar(resp: str) -> str:
    return resp.strip().strip('"').strip("'").strip()  # "Copiar como caminho" do Explorer


def _escolher_na_pasta(pasta: Path) -> Path | None:
    arquivos = sorted(
        (p for p in pasta.iterdir() if p.suffix.lower() in MIDIA), key=lambda p: p.name.lower()
    )
    if not arquivos:
        console.print(f"[yellow]Nenhum áudio/vídeo em[/] {pasta}")
        return None
    t = Table(box=None, header_style="dim")
    t.add_column("#", justify="right", style="cyan")
    t.add_column("arquivo")
    t.add_column("tamanho", justify="right", style="dim")
    t.add_column("", style="green")
    for i, p in enumerate(arquivos, 1):
        md = "✔ .md" if p.with_suffix(".md").exists() else ""
        t.add_row(str(i), p.name, f"{p.stat().st_size / 2**20:,.1f} MB", md)
    console.print(t)
    resp = _limpar(Prompt.ask("Número ou nome do arquivo [dim](Enter volta)[/]", default="", show_default=False))
    if not resp:
        return None
    if resp.isdigit() and 1 <= int(resp) <= len(arquivos):
        return arquivos[int(resp) - 1]
    return pasta / resp


def _resolver(resp: str) -> Path | None:
    p: Path | None = Path(resp).expanduser()
    if p.is_dir():
        p = _escolher_na_pasta(p)
        if p is None:
            return None
    if not p.is_file():
        console.print(f"[red]Arquivo não encontrado:[/] {p}")
        return None
    if p.suffix.lower() == ".md":
        console.print("[red]Informe o áudio/vídeo, não o .md.[/]")
        return None
    if p.suffix.lower() not in MIDIA:
        console.print(f"[yellow]Extensão {p.suffix or '(nenhuma)'} incomum; tentando mesmo assim.[/]")
    return p


def _perguntar_existente(destino: Path, sessao: Sessao) -> str:
    """Retorna 's' (sobrescrever), 'r' (só resumo) ou 'c' (cancelar)."""
    opcoes = {"s": "sobrescrever"}
    if sessao.cliente:
        opcoes["r"] = "refazer só o resumo"
    opcoes["c"] = "cancelar"
    status = status_resumo(destino.read_text(encoding="utf-8")) or "sem resumo"
    console.print(f"[yellow]{destino.name} já existe[/] [dim](resumo: {status})[/]")
    legenda = "  ".join(f"[cyan]{k}[/] {v}" for k, v in opcoes.items())
    return Prompt.ask(legenda, choices=list(opcoes), default="c", show_choices=False)


def interativo(sessao: Sessao) -> None:
    while True:
        console.print()
        try:
            resp = _limpar(Prompt.ask("[bold]Arquivo ou pasta[/] [dim](Enter sai)[/]", default="", show_default=False))
        except (KeyboardInterrupt, EOFError):
            break
        if not resp:
            break
        try:
            arquivo = _resolver(resp)
            if not arquivo:
                continue
            escolha = "s"
            if arquivo.with_suffix(".md").exists():
                escolha = _perguntar_existente(arquivo.with_suffix(".md"), sessao)
            if escolha != "c":
                processar(arquivo, sessao, so_resumo=escolha == "r")
        except KeyboardInterrupt:
            console.print("[yellow]Cancelado.[/]")
        except Exception as e:
            console.print(f"[red]Falhou:[/] {type(e).__name__}: {e}")
    console.print("[dim]Até mais.[/]")


# --- entrada ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="transcrever", description="Transcreve áudio/vídeo para Markdown ao lado do arquivo."
    )
    ap.add_argument("arquivos", nargs="*", type=Path, help="sem argumentos: modo interativo")
    ap.add_argument("-f", "--forcar", action="store_true", help="sobrescreve .md existente")
    ap.add_argument("-r", "--resumo", action="store_true", help="refaz só o resumo do .md existente")
    args = ap.parse_args(argv)

    sessao = Sessao(carregar())
    sessao.banner()
    if not args.arquivos:
        interativo(sessao)
        return 0

    falhas = _lote(args, sessao)
    if _console_proprio():  # arrastou arquivos sobre o .exe: não fechar a janela na hora
        input("\nEnter para fechar...")
    return 1 if falhas else 0


def _console_proprio() -> bool:
    """True no .exe aberto por duplo clique/arrastar (console sem shell; onefile = 2 processos)."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False
    import ctypes

    return ctypes.windll.kernel32.GetConsoleProcessList((ctypes.c_uint * 4)(), 4) <= 2


def _lote(args: argparse.Namespace, sessao: Sessao) -> int:
    falhas = 0
    for a in args.arquivos:  # sequencial: o Ollama atende uma requisição por vez
        destino = a.with_suffix(".md")
        try:
            if args.resumo:
                if not destino.exists():
                    raise FileNotFoundError(destino)
                processar(destino, sessao, so_resumo=True)
            elif not a.is_file() or a.suffix.lower() == ".md":
                raise FileNotFoundError(a)
            elif destino.exists() and not args.forcar:
                console.print(f"[dim]↷ {destino.name} já existe (use -f)[/]")
            else:
                processar(a, sessao)
        except KeyboardInterrupt:
            console.print("[yellow]Cancelado.[/]")
            return falhas + 1
        except Exception as e:
            falhas += 1
            console.print(f"[red]✖ {a.name}:[/] {type(e).__name__}: {e}")
    return falhas


if __name__ == "__main__":
    sys.exit(main())
