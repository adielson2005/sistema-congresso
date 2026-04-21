import os
import sqlite3
import bcrypt
from getpass import getpass

conn = sqlite3.connect("database/banco.db")
cursor = conn.cursor()

nome = os.environ.get("NOVO_USUARIO_NOME") or input("Nome do usuário: ").strip()
usuario = os.environ.get("NOVO_USUARIO_LOGIN") or input("Login do usuário: ").strip()
senha = os.environ.get("NOVO_USUARIO_SENHA") or getpass("Senha do usuário: ")
cargo = os.environ.get("NOVO_USUARIO_CARGO") or input("Cargo [admin]: ").strip() or "admin"

if not nome or not usuario or not senha:
    raise ValueError("Nome, login e senha são obrigatórios.")

senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())

cursor.execute("""
INSERT INTO usuarios (nome, usuario, senha_hash, cargo)
VALUES (?, ?, ?, ?)
""", (nome, usuario, senha_hash, cargo))

conn.commit()
conn.close()

print("Usuário criado com sucesso!")