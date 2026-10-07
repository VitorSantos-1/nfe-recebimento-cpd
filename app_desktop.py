"""
app_desktop.py — Formulário CPD (Aplicativo Desktop Nativo)
Supermercados Opção

Mesma aplicação de sempre (FastAPI + index.html), porém empacotada como um
PROGRAMA PRÓPRIO: em vez de abrir o navegador, abre em uma janela nativa do
Windows (WebView2), sem abas e sem barra de endereços.

O back-end e a interface são reaproveitados de main.py (fonte única de verdade):
importar main como módulo NÃO executa o bloco __main__, ou seja, não abre o
navegador — apenas disponibiliza o app FastAPI.
"""

import os
import sys

# ─── Correção crítica para PyInstaller --noconsole ────────────────────────────
class _SaidaNula:
    def write(self, *a, **k): return 0
    def writelines(self, *a, **k): pass
    def flush(self, *a, **k): pass
    def isatty(self, *a, **k): return False

if sys.stdout is None: sys.stdout = _SaidaNula()
if sys.stderr is None: sys.stderr = _SaidaNula()

import time
import socket
import threading
import traceback

import uvicorn
import webview  # pywebview → janela nativa (WebView2 no Windows)

# Reaproveita 100% do servidor/rotas/HTML. Importar como módulo não sobe o
# servidor nem abre o navegador (isso só acontece no __main__ de main.py).
import database
import cpd_mysql
import main as cpd

APP_TITLE = "Formulário CPD — Recebimentos & Ocorrências"


# ─── Utilidades de rede ───────────────────────────────────────────────────────
def _porta_livre(preferida=8080):
    candidatas = [preferida] + list(range(preferida + 1, preferida + 60))
    for port in candidatas:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
            s.close()
            return port
        except OSError:
            continue
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _servidor_no_ar(port, timeout=40.0):
    alvo = time.time() + timeout
    while time.time() < alvo:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1.0)
            s.close()
            return True
        except OSError:
            time.sleep(0.15)
    return False


def _iniciar_servidor(port):
    config = uvicorn.Config(cpd.app, host="127.0.0.1", port=port, log_level="warning")
    uvicorn.Server(config).run()


def _mostrar_erro(msg, titulo="Formulário CPD — Aviso"):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, msg, titulo, 0x30)
    except Exception:
        pass


# ─── Programa principal ───────────────────────────────────────────────────────
def main():
    # 1. Banco: SQLite (fallback local) sempre; MySQL (principal) se disponível.
    try:
        database.init_db()
    except Exception:
        pass  # o fallback SQLite não deve impedir a abertura do programa

    try:
        cpd_mysql.init_mysql()
    except Exception as e:
        _mostrar_erro(
            "O Formulário CPD não conseguiu conectar ao banco de dados (MySQL).\n\n"
            "Confira o arquivo config.json (host/porta) e se o servidor MySQL está ligado.\n\n"
            f"Detalhe técnico:\n{e}"
        )
        # Segue mesmo assim: a tela do app informará o problema de conexão.

    # 2. Servidor interno (FastAPI) em segundo plano, só no localhost.
    port = _porta_livre(int(os.environ.get("CPD_PORT", "8080")))
    threading.Thread(target=_iniciar_servidor, args=(port,), daemon=True).start()

    if not _servidor_no_ar(port):
        _mostrar_erro(f"O servidor interno não respondeu a tempo (porta {port}).", "Formulário CPD — Erro")
        sys.exit(1)

    # 3. Janela desktop nativa (sem navegador).
    webview.create_window(
        APP_TITLE,
        f"http://127.0.0.1:{port}",
        width=1440,
        height=900,
        min_size=(1100, 680),
    )
    try:
        webview.start(gui="edgechromium")
    except Exception:
        _mostrar_erro(
            "Para o visual completo, instale o \"Microsoft Edge WebView2 Runtime\" "
            "(gratuito da Microsoft) neste computador.\n\nO aplicativo tentará abrir mesmo assim."
        )
        webview.start()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        err_path = os.path.join(os.path.expanduser("~"), "Desktop", "formulario_cpd_error.txt")
        try:
            with open(err_path, "w", encoding="utf-8") as f:
                f.write("Erro ao iniciar o Formulário CPD:\n\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        _mostrar_erro(f"Erro ao iniciar o Formulário CPD:\n\n{e}\n\nDetalhe salvo em:\n{err_path}", "Formulário CPD — Erro")
        sys.exit(1)
