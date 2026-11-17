"""Registro anônimo das avaliações feitas durante os testes com usuários.

Grava apenas: data/hora, código do participante (ex.: P1), pergunta feita,
intenção respondida, se a resposta foi entendida/útil e um comentário livre.
Nenhum nome, telefone, endereço ou outro dado pessoal é solicitado ou armazenado.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "testes" / "registro_feedback.csv"
CAMPOS = ["data_hora", "participante", "pergunta", "intencao", "entendeu", "util", "comentario"]

_PADROES_PESSOAIS = [
    r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",          # CPF
    r"\b\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b",          # telefone
    r"[\w.+-]+@[\w-]+\.[\w.]+",                    # e-mail
]


def anonimizar(texto: str) -> str:
    for padrao in _PADROES_PESSOAIS:
        texto = re.sub(padrao, "[removido]", texto)
    return texto.strip()[:300]


def registrar(participante: str, pergunta: str, intencao: str, entendeu: bool, util: bool,
              comentario: str = "", arquivo: Path = ARQUIVO) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    novo = not arquivo.exists()
    with open(arquivo, "a", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            escritor.writeheader()
        escritor.writerow({
            "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "participante": re.sub(r"[^A-Za-z0-9]", "", participante)[:5] or "P?",
            "pergunta": anonimizar(pergunta),
            "intencao": intencao,
            "entendeu": "sim" if entendeu else "nao",
            "util": "sim" if util else "nao",
            "comentario": anonimizar(comentario),
        })
