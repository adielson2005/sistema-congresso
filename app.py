import os
import sqlite3
import bcrypt
from io import BytesIO
from flask import Flask, render_template, request, redirect, session, flash, jsonify, make_response
from xhtml2pdf import pisa

# =========================
# CONFIG
# =========================
DB_PATH = os.environ.get("DB_PATH", "database/banco.db")
db_dir = os.path.dirname(DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-secreta")


# =========================
# BANCO
# =========================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario TEXT UNIQUE,
            senha_hash BLOB,
            cargo TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS macros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS congregacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            macro_id INTEGER,
            UNIQUE(nome, macro_id),
            FOREIGN KEY (macro_id) REFERENCES macros(id)
        )
    """)

    cursor.execute("""
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS arrecadacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participante_id INTEGER,
            valor REAL,
            data_lancamento TEXT,
            observacao TEXT,
            FOREIGN KEY (participante_id) REFERENCES participantes(id)
        )
    """)

    # usuário admin padrão
    user = cursor.execute("""
        SELECT * FROM usuarios WHERE usuario = ?
    """, ("admin",)).fetchone()

    if not user:
        senha_hash = bcrypt.hashpw("123456".encode("utf-8"), bcrypt.gensalt())
        cursor.execute("""
            INSERT INTO usuarios (nome, usuario, senha_hash, cargo)
            VALUES (?, ?, ?, ?)
        """, ("Administrador", "admin", senha_hash, "admin"))

    # macros padrão
    macros = [
        "MACRO 1",
        "MACRO 2",
        "MACRO 3",
        "MACRO 4",
        "MACRO 5",
        "MACRO 6",
        "MACRO MISSª"
    ]

    for macro in macros:
        cursor.execute("INSERT OR IGNORE INTO macros (nome) VALUES (?)", (macro,))

    cursor.execute("SELECT id, nome FROM macros")
    macro_map = {row[1]: row[0] for row in cursor.fetchall()}

    dados_congregacoes = {
        "MACRO 1": [
            "Betesda", "El-Raah", "E. do Altíssimo",
            "Morada do Altíssimo", "Hebrom", "Shalom"
        ],
        "MACRO 2": [
            "Alto Refúgio", "Jardim de Deus", "Jardim Celeste",
            "Manancial de Vida", "Monte Carmelo", "Orvalho de Hermon",
            "Rosa de Sarom", "Cafarnaum", "Ebenezer", "Monte Ararate"
        ],
        "MACRO 3": [
            "Betânia", "Deus Forte", "Monte Hermon",
            "Monte Santo", "Monte Sinai", "Rio Jordão"
        ],
        "MACRO 4": [
            "Adonai", "Fonte de Luz", "Gileade",
            "Rocha Eterna", "Vitória da Fé", "Monte Horebe",
            "Nova Jerusalém"
        ],
        "MACRO 5": [
            "Monte das Oliveiras", "Monte Sião", "Nova Canaã",
            "Porta do Céu", "Nova Aliança", "Filadélfia",
            "Fonte de Águas Vivas"
        ],
        "MACRO 6": [
            "Betel", "Monte Tabor", "Nova Sião", "Pioneira",
            "Monte Moriá", "Getsêmani", "Joia de Cristo",
            "Maranata", "Nova Vida", "Porta Formosa"
        ],
        "MACRO MISSª": [
            "Luz do Mundo", "Vale de Benção", "Lírio dos Vales"
        ]
    }

    for macro_nome, congregacoes in dados_congregacoes.items():
        macro_id = macro_map.get(macro_nome)
        if macro_id:
            for nome in congregacoes:
                cursor.execute("""
                    INSERT OR IGNORE INTO congregacoes (nome, macro_id)
                    VALUES (?, ?)
                """, (nome, macro_id))

    conn.commit()
    conn.close()


init_db()


# =========================
# ROTAS BÁSICAS
# =========================
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
            senha_hash = user["senha_hash"]
            if bcrypt.checkpw(senha.encode("utf-8"), senha_hash):
                session["user_id"] = user["id"]
                session["nome"] = user["nome"]
                session["cargo"] = user["cargo"]
                return redirect("/dashboard")
            flash("Senha incorreta.", "danger")
            return redirect("/login")

        flash("Usuário não encontrado.", "danger")
        return redirect("/login")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# DASHBOARD
# =========================
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

    arrecadacao_por_congregacao = conn.execute("""
        SELECT participantes.congregacao, COALESCE(SUM(arrecadacoes.valor), 0) AS total
        FROM participantes
        LEFT JOIN arrecadacoes ON arrecadacoes.participante_id = participantes.id
        GROUP BY participantes.congregacao
        ORDER BY total DESC
        LIMIT 10
    """).fetchall()

    arrecadacao_por_macro = conn.execute("""
        SELECT macros.nome AS macro, COALESCE(SUM(arrecadacoes.valor), 0) AS total
        FROM macros
        LEFT JOIN congregacoes ON congregacoes.macro_id = macros.id
        LEFT JOIN participantes ON participantes.congregacao = congregacoes.nome
        LEFT JOIN arrecadacoes ON arrecadacoes.participante_id = participantes.id
        GROUP BY macros.id, macros.nome
        ORDER BY macros.nome
    """).fetchall()

    evolucao_arrecadacao = conn.execute("""
        SELECT data_lancamento, COALESCE(SUM(valor), 0) AS total
        FROM arrecadacoes
        GROUP BY data_lancamento
        ORDER BY data_lancamento ASC
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_participantes=total_participantes,
        total_arrecadado=total_arrecadado,
        total_lancamentos=total_lancamentos,
        ultimas_arrecadacoes=ultimas_arrecadacoes,
        arrecadacao_por_congregacao=arrecadacao_por_congregacao,
        arrecadacao_por_macro=arrecadacao_por_macro,
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
        {"data": item["data_lancamento"], "total": float(item["total"])}
        for item in evolucao
    ])


# =========================
# PARTICIPANTES
# =========================
@app.route("/participantes")
def participantes():
    if "user_id" not in session:
        return redirect("/login")

    busca = request.args.get("busca", "").strip()
    macro = request.args.get("macro", "").strip()
    congregacao = request.args.get("congregacao", "").strip()

    conn = get_db()

    query = "SELECT * FROM participantes WHERE 1=1"
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
        params.extend([termo, termo, termo, termo, termo, termo])

    if macro:
        query += " AND congregacao IN (SELECT nome FROM congregacoes WHERE macro_id = ?)"
        params.append(macro)

    if congregacao:
        query += " AND congregacao = ?"
        params.append(congregacao)

    query += " ORDER BY id DESC"

    lista_participantes = conn.execute(query, params).fetchall()

    macros = conn.execute("""
        SELECT * FROM macros
        ORDER BY nome
    """).fetchall()

    congregacoes = conn.execute("""
        SELECT DISTINCT nome
        FROM congregacoes
        ORDER BY nome
    """).fetchall()

    conn.close()

    return render_template(
        "participantes.html",
        participantes=lista_participantes,
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
                INSERT INTO participantes (
                    nome_completo, data_nascimento, cpf, email, numero, nome_mae, congregacao
                )
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
            flash("Participante cadastrado com sucesso!", "success")
        except sqlite3.IntegrityError:
            conn.close()
            flash("CPF já cadastrado. Verifique os dados.", "danger")
            return redirect("/participantes/cadastrar")

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
        flash("Participante não encontrado.", "danger")
        return redirect("/participantes")

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
            flash("Participante atualizado com sucesso!", "success")
        except sqlite3.IntegrityError:
            conn.close()
            flash("CPF já cadastrado em outro participante.", "danger")
            return redirect(f"/participantes/{id}/editar")

        conn.close()
        return redirect(f"/participantes/{id}")

    macros = conn.execute("""
        SELECT * FROM macros
        ORDER BY nome
    """).fetchall()

    conn.close()

    return render_template(
        "editar_participante.html",
        participante=participante,
        macros=macros
    )


@app.route("/participantes/<int:id>/excluir", methods=["POST"])
def excluir_participante(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    conn.execute("DELETE FROM arrecadacoes WHERE participante_id = ?", (id,))
    conn.execute("DELETE FROM participantes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Participante excluído com sucesso.", "success")
    return redirect("/participantes")


# =========================
# CONGREGAÇÕES
# =========================
@app.route("/api/congregacoes/<int:macro_id>")
def api_congregacoes(macro_id):
    if "user_id" not in session:
        return jsonify([])

    conn = get_db()
    congregacoes = conn.execute("""
        SELECT DISTINCT id, nome
        FROM congregacoes
        WHERE macro_id = ?
        ORDER BY nome
    """, (macro_id,)).fetchall()
    conn.close()

    return jsonify([
        {"id": c["id"], "nome": c["nome"]}
        for c in congregacoes
    ])


@app.route("/congregacoes")
def congregacoes():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    lista_congregacoes = conn.execute("""
        SELECT congregacoes.nome, macros.nome AS macro_nome,
               COUNT(participantes.id) AS total_participantes
        FROM congregacoes
        JOIN macros ON macros.id = congregacoes.macro_id
        LEFT JOIN participantes ON participantes.congregacao = congregacoes.nome
        GROUP BY congregacoes.id, congregacoes.nome, macros.nome
        ORDER BY macros.nome, congregacoes.nome
    """).fetchall()

    conn.close()

    return render_template("congregacoes.html", congregacoes=lista_congregacoes)


@app.route("/congregacoes/<nome_slug>")
def detalhe_congregacao(nome_slug):
    if "user_id" not in session:
        return redirect("/login")

    nome_congregacao = nome_slug.replace("-", " ")

    conn = get_db()

    participantes_da_congregacao = conn.execute("""
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
        participantes=participantes_da_congregacao
    )


# =========================
# ARRECADAÇÕES
# =========================
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

    flash("Arrecadação registrada com sucesso!", "success")
    return redirect(f"/participantes/{id}")


@app.route("/arrecadacoes/<int:id>/editar", methods=["GET", "POST"])
def editar_arrecadacao(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    arrecadacao = conn.execute("""
        SELECT * FROM arrecadacoes
        WHERE id = ?
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

        flash("Arrecadação atualizada com sucesso!", "success")
        return redirect(f"/participantes/{participante_id}")

    conn.close()
    return render_template("editar_arrecadacao.html", arrecadacao=arrecadacao)


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
    conn.execute("DELETE FROM arrecadacoes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    flash("Arrecadação excluída com sucesso!", "success")
    return redirect(f"/participantes/{participante_id}")


# =========================
# RELATÓRIOS
# =========================
@app.route("/relatorios")
def relatorios():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    data_inicio = request.args.get("data_inicio", "").strip()
    data_fim = request.args.get("data_fim", "").strip()
    congregacao = request.args.get("congregacao", "").strip()
    macro = request.args.get("macro", "").strip()

    filtro = "WHERE 1=1"
    params = []

    if data_inicio:
        filtro += " AND data_lancamento >= ?"
        params.append(data_inicio)

    if data_fim:
        filtro += " AND data_lancamento <= ?"
        params.append(data_fim)

    if congregacao:
        filtro += " AND participantes.congregacao = ?"
        params.append(congregacao)

    if macro:
        filtro += """
            AND participantes.congregacao IN (
                SELECT nome FROM congregacoes
                WHERE macro_id = (SELECT id FROM macros WHERE nome = ?)
            )
        """
        params.append(macro)

    total = conn.execute(f"""
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        {filtro}
    """, params).fetchone()["total"]

    total_lancamentos = conn.execute(f"""
        SELECT COUNT(*) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        {filtro}
    """, params).fetchone()["total"]

    por_congregacao = conn.execute(f"""
        SELECT participantes.congregacao, COALESCE(SUM(valor), 0) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        {filtro}
        GROUP BY participantes.congregacao
        ORDER BY total DESC
    """, params).fetchall()

    por_macro = conn.execute(f"""
        SELECT macros.nome AS macro, COALESCE(SUM(valor), 0) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        JOIN congregacoes ON congregacoes.nome = participantes.congregacao
        JOIN macros ON macros.id = congregacoes.macro_id
        {filtro}
        GROUP BY macros.nome
        ORDER BY total DESC
    """, params).fetchall()

    macros = conn.execute("""
        SELECT * FROM macros
        ORDER BY nome
    """).fetchall()

    congregacoes = conn.execute("""
        SELECT DISTINCT nome
        FROM congregacoes
        ORDER BY nome
    """).fetchall()

    conn.close()

    return render_template(
        "relatorios.html",
        total=total,
        total_lancamentos=total_lancamentos,
        por_congregacao=por_congregacao,
        por_macro=por_macro,
        macros=macros,
        congregacoes=congregacoes
    )

@app.route("/relatorios/pdf")
def relatorios_pdf():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    data_inicio = request.args.get("data_inicio", "").strip()
    data_fim = request.args.get("data_fim", "").strip()
    congregacao = request.args.get("congregacao", "").strip()
    macro = request.args.get("macro", "").strip()

    filtro = "WHERE 1=1"
    params = []

    if data_inicio:
        filtro += " AND data_lancamento >= ?"
        params.append(data_inicio)

    if data_fim:
        filtro += " AND data_lancamento <= ?"
        params.append(data_fim)

    if congregacao:
        filtro += " AND participantes.congregacao = ?"
        params.append(congregacao)

    if macro:
        filtro += """
            AND participantes.congregacao IN (
                SELECT nome FROM congregacoes
                WHERE macro_id = (SELECT id FROM macros WHERE nome = ?)
            )
        """
        params.append(macro)

    total = conn.execute(f"""
        SELECT COALESCE(SUM(valor), 0) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        {filtro}
    """, params).fetchone()["total"]

    total_lancamentos = conn.execute(f"""
        SELECT COUNT(*) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        {filtro}
    """, params).fetchone()["total"]

    por_congregacao = conn.execute(f"""
        SELECT participantes.congregacao, COALESCE(SUM(valor), 0) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        {filtro}
        GROUP BY participantes.congregacao
        ORDER BY total DESC
    """, params).fetchall()

    por_macro = conn.execute(f"""
        SELECT macros.nome AS macro, COALESCE(SUM(valor), 0) AS total
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        JOIN congregacoes ON congregacoes.nome = participantes.congregacao
        JOIN macros ON macros.id = congregacoes.macro_id
        {filtro}
        GROUP BY macros.nome
        ORDER BY total DESC
    """, params).fetchall()

    detalhes = conn.execute(f"""
        SELECT participantes.nome_completo, participantes.congregacao, arrecadacoes.valor, arrecadacoes.data_lancamento, arrecadacoes.observacao
        FROM arrecadacoes
        JOIN participantes ON participantes.id = arrecadacoes.participante_id
        {filtro}
        ORDER BY arrecadacoes.data_lancamento DESC, arrecadacoes.id DESC
    """, params).fetchall()

    conn.close()

    html = f"""
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            font-size: 12px;
            color: #111;
        }}

        .topo {{
            text-align: center;
            margin-bottom: 20px;
            border-bottom: 2px solid #ccc;
            padding-bottom: 10px;
        }}

        h1, h2, h3 {{
            margin: 0 0 10px 0;
        }}

        .resumo {{
            margin-bottom: 20px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}

        th, td {{
            border: 1px solid #ccc;
            padding: 6px;
            text-align: left;
        }}

        th {{
            background: #f2f2f2;
        }}

        .small {{
            color: #555;
            font-size: 11px;
        }}
    </style>
</head>

<body>

    <div class="topo">
        <h1>Sistema Cadepa</h1>
        <h3>Relatório de Arrecadação</h3>
        <p class="small">Sistema de gestão do congresso</p>
    </div>

    <div class="resumo">
        <h3>Resumo</h3>
        <p><strong>Total arrecadado:</strong> R$ {total:.2f}</p>
        <p><strong>Total de lançamentos:</strong> {total_lancamentos}</p>
        <p><strong>Filtro data início:</strong> {data_inicio or '-'}</p>
        <p><strong>Filtro data fim:</strong> {data_fim or '-'}</p>
        <p><strong>Filtro macro:</strong> {macro or '-'}</p>
        <p><strong>Filtro congregação:</strong> {congregacao or '-'}</p>
    </div>

    <h3>Detalhamento das Arrecadações</h3>

    <table>
        <tr>
            <th>Participante</th>
            <th>Congregação</th>
            <th>Valor</th>
            <th>Data</th>
            <th>Observação</th>
        </tr>
"""

    for d in detalhes:
        html += f"""
        <tr>
            <td>{d['nome_completo']}</td>
            <td>{d['congregacao']}</td>
            <td>R$ {d['valor']:.2f}</td>
            <td>{d['data_lancamento']}</td>
            <td>{d['observacao'] or '-'}</td>
        </tr>
"""

    html += """
        </table>
    </body>
    </html>
    """

    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf)

    if pisa_status.err:
        return "Erro ao gerar PDF"

    response = make_response(pdf.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=relatorio_arrecadacao.pdf"
    return response


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)