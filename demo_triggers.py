"""Demonstração dos triggers para o vídeo: corrige uma nota e mostra log, média recalculada e alerta.

Uso: python demo_triggers.py [RA] [DISCIPLINA] [AVALIACAO] [NOTA]
     python demo_triggers.py 2026001 ESW303 P1 3.0
     (corrige a P1 da Ana de 9,5 para 3,0: log de alteração + média 3,0 + alerta + chamado automático)
"""
import sys

from smartcampus import db

ra, codigo, avaliacao, valor = (sys.argv[1:] + ["2026001", "ESW303", "P1", "3.0"][len(sys.argv) - 1:])[:4]

print(f"Antes:  {db.calcular_media(ra, codigo)}")
db.lancar_nota(ra, codigo, avaliacao, float(valor))
print(f"\nLançada nota {avaliacao} = {valor} via CALL sp_lancar_nota(...)\n")
print(f"Depois: {db.calcular_media(ra, codigo)}")

print("\nÚltimas alterações (trigger trg_log_alteracao_nota):")
for linha in db.listar_log_notas(5):
    print("  ", linha)
print("\nAlertas abertos do aluno (trigger trg_alerta_media_baixa):")
for alerta in db.listar_alertas(ra):
    print("  ", alerta)
print("\nChamados do aluno:")
for chamado in db.listar_chamados(ra):
    print("  ", chamado)
