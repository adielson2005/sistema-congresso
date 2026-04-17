import os
from flask import Flask, render_template, request, redirect, session, flash, jsonify, send_from_directory
import sqlite3
import bcrypt
from datetime import datetime


os.makedirs("database", exist_ok=True)

def init_db():
    conn = sqlite3.connect("database/banco.db")
    # cria tabelas
    conn.close()

    init_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario TEXT UNIQUE,
            senha_hash BLOB,
            cargo TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS participantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT,
            data_nascimento TEXT,
            cpf TEXT UNIQUE,
            email TEXT,
            numero TEXT,
            nome_mae TEXT,
            congregacao TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS arrecadacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participante_id INTEGER,
            valor REAL,
            data_lancamento TEXT,
            observacao TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS macros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS congregacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            macro_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS historico_alteracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participante_id INTEGER,
            campo_alterado TEXT,
            valor_antigo TEXT,
            valor_novo TEXT,
            alterado_por TEXT,
            data_alteracao TEXT
        )
    """)

    cursor = conn.cursor()

    user = cursor.execute("""
        SELECT * FROM usuarios WHERE usuario = 'admin'
    """).fetchone()

    if not user:
        senha_hash = bcrypt.hashpw("123456".encode("utf-8"), bcrypt.gensalt())

        conn.execute("""
            INSERT INTO usuarios (nome, usuario, senha_hash, cargo)
            VALUES (?, ?, ?, ?)
        """, ("Administrador", "admin", senha_hash, "admin"))

    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = "chave-secreta"

init_db()

def get_db():
    conn = sqlite3.connect("database/banco.db")
    conn.row_factory = sqlite3.Row
    return conn

def obter_filtros_relatorio(args):
    return {
        "data_inicio": (args.get("data_inicio") or "").strip(),
        "data_fim": (args.get("data_fim") or "").strip(),
        "congregacao": (args.get("congregacao") or "").strip(),
        "macro": (args.get("macro") or "").strip()
    }

def consultar_dados_relatorio(conn, filtros):
    clausulas = ["1=1"]
    params = []

    if filtros["data_inicio"]:
        clausulas.append("arrecadacoes.data_lancamento >= ?")
        params.append(filtros["data_inicio"])

    if filtros["data_fim"]:
        clausulas.append("arrecadacoes.data_lancamento <= ?")
        params.append(filtros["data_fim"])

    if filtros["congregacao"]:
        clausulas.append("participantes.congregacao = ?")
        params.append(filtros["congregacao"])

    if filtros["macro"]:
        clausulas.append("macros.nome = ?")
        params.append(filtros["macro"])

    filtro = "WHERE " + " AND ".join(clausulas)

    total = conn.execute(f"""
        SELECT COALESCE(SUM(arrecadacoes.valor), 0) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        LEFT JOIN congregacoes ON congregacoes.nome = participantes.congregacao
        LEFT JOIN macros ON macros.id = congregacoes.macro_id
        {filtro}
    """, params).fetchone()["total"]

    total_lancamentos = conn.execute(f"""
        SELECT COUNT(*) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        LEFT JOIN congregacoes ON congregacoes.nome = participantes.congregacao
        LEFT JOIN macros ON macros.id = congregacoes.macro_id
        {filtro}
    """, params).fetchone()["total"]

    por_congregacao = conn.execute(f"""
        SELECT
            COALESCE(participantes.congregacao, 'Sem congregação') AS congregacao,
            COALESCE(SUM(arrecadacoes.valor), 0) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        LEFT JOIN congregacoes ON congregacoes.nome = participantes.congregacao
        LEFT JOIN macros ON macros.id = congregacoes.macro_id
        {filtro}
        GROUP BY participantes.congregacao
        ORDER BY total DESC, congregacao ASC
    """, params).fetchall()

    por_macro = conn.execute(f"""
        SELECT
            COALESCE(macros.nome, 'Sem macro') AS macro,
            COALESCE(SUM(arrecadacoes.valor), 0) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        LEFT JOIN congregacoes ON congregacoes.nome = participantes.congregacao
        LEFT JOIN macros ON macros.id = congregacoes.macro_id
        {filtro}
        GROUP BY macros.nome
        ORDER BY total DESC, macro ASC
    """, params).fetchall()

    return {
        "total": float(total or 0),
        "total_lancamentos": int(total_lancamentos or 0),
        "melhor_congregacao": por_congregacao[0]["congregacao"] if por_congregacao else "Sem dados",
        "melhor_congregacao_total": float(por_congregacao[0]["total"] or 0) if por_congregacao else 0.0,
        "por_congregacao": [
            {
                "congregacao": item["congregacao"],
                "total": float(item["total"] or 0)
            }
            for item in por_congregacao
        ],
        "por_macro": [
            {
                "macro": item["macro"],
                "total": float(item["total"] or 0)
            }
            for item in por_macro
        ],
        "filtros": filtros,
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conn = get_db()
        user = conn.execute("""
            SELECT * FROM usuarios
            WHERE usuario = ?
        """, (usuario,)).fetchone()
        conn.close()

        if user:
            if bcrypt.checkpw(senha.encode("utf-8"), user["senha_hash"]):
                session["user_id"] = user["id"]
                session["nome"] = user["nome"]
                session["cargo"] = user["cargo"]
                return redirect("/dashboard")
            else:
                return "Senha incorreta"
        else:
            return "Usuário não encontrado"

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    total_participantes = conn.execute("""
        SELECT COUNT(*) AS total FROM participantes
    """).fetchone()["total"]

    total_arrecadado = conn.execute("""
        SELECT COALESCE(SUM(valor), 0) AS total FROM arrecadacoes
    """).fetchone()["total"]

    total_lancamentos = conn.execute("""
        SELECT COUNT(*) AS total FROM arrecadacoes
    """).fetchone()["total"]

    ultimas_arrecadacoes = conn.execute("""
        SELECT arrecadacoes.*, participantes.nome_completo
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        ORDER BY arrecadacoes.id DESC
        LIMIT 5
    """).fetchall()

    arrecadacoes_por_congregacao = conn.execute("""
        SELECT
            COALESCE(participantes.congregacao, 'Sem congregação') AS congregacao,
            COALESCE(SUM(arrecadacoes.valor), 0) AS total
        FROM participantes
        LEFT JOIN arrecadacoes ON arrecadacoes.participante_id = participantes.id
        GROUP BY participantes.congregacao
        ORDER BY total DESC
    """).fetchall()

    arrecadacoes_por_macro = conn.execute("""
        SELECT
            macros.nome AS macro,
            COALESCE(SUM(arrecadacoes.valor), 0) AS total
        FROM macros
        LEFT JOIN congregacoes ON congregacoes.macro_id = macros.id
        LEFT JOIN participantes ON participantes.congregacao = congregacoes.nome
        LEFT JOIN arrecadacoes ON arrecadacoes.participante_id = participantes.id
        GROUP BY macros.id, macros.nome
        ORDER BY total DESC, macros.nome ASC
    """).fetchall()

    evolucao_arrecadacao = conn.execute("""
        SELECT data_lancamento, COALESCE(SUM(valor), 0) AS total
        FROM arrecadacoes
        GROUP BY data_lancamento
        ORDER BY data_lancamento ASC
    """).fetchall()

    conn.close()

    return render_template(
        "Dashboard.html",
        total_participantes=total_participantes,
        total_arrecadado=total_arrecadado,
        total_lancamentos=total_lancamentos,
        ultimas_arrecadacoes=ultimas_arrecadacoes,
        arrecadacoes_por_congregacao=arrecadacoes_por_congregacao,
        arrecadacoes_por_macro=arrecadacoes_por_macro,
        evolucao_arrecadacao=evolucao_arrecadacao
    )

@app.route("/api/dashboard/evolucao")
def api_dashboard_evolucao():
    if "user_id" not in session:
        return jsonify([])
    
    conn = get_db()

    evolucao = conn.execute("""
        SELECT data_lancamento, COALESCE(SUM(valor), 0) AS total
        FROM arrecadacoes
        GROUP BY data_lancamento
        ORDER BY data_lancamento ASC
    """).fetchall()

    conn.close()

    return jsonify([
        {
            "data":
item["data_lancamento"],
            "total":
float(item["total"])
        }
        for item in evolucao
    ])


@app.route("/participantes")
def participantes():
    if "user_id" not in session:
        return redirect("/login")

    busca = request.args.get("busca", "").strip()
    macro = request.args.get("macro", "").strip()
    congregacao = request.args.get("congregacao", "").strip()

    conn = get_db()

    query = """
        SELECT * FROM participantes
        WHERE 1=1
    """
    params = []

    if busca:
        query += """
            AND (
                nome_completo LIKE ?
                OR cpf LIKE ?
                OR email LIKE ?
                OR numero LIKE ?
                OR nome_mae LIKE ?
                OR congregacao LIKE ?
            )
        """
        termo = f"%{busca}%"
        params.extend([termo] *6)

    if macro:
        query += " AND congregacao IN (SELECT nome FROM congregacoes WHERE macro_id = ?)"
        params.append(macro)

    if congregacao:
        query += "AND congregacao = ?"
        params.append(congregacao)

    query += " ORDER BY id DESC"

    participantes = conn.execute(query, params).fetchall()

    macros = conn.execute("SELECT * FROM macros ORDER BY nome").fetchall()
    congregacoes = conn.execute("SELECT * FROM congregacoes ORDER BY nome").fetchall()

    conn.close()

    return render_template(
        "participantes.html",
        participantes=participantes,
        busca=busca,
        macros=macros,
        congregacoes=congregacoes,
        macro_selecionada=macro,
        congregacao_selecionada=congregacao
    )


@app.route("/participantes/cadastrar", methods=["GET", "POST"])
def cadastrar_participante():
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()

    if request.method == "POST":
        nome_completo = request.form["nome_completo"]
        data_nascimento = request.form["data_nascimento"]
        cpf = request.form["cpf"]
        email = request.form["email"]
        numero = request.form["numero"]
        nome_mae = request.form["nome_mae"]
        congregacao = request.form["congregacao"]

        try:
            conn.execute("""
                INSERT INTO participantes (nome_completo, data_nascimento, cpf, email, numero, nome_mae, congregacao)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                nome_completo,
                data_nascimento,
                cpf,
                email,
                numero,
                nome_mae,
                congregacao
            ))
            conn.commit()
            flash("Participante cadastrado com sucesso!", "sucess")
        except sqlite3.IntegrityError:
            conn.close()
            flash("CPF já cadastrado. Verifique os dados.", "danger")
            return redirect ("/participantes/cadastrar")
        
        conn.close()
        return redirect("/participantes")

    macros = conn.execute("""
        SELECT * FROM macros
        ORDER BY nome
    """).fetchall()
    conn.close()

    return render_template("cadastrar_participante.html", macros=macros)

@app.route("/participantes/<int:id>")
def detalhe_participante(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    participante = conn.execute("""
        SELECT * FROM participantes
        WHERE id = ?
    """, (id,)).fetchone()

    arrecadacoes = conn.execute("""
        SELECT * FROM arrecadacoes
        WHERE participante_id = ?
        ORDER BY id DESC
    """, (id,)).fetchall()

    total = conn.execute("""
        SELECT COALESCE(SUM(valor), 0) AS total_arrecadado
        FROM arrecadacoes
        WHERE participante_id = ?
    """, (id,)).fetchone()

    conn.close()

    if not participante:
        return "Participante não encontrado"

    return render_template(
        "detalhe_participante.html",
        participante=participante,
        arrecadacoes=arrecadacoes,
        total=total["total_arrecadado"]
    )

@app.route("/arrecadacoes/<int:id>/excluir", methods=["POST"])
def excluir_arrecadacao(id):
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db()

    registro = conn.execute("""
        SELECT participante_id FROM arrecadacoes WHERE id = ?
    """, (id,)).fetchone()

    if not registro:
        conn.close()
        return "Registro não encontrado"
    
    participante_id = registro["participante_id"]

    conn.execute("""DELETE FROM arrecadacoes WHERE id = ?""", (id,))
    conn.commit()
    conn.close()

    return redirect(f"/participantes/{participante_id}")

@app.route("/arrecadacoes/<int:id>/editar", methods=["GET", "POST"])
def editar_arrecadacao(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    arrecadacao = conn.execute("""
        SELECT * FROM arrecadacoes WHERE id = ?
    """, (id,)).fetchone()

    if not arrecadacao:
        conn.close()
        return "Registro não encontrado"

    if request.method == "POST":
        valor = request.form["valor"]
        data_lancamento = request.form["data_lancamento"]
        observacao = request.form["observacao"]

        conn.execute("""
            UPDATE arrecadacoes
            SET valor = ?, data_lancamento = ?, observacao = ?
            WHERE id = ?
        """, (valor, data_lancamento, observacao, id))

        conn.commit()

        participante_id = arrecadacao["participante_id"]
        conn.close()

        return redirect(f"/participantes/{participante_id}")

    conn.close()
    return render_template("editar_arrecadacao.html", arrecadacao=arrecadacao)

@app.route("/api/congregacoes/<int:macro_id>")
def api_congregacoes(macro_id):
    if "user_id" not in session:
        return jsonify([])

    conn = get_db()
    congregacoes = conn.execute("""
        SELECT id, nome
        FROM congregacoes
        WHERE macro_id = ?
        ORDER BY nome
    """, (macro_id,)).fetchall()
    conn.close()

    return jsonify([
        {"id": c["id"], "nome": c["nome"]}
        for c in congregacoes
    ])

@app.route("/congregacoes/<nome_slug>")
def detalhe_congregacao(nome_slug):
    if "user_id" not in session:
        return redirect("/login")

    nome_congregacao = nome_slug.replace("-", " ")

    conn = get_db()

    participantes = conn.execute("""
        SELECT * FROM participantes
        WHERE congregacao = ?
        ORDER BY nome_completo ASC
    """, (nome_congregacao,)).fetchall()

    congregacao_info = conn.execute("""
        SELECT congregacoes.nome, macros.nome AS macro_nome
        FROM congregacoes
        JOIN macros ON macros.id = congregacoes.macro_id
        WHERE congregacoes.nome = ?
    """, (nome_congregacao,)).fetchone()

    conn.close()

    if not congregacao_info:
        return "Congregação não encontrada."

    return render_template(
        "detalhe_congregacao.html",
        congregacao=congregacao_info["nome"],
        macro=congregacao_info["macro_nome"],
        participantes=participantes
    )

@app.route("/congregacoes")
def congregacoes():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    congregacoes = conn.execute("""
        SELECT congregacoes.nome, macros.nome AS macro_nome,
               COUNT(participantes.id) AS total_participantes
        FROM congregacoes
        JOIN macros ON macros.id = congregacoes.macro_id
        LEFT JOIN participantes ON participantes.congregacao = congregacoes.nome
        GROUP BY congregacoes.id, congregacoes.nome, macros.nome
        ORDER BY macros.nome, congregacoes.nome
    """).fetchall()

    conn.close()

    return render_template("congregacoes.html", congregacoes=congregacoes)

@app.route("/participantes/<int:id>/arrecadar", methods=["POST"])
def salvar_arrecadacao(id):
    if "user_id" not in session:
        return redirect("/login")

    valor = request.form["valor"]
    data_lancamento = request.form["data_lancamento"]
    observacao = request.form["observacao"]

    conn = get_db()
    conn.execute("""
        INSERT INTO arrecadacoes (participante_id, valor, data_lancamento, observacao)
        VALUES (?, ?, ?, ?)
    """, (id, valor, data_lancamento, observacao))
    conn.commit()
    conn.close()

    return redirect(f"/participantes/{id}")


@app.route("/participantes/<int:id>/editar", methods=["GET", "POST"])
def editar_participante(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    participante = conn.execute("""
        SELECT * FROM participantes
        WHERE id = ?
    """, (id,)).fetchone()

    if not participante:
        conn.close()
        return "Participante não encontrado"

    if request.method == "POST":
        nome_completo = request.form["nome_completo"]
        data_nascimento = request.form["data_nascimento"]
        cpf = request.form["cpf"]
        email = request.form["email"]
        numero = request.form["numero"]
        nome_mae = request.form["nome_mae"]
        congregacao = request.form["congregacao"]

        campos = {
            "nome_completo": nome_completo,
            "data_nascimento": data_nascimento,
            "cpf": cpf,
            "email": email,
            "numero": numero,
            "nome_mae": nome_mae,
            "congregacao": congregacao
        }

        for campo, valor in campos.items():
            valor_antigo = participante[campo]
            if str(valor_antigo or "") != str(valor or ""):
                conn.execute("""
                    INSERT INTO historico_alteracoes (
                        participante_id,
                        campo_alterado,
                        valor_antigo,
                        valor_novo,
                        alterado_por,
                        data_alteracao
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    id,
                    campo,
                    str(valor_antigo or ""),
                    str(valor or ""),
                    session.get("nome", "Sistema"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
        try:
            conn.execute("""
                UPDATE participantes
                SET nome_completo = ?, data_nascimento = ?, cpf = ?, email = ?, numero = ?, nome_mae = ?, congregacao = ?
                WHERE id = ?
            """, (
                nome_completo,
                data_nascimento,
                cpf,
                email,
                numero,
                nome_mae,
                congregacao,
                id
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "CPF já cadastrado em outro participante"

        conn.close()
        return redirect(f"/participantes/{id}")

    conn.close()
    return render_template("editar_participante.html", participante=participante)

@app.route("/participantes/<int:id>/excluir", methods=["POST"])
def excluir_participante(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    conn.execute("DELETE FROM arrecadacoes WHERE participante_id = ?", (id,))
    conn.execute("DELETE FROM participantes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/participantes")

@app.route("/relatorios")
def relatorios():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    filtros = obter_filtros_relatorio(request.args)

    macros = conn.execute("""
        SELECT nome
        FROM macros
        ORDER BY nome ASC
    """).fetchall()

    congregacoes = conn.execute("""
        SELECT nome
        FROM congregacoes
        ORDER BY nome ASC
    """).fetchall()
    relatorio = consultar_dados_relatorio(conn, filtros)

    conn.close()

    return render_template(
        "relatorios.html",
        total=relatorio["total"],
        total_lancamentos=relatorio["total_lancamentos"],
        por_congregacao=relatorio["por_congregacao"],
        por_macro=relatorio["por_macro"],
        melhor_congregacao=relatorio["melhor_congregacao"],
        melhor_congregacao_total=relatorio["melhor_congregacao_total"],
        atualizado_em=relatorio["atualizado_em"],
        macros=macros,
        congregacoes=congregacoes,
        filtro_data_inicio=filtros["data_inicio"],
        filtro_data_fim=filtros["data_fim"],
        filtro_congregacao=filtros["congregacao"],
        filtro_macro=filtros["macro"]
    )

@app.route("/api/relatorios")
def api_relatorios():
    if "user_id" not in session:
        return jsonify({"erro": "nao_autorizado"}), 401

    conn = get_db()
    filtros = obter_filtros_relatorio(request.args)
    relatorio = consultar_dados_relatorio(conn, filtros)
    conn.close()

    return jsonify(relatorio)
                                                                                  
@app.route("/sw.js")
def service_worker():
    """Serve o service worker no escopo raiz para que controle todas as páginas."""
    response = send_from_directory("static", "sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)