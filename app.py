import os
from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import bcrypt
from flask import jsonify

os.makedirs("database", exist_ok=True)

def init_db():
    conn = sqlite3.connect("database/banco.db")

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

    # criar usuário padrão
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

    conn.close()

    return render_template(
        "dashboard.html",
        total_participantes=total_participantes,
        total_arrecadado=total_arrecadado,
        total_lancamentos=total_lancamentos,
        ultimas_arrecadacoes=ultimas_arrecadacoes
    )

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

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)