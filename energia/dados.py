"""Carregamento das premissas e referências usadas pelo módulo de energia."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PASTA_DADOS = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def premissas() -> dict:
    with open(PASTA_DADOS / "premissas.json", encoding="utf-8") as arquivo:
        return json.load(arquivo)


@lru_cache(maxsize=1)
def referencias() -> dict:
    with open(PASTA_DADOS / "referencias.json", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def valor(grupo: str, chave: str, campo: str = "valor") -> float:
    """Retorna um valor numérico das premissas (``campo`` pode ser valor, min ou max)."""
    item = premissas()[grupo][chave]
    return item.get(campo, item["valor"])


def citar(chaves: list[str]) -> list[dict]:
    """Converte chaves de referência em lista de {chave, titulo, url}."""
    refs = referencias()
    vistas: list[str] = []
    for chave in chaves:
        if chave in refs and chave not in vistas:
            vistas.append(chave)
    return [{"chave": c, **refs[c]} for c in vistas]
