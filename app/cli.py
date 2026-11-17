"""Chat do assistente de energia no terminal.

Execução:  python -m app.cli
Comandos:  'sair' encerra | 'avaliar' registra o feedback da última resposta (modo teste)
"""

from __future__ import annotations

import sys

from energia import Sessao, responder
from energia.feedback import registrar


def _sim(pergunta: str) -> bool:
    return input(pergunta + " (s/n) ").strip().lower().startswith("s")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sessao = Sessao()
    ultima_pergunta, ultima_intencao = "", ""
    print("Citizen Assist AI – Energia no banho. Digite 'ajuda' para ver o que posso fazer ou 'sair' para encerrar.\n")
    while True:
        try:
            mensagem = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not mensagem:
            continue
        if mensagem.lower() in {"sair", "tchau", "fim"}:
            print("Assistente: Até logo! Bons banhos e boa economia.")
            break
        if mensagem.lower() == "avaliar":
            if not ultima_intencao:
                print("Assistente: Faça uma pergunta antes de avaliar.\n")
                continue
            participante = input("Código do participante (ex.: P1): ")
            registrar(participante, ultima_pergunta, ultima_intencao,
                      _sim("Entendeu a resposta?"), _sim("A resposta foi útil?"),
                      input("Comentário (não escreva dados pessoais): "))
            print("Assistente: Obrigado! Avaliação registrada.\n")
            continue
        resposta = responder(mensagem, sessao)
        ultima_pergunta, ultima_intencao = mensagem, resposta.intencao
        print("\nAssistente: " + resposta.formatada() + "\n")


if __name__ == "__main__":
    main()
