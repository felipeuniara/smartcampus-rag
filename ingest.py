"""Cria/recria a base vetorial no ChromaDB a partir da pasta documentos/.

Uso:
    python ingest.py                       # indexa todos os documentos
    python ingest.py --testar "conteúdo da P2"   # faz uma busca de teste
"""
import argparse

from smartcampus import rag


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testar", help="pergunta para testar a busca semântica")
    parser.add_argument("--sem-recriar", action="store_true", help="não apaga a coleção antes")
    args = parser.parse_args()

    if not args.testar:
        print("Indexando documentos no ChromaDB...")
        resumo = rag.indexar(recriar=not args.sem_recriar)
        print(f"Pronto: {resumo['arquivos']} arquivos, {resumo['chunks']} chunks.")
        return

    for i, r in enumerate(rag.buscar(args.testar), 1):
        print(f"\n#{i}  score={r['score']}  (vetorial={r['similaridade']})  {r['fonte']}  [{r['secao']}]")
        print("   " + r["texto"][:250].replace("\n", " ") + "...")


if __name__ == "__main__":
    main()
