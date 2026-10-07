"""
build_desktop.py — Compila o Formulário CPD como PROGRAMA DESKTOP NATIVO.

Abre em janela própria (WebView2), sem navegador. Empacota app_desktop.py
(launcher pywebview) + main.py (FastAPI) + index.html, em um único .exe.

Como usar:
    python build_desktop.py
Saida: dist/Formulario_CPD.exe  (e uma copia na Area de Trabalho)

Requisitos no PC final: Microsoft Edge WebView2 Runtime (já vem no Windows 10/11
atuais). O config.json NÃO é embutido — ele é distribuído ao lado do .exe pelo
instalador, editável por instalação.
"""

import os
import sys
import subprocess
import shutil

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DESKTOP_DIR = os.path.join(os.path.expanduser("~"), "Desktop")
ICON_PATH = os.path.join(PROJECT_DIR, "app_icon.ico")


def check_and_install_deps():
    deps = ["fastapi", "uvicorn", "pydantic", "pyinstaller", "passlib", "bcrypt",
            "python-jose", "mysql-connector-python", "pywebview", "pythonnet"]
    print("Verificando dependencias...")
    for dep in deps:
        mod = {"python-jose": "jose", "mysql-connector-python": "mysql.connector",
               "pywebview": "webview", "pythonnet": "clr", "pyinstaller": "PyInstaller"}.get(dep, dep)
        try:
            __import__(mod)
            print(f"  OK {dep}")
        except ImportError:
            print(f"  Instalando {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)


def build():
    os.chdir(PROJECT_DIR)
    print("\nCompilando Formulario_CPD (Desktop Nativo WebView2)...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--add-data", "index.html;.",
    ]
    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", "app_icon.ico"])

    hidden = [
        # servidor / API
        "fastapi", "uvicorn", "uvicorn.logging", "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto", "uvicorn.protocols.http.h11_impl",
        # auth
        "passlib", "passlib.handlers", "passlib.handlers.sha2_crypt",
        "passlib.utils", "passlib.utils.handlers", "passlib.context", "passlib.registry",
        "bcrypt",
        "jose", "jose.jwt", "jose.jws", "jose.exceptions", "jose.constants", "jose.backends",
        # banco
        "mysql.connector", "mysql.connector.plugins",
        "mysql.connector.plugins.mysql_native_password",
        "mysql.connector.plugins.caching_sha2_password",
        # modulos do projeto
        "main", "database", "cpd_mysql",
        # janela nativa (WebView2)
        "webview", "webview.platforms.edgechromium", "webview.platforms.winforms",
        "clr", "clr_loader",
    ]
    for h in hidden:
        cmd.extend(["--hidden-import", h])

    for c in ["passlib", "bcrypt", "mysql.connector", "jose", "uvicorn", "webview", "clr_loader"]:
        cmd.extend(["--collect-all", c])

    cmd.extend(["--name=Formulario_CPD", "app_desktop.py"])

    if subprocess.run(cmd).returncode != 0:
        print("\nErro na compilacao.")
        sys.exit(1)

    src = os.path.join(PROJECT_DIR, "dist", "Formulario_CPD.exe")
    try:
        shutil.copy2(src, os.path.join(DESKTOP_DIR, "Formulario_CPD.exe"))
        print("Copia na Area de Trabalho: OK")
    except Exception as e:
        print(f"(aviso) nao copiei para a Area de Trabalho: {e}")

    for p in ["build"]:
        pp = os.path.join(PROJECT_DIR, p)
        if os.path.exists(pp):
            shutil.rmtree(pp, ignore_errors=True)
    spec = os.path.join(PROJECT_DIR, "Formulario_CPD.spec")
    if os.path.exists(spec):
        os.remove(spec)
    print(f"\nExecutavel gerado: {src}")


if __name__ == "__main__":
    check_and_install_deps()
    build()
