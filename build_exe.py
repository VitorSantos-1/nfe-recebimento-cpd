import os
import sys
import subprocess
import shutil

PROJECT_DIR = r"C:\Users\Usuário\OneDrive\Documentos\minha_pasta\Projetos\cpd_form_project"
DESKTOP_DIR = r"C:\Users\Usuário\Desktop"

def check_and_install_deps():
    deps = ["fastapi", "uvicorn", "pydantic", "pyinstaller",
            "passlib", "bcrypt", "jose", "mysql.connector"]
    print("Verificando dependências do Python...")
    for dep in deps:
        try:
            __import__(dep if dep != "pyinstaller" else "PyInstaller")
            print(f"  OK {dep}")
        except ImportError:
            print(f"  Instalando {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)

def build_executable():
    os.chdir(PROJECT_DIR)
    print("\nCompilando executável com PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--add-data", "index.html;.",
        # passlib — inclui TODOS os handlers para evitar ModuleNotFoundError
        "--hidden-import", "passlib",
        "--hidden-import", "passlib.handlers",
        "--hidden-import", "passlib.handlers.sha2_crypt",
        "--hidden-import", "passlib.handlers.sha1_crypt",
        "--hidden-import", "passlib.handlers.md5_crypt",
        "--hidden-import", "passlib.utils",
        "--hidden-import", "passlib.utils.handlers",
        "--hidden-import", "passlib.utils.pbkdf2",
        "--hidden-import", "passlib.crypto",
        "--hidden-import", "passlib.crypto.digest",
        "--hidden-import", "passlib.context",
        "--hidden-import", "passlib.registry",
        # bcrypt nativo
        "--hidden-import", "bcrypt",
        # jose / JWT
        "--hidden-import", "jose",
        "--hidden-import", "jose.jwt",
        "--hidden-import", "jose.jws",
        "--hidden-import", "jose.exceptions",
        "--hidden-import", "jose.constants",
        "--hidden-import", "jose.backends",
        # mysql connector
        "--hidden-import", "mysql.connector",
        "--hidden-import", "mysql.connector.plugins",
        "--hidden-import", "mysql.connector.plugins.mysql_native_password",
        "--hidden-import", "mysql.connector.plugins.caching_sha2_password",
        # uvicorn
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        # collect-all garante binários e dados de cada pacote
        "--collect-all", "passlib",
        "--collect-all", "bcrypt",
        "--collect-all", "mysql.connector",
        "--collect-all", "jose",
        "--collect-all", "uvicorn",
        "--name=Formulario_CPD",
        "main.py"
    ]
    result = subprocess.run(cmd)
    if result.returncode == 0:
        src  = os.path.join(PROJECT_DIR, "dist", "Formulario_CPD.exe")
        dest = os.path.join(DESKTOP_DIR, "Formulario_CPD.exe")
        print(f"\nCopiando para: {dest}")
        shutil.copy2(src, dest)
        print("Executavel disponivel na Area de Trabalho!")
        for p in ["build", "dist"]:
            pp = os.path.join(PROJECT_DIR, p)
            if os.path.exists(pp): shutil.rmtree(pp)
        spec = os.path.join(PROJECT_DIR, "Formulario_CPD.spec")
        if os.path.exists(spec): os.remove(spec)
        print("Limpeza concluida.")
    else:
        print("\nErro durante a compilacao.")
        sys.exit(1)

if __name__ == "__main__":
    check_and_install_deps()
    build_executable()

