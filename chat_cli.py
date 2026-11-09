"""Chat no terminal.   Uso: python chat_cli.py --ra 2026002 [--modo offline|claude]"""
import argparse
import json

from smartcampus import db
from smartcampus.assistente import Assistente


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ra", help="RA do aluno logado (ex.: 2026001)")
    parser.add_argument("--modo", choices=["claude", "offline"], help="força o modo do assistente")
    parser.add_argument("--debug", action="store_true", help="mostra as chamadas de ferramentas")
    args = parser.parse_args()

    ra = args.ra
    if not ra:
        for a in db.listar_alunos():
            print(f"  {a['ra']}  {a['nome']}")
        ra = input("RA do aluno: ").strip()

    bot = Assistente(ra, modo=args.modo)
    print(f"\nOlá, {bot.aluno['nome']}! Modo: {bot.modo}. Digite 'sair' para encerrar.\n")
    while True:
        pergunta = input("Você: ").strip()
        if pergunta.lower() in {"sair", "exit", "quit"}:
            break
        if not pergunta:
            continue
        r = bot.responder(pergunta)
        if args.debug:
            for c in r["chamadas"]:
                print(f"  [ferramenta] {c['ferramenta']}({json.dumps(c['entrada'], ensure_ascii=False)})")
        print(f"\nSmartCampus: {r['resposta']}\n")


if __name__ == "__main__":
    main()
