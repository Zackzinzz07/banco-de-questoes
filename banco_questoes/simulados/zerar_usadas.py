"""Zera a marca de 'usada em simulado' de todas as questões (recicla o banco)."""
import db

con = db.conectar()
db.zerar_usadas(con)
print("Pronto: todas as questões voltaram a ficar disponíveis para sorteio.")
con.close()
