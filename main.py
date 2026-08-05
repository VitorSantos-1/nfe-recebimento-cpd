import os
import sys
import socket
import webbrowser
import threading
import time
import sqlite3
from datetime import datetime
from typing import Optional

# ─── Correção crítica para PyInstaller --noconsole ────────────────────────────
class DummyStream:
    def write(self, *a, **k): pass
    def writelines(self, *a, **k): pass
    def flush(self, *a, **k): pass
    def isatty(self, *a, **k): return False

if sys.stdout is None: sys.stdout = DummyStream()
if sys.stderr is None: sys.stderr = DummyStream()

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError

# ─── Auth Config ─────────────────────────────────────────────────────────────
import os as _os
SECRET_KEY = _os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")
ALGORITHM = "HS256"
# sha256_crypt é pure-Python → sem problemas no PyInstaller
pwd_ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

app = FastAPI(title="CPD Recebimentos API v2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# ─── Importa camadas de banco ─────────────────────────────────────────────────
from database import get_connection as get_sqlite, init_db, obter_ou_criar_data_fk as data_fk_sqlite

try:
    from cpd_mysql import get_connection as get_mysql, obter_ou_criar_data_fk as data_fk_mysql, init_mysql
    MYSQL_OK = True
except Exception as _e:
    MYSQL_OK = False
    print(f"[AVISO] MySQL não disponível: {_e}. Usando apenas SQLite.")

def get_conn():
    """Retorna conexão MySQL (preferencial) ou SQLite como fallback."""
    if MYSQL_OK:
        try:
            return get_mysql(), "mysql"
        except Exception:
            pass
    return get_sqlite(), "sqlite"

def get_data_fk(conn, data_str, mode):
    if mode == "mysql":
        return data_fk_mysql(conn, data_str)
    return data_fk_sqlite(conn, data_str)

def sql_ph(mode):
    """Retorna placeholder SQL correto por modo de banco."""
    return "%s" if mode == "mysql" else "?"

# ─── HTML Path ───────────────────────────────────────────────────────────────
def get_html_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "index.html")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

HTML_PATH = get_html_path()

# ─── Modelos Pydantic ─────────────────────────────────────────────────────────
class LoginInput(BaseModel):
    email: str
    senha: str

class CadastroUsuarioInput(BaseModel):
    nome: str
    email: str
    senha: str
    cargo: Optional[str] = "OPERADOR"

class RecebimentoInput(BaseModel):
    data: str
    loja_fk: int
    nota: str
    fornecedor_fk: int
    comprador_fk: Optional[int] = None
    recebedor_fk: Optional[int] = None
    tipo_entrega: Optional[str] = "CIF"
    tipo_carga: Optional[str] = None        # VOLUME | MIX | AMBOS
    hora_chegada: Optional[str] = None
    hora_liberado: Optional[str] = None
    hora_inicio_rec: Optional[str] = None
    hora_final_rec: Optional[str] = None
    sucesso_flag: int = 0
    status_fk: int
    setor_fk: Optional[int] = None
    ocorrencia_fk: Optional[int] = None
    resolucao: Optional[str] = None
    obs: Optional[str] = None

class AdminCadastroInput(BaseModel):
    tipo: str
    nome: str

class FornecedorInput(BaseModel):
    razao_social: str
    nome_fantasia: Optional[str] = None
    cnpj_cpf: Optional[str] = None

class ResolucaoInput(BaseModel):
    setor_fk: int
    ocorrencia_fk: int
    descricao_resolucao: str

# ─── Helpers ─────────────────────────────────────────────────────────────────
def calc_minutes(t1: Optional[str], t2: Optional[str]) -> Optional[int]:
    if not t1 or not t2:
        return None
    try:
        t1p = datetime.strptime(t1, "%H:%M")
        t2p = datetime.strptime(t2, "%H:%M")
        diff = (t2p - t1p).total_seconds()
        if diff < 0: diff += 86400
        return int(diff / 60)
    except Exception:
        return None

def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticação ausente.")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

def get_user_from_token(authorization: Optional[str] = Header(None)):
    """Retorna usuario_pk ou None (endpoints opcionais)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except Exception:
        return None

# ─── Rotas: Auth ─────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def get_form():
    try:
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception as e:
        return HTMLResponse(content=f"<h1>Erro: {e}</h1>", status_code=500)

@app.post("/api/auth/cadastro")
def cadastrar_usuario(item: CadastroUsuarioInput):
    conn, mode = get_conn()
    ph = sql_ph(mode)
    cur = conn.cursor() if mode == "sqlite" else conn.cursor(dictionary=True)
    try:
        senha_hash = pwd_ctx.hash(item.senha)
        cur.execute(
            f"INSERT INTO dim_usuario_cpd (nome, email, senha_hash, cargo) VALUES ({ph},{ph},{ph},{ph})",
            (item.nome, item.email, senha_hash, item.cargo)
        )
        conn.commit()
        return {"ok": True, "message": "Usuário cadastrado!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Erro: {e}")
    finally:
        cur.close(); conn.close()

@app.post("/api/auth/login")
def login(item: LoginInput):
    conn, mode = get_conn()
    ph = sql_ph(mode)
    cur = conn.cursor() if mode == "sqlite" else conn.cursor(dictionary=True)
    try:
        cur.execute(f"SELECT pk, nome, email, senha_hash, cargo, ativo FROM dim_usuario_cpd WHERE email = {ph}", (item.email,))
        row = cur.fetchone()
        if mode == "sqlite" and row:
            row = dict(row)
    finally:
        cur.close(); conn.close()

    if not row or not pwd_ctx.verify(item.senha, row["senha_hash"]):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")
    if not row["ativo"]:
        raise HTTPException(status_code=403, detail="Usuário inativo. Contate o administrador.")

    token = jwt.encode(
        {"sub": str(row["pk"]), "nome": row["nome"], "cargo": row["cargo"]},
        SECRET_KEY, algorithm=ALGORITHM
    )
    return {"token": token, "nome": row["nome"], "cargo": row["cargo"], "pk": row["pk"]}

@app.get("/api/auth/me")
def me(user=Depends(verify_token)):
    return user

# ─── Rotas: Opções ───────────────────────────────────────────────────────────
@app.get("/api/opcoes")
def get_options():
    conn, mode = get_conn()
    cur = conn.cursor() if mode == "sqlite" else conn.cursor(dictionary=True)
    ph = sql_ph(mode)
    try:
        def fetch(sql):
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

        lojas        = fetch("SELECT pk, nome_loja FROM dim_loja ORDER BY nome_loja")
        compradores  = fetch("SELECT pk, nome_comprador FROM dim_comprador ORDER BY nome_comprador")
        recebedores  = fetch("SELECT pk, nome_recebedor FROM dim_recebedor ORDER BY nome_recebedor")
        fornecedores = fetch("SELECT pk, razao_social, nome_fantasia, cnpj_cpf FROM dim_fornecedor ORDER BY razao_social")
        setores      = fetch("SELECT pk, nome_setor FROM dim_setor ORDER BY nome_setor")
        ocorrencias  = fetch("SELECT pk, descricao_ocorrencia FROM dim_ocorrencia ORDER BY descricao_ocorrencia")
        statuses     = fetch("SELECT pk, nome_status FROM dim_status ORDER BY nome_status")
        resolucoes   = fetch("SELECT pk, setor_fk, ocorrencia_fk, descricao_resolucao FROM dim_resolucao")
        usuarios     = fetch("SELECT pk, nome, cargo FROM dim_usuario_cpd WHERE ativo=1 ORDER BY nome")

        return {
            "lojas": lojas, "compradores": compradores, "recebedores": recebedores,
            "fornecedores": fornecedores, "setores": setores, "ocorrencias": ocorrencias,
            "statuses": statuses, "resolucoes": resolucoes, "usuarios": usuarios
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

# ─── Rotas: Recebimentos ──────────────────────────────────────────────────────
@app.get("/api/recebimentos")
def list_recebimentos(busca: Optional[str] = None, status: Optional[str] = None, limite: int = 100):
    conn, mode = get_conn()
    ph = sql_ph(mode)
    cur = conn.cursor() if mode == "sqlite" else conn.cursor(dictionary=True)
    try:
        sql = f"""
            SELECT
                f.fact_id, f.nota, f.obs, f.tipo_entrega, f.tipo_carga, f.sucesso_flag, f.resolucao,
                d.data_completa,
                l.nome_loja,
                forn.razao_social, forn.nome_fantasia,
                c.nome_comprador,
                rec.nome_recebedor,
                u.nome AS nome_usuario, u.cargo AS cargo_usuario,
                s.nome_setor, st.nome_status, o.descricao_ocorrencia,
                f.hora_chegada, f.hora_liberado, f.hora_inicio_rec, f.hora_final_rec,
                f.minutos_para_liberar_nfe, f.minutos_espera, f.minutos_recebimento,
                f.created_at
            FROM fact_recebimento f
            JOIN dim_data d       ON f.data_fk = d.pk
            JOIN dim_loja l       ON f.loja_fk = l.pk
            JOIN dim_fornecedor forn ON f.fornecedor_fk = forn.pk
            LEFT JOIN dim_comprador c  ON f.comprador_fk = c.pk
            LEFT JOIN dim_recebedor rec ON f.recebedor_fk = rec.pk
            LEFT JOIN dim_usuario_cpd u ON f.usuario_fk = u.pk
            LEFT JOIN dim_setor s      ON f.setor_fk = s.pk
            JOIN dim_status st         ON f.status_fk = st.pk
            LEFT JOIN dim_ocorrencia o ON f.ocorrencia_fk = o.pk
            WHERE 1=1
        """
        params = []
        if status:
            sql += f" AND st.nome_status = {ph}"
            params.append(status)
        if busca:
            q = f"%{busca}%"
            sql += f" AND (f.nota LIKE {ph} OR forn.razao_social LIKE {ph} OR forn.nome_fantasia LIKE {ph})"
            params.extend([q, q, q])
        sql += f" ORDER BY f.fact_id DESC LIMIT {ph}"
        params.append(limite)

        cur.execute(sql, params)
        rows = cur.fetchall()
        # Converter para dict e garantir strings em campos de hora/timestamp
        result = []
        for r in rows:
            d = dict(r)
            # Converter timedelta (MySQL retorna TIME como timedelta) para string HH:MM
            for field in ["hora_chegada", "hora_liberado", "hora_inicio_rec", "hora_final_rec"]:
                val = d.get(field)
                if val is not None and hasattr(val, "seconds"):
                    total = int(val.total_seconds())
                    h, m = divmod(total // 60, 60)
                    d[field] = f"{h:02d}:{m:02d}"
                elif val is not None:
                    d[field] = str(val)
            if d.get("created_at") and hasattr(d["created_at"], "strftime"):
                d["created_at"] = d["created_at"].strftime("%Y-%m-%d %H:%M")
            if d.get("data_completa") and hasattr(d["data_completa"], "strftime"):
                d["data_completa"] = d["data_completa"].strftime("%Y-%m-%d")
            result.append(d)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close(); conn.close()

@app.post("/api/recebimentos")
def create_recebimento(item: RecebimentoInput, usuario_pk=Depends(get_user_from_token)):
    conn, mode = get_conn()
    ph = sql_ph(mode)
    cur = conn.cursor() if mode == "sqlite" else conn.cursor(dictionary=True)

    min_liberar    = calc_minutes(item.hora_chegada, item.hora_liberado)
    min_espera     = calc_minutes(item.hora_chegada, item.hora_inicio_rec)
    min_recebimento = calc_minutes(item.hora_inicio_rec, item.hora_final_rec)

    try:
        data_fk = get_data_fk(conn, item.data, mode)
        cur.execute(f"""
            INSERT INTO fact_recebimento (
                nota, obs, tipo_entrega, tipo_carga, sucesso_flag, resolucao,
                data_fk, loja_fk, fornecedor_fk, comprador_fk, recebedor_fk, usuario_fk,
                setor_fk, status_fk, ocorrencia_fk,
                hora_chegada, hora_liberado, hora_inicio_rec, hora_final_rec,
                minutos_para_liberar_nfe, minutos_espera, minutos_recebimento
            ) VALUES ({','.join([ph]*22)})
        """, (
            item.nota, item.obs, item.tipo_entrega, item.tipo_carga,
            item.sucesso_flag, item.resolucao,
            data_fk, item.loja_fk, item.fornecedor_fk,
            item.comprador_fk, item.recebedor_fk,
            int(usuario_pk) if usuario_pk else None,
            item.setor_fk, item.status_fk, item.ocorrencia_fk,
            item.hora_chegada, item.hora_liberado, item.hora_inicio_rec, item.hora_final_rec,
            min_liberar, min_espera, min_recebimento
        ))
        conn.commit()
        return {"ok": True, "message": "Recebimento salvo com sucesso!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Erro de banco: {e}")
    finally:
        cur.close(); conn.close()

# ─── Rotas: Admin ─────────────────────────────────────────────────────────────
@app.post("/api/admin/cadastro")
def admin_cadastro(item: AdminCadastroInput):
    conn, mode = get_conn()
    ph = sql_ph(mode)
    cur = conn.cursor() if mode == "sqlite" else conn.cursor(dictionary=True)
    try:
        tabelas = {
            "loja":      ("dim_loja",      "nome_loja"),
            "comprador": ("dim_comprador", "nome_comprador"),
            "recebedor": ("dim_recebedor", "nome_recebedor"),
        }
        if item.tipo not in tabelas:
            raise HTTPException(status_code=400, detail="Tipo inválido")
        tab, col = tabelas[item.tipo]
        cur.execute(f"INSERT IGNORE INTO {tab} ({col}) VALUES ({ph})", (item.nome,))
        conn.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close(); conn.close()

@app.post("/api/admin/fornecedor")
def admin_fornecedor(item: FornecedorInput):
    conn, mode = get_conn()
    ph = sql_ph(mode)
    cur = conn.cursor() if mode == "sqlite" else conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"INSERT IGNORE INTO dim_fornecedor (razao_social, nome_fantasia, cnpj_cpf) VALUES ({ph},{ph},{ph})",
            (item.razao_social, item.nome_fantasia, item.cnpj_cpf)
        )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close(); conn.close()

@app.post("/api/admin/resolucao")
def admin_resolucao(item: ResolucaoInput):
    conn, mode = get_conn()
    ph = sql_ph(mode)
    cur = conn.cursor() if mode == "sqlite" else conn.cursor(dictionary=True)
    try:
        cur.execute(
            f"INSERT IGNORE INTO dim_resolucao (setor_fk, ocorrencia_fk, descricao_resolucao) VALUES ({ph},{ph},{ph})",
            (item.setor_fk, item.ocorrencia_fk, item.descricao_resolucao)
        )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close(); conn.close()

# ─── Inicialização do Servidor ────────────────────────────────────────────────
def find_free_port():
    s = socket.socket(); s.bind(('', 0)); p = s.getsockname()[1]; s.close(); return p

def start_browser(port):
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{port}")

if __name__ == "__main__":
    try:
        import uvicorn

        # Inicializa bancos
        init_db()           # SQLite (fallback)
        if MYSQL_OK:
            init_mysql()    # MySQL principal

        port = 8080
        try:
            s = socket.socket(); s.bind(('127.0.0.1', port)); s.close()
        except OSError:
            port = find_free_port()

        threading.Thread(target=start_browser, args=(port,), daemon=True).start()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    except Exception as e:
        import traceback
        path = r"C:\Users\Usuário\Desktop\formulario_cpd_error.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Erro:\n{e}\n\n"); traceback.print_exc(file=f)
        input("Pressione Enter para fechar...")
