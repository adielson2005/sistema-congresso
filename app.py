from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import bcrypt
from flask import jsonify

app = Flask(__name__)
app.secret_key = "chave-secreta"

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

    conn = get_db()

    if busca:
        participantes = conn.execute("""
            SELECT * FROM participantes
            WHERE nome_completo LIKE ?
            ORDER BY id DESC
        """, (f"%{busca}%",)).fetchall()
    else:
        participantes = conn.execute("""
            SELECT * FROM participantes
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    return render_template("participantes.html", participantes=participantes, busca=busca)

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
    app.run(debug=True)