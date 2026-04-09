import sqlite3
import bcrypt

conn = sqlite3.connect("database/banco.db")
cursor = conn.cursor()

nome = "Administrador"
usuario = "admin"
senha = "123456"
cargo = "admin"

senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt())

cursor.execute("""
INSERT INTO usuarios (nome, usuario, senha_hash, cargo)
VALUES (?, ?, ?, ?)
""", (nome, usuario, senha_hash, cargo))

conn.commit()
conn.close()

print("Usuário criado com sucesso!")