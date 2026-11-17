"""Gera as tabelas da análise energética a partir das premissas e atualiza os documentos.

Execução:
    python -m scripts.gerar_analise            → grava resultados/ e atualiza README e docs/analise_energetica.md
    python -m scripts.gerar_analise --checar   → só verifica se os documentos estão em dia (usado nos testes)

As tabelas ficam entre marcadores <!-- gerado:NOME --> ... <!-- /gerado:NOME --> nos
documentos, para que nenhum número publicado divirja do código.
"""

from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

from energia import alternativas as alt
from energia import calculos as calc

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "resultados"
DOCUMENTOS = [RAIZ / "README.md", RAIZ / "docs" / "analise_energetica.md"]


def fmt(v: float | None, casas: int = 2) -> str:
    if v is None or (isinstance(v, float) and math.isinf(v)):
        return "—"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _meses(anos: float) -> str:
    n = max(1, round(anos * 12))
    return f"≈ {n} {'mês' if n == 1 else 'meses'}"


def sim(v: bool) -> str:
    return "sim" if v else "não"


def tabelas(perfil: calc.Perfil | None = None) -> dict[str, str]:
    perfil = perfil or calc.Perfil()
    atual = alt.situacao_atual(perfil)
    res = alt.comparar(perfil)
    sens = alt.sensibilidade(perfil)
    verao = alt.modo_verao_adicional(perfil, minutos=alt.minutos_meta(perfil))
    a, b, c, ab = res

    linha_base = (f"Situação atual: **{fmt(atual['consumo_kwh_mes'], 1)} kWh/mês** · "
                  f"**R$ {fmt(atual['custo_rs_mes'])}/mês** (R$ {fmt(atual['custo_rs_ano'])}/ano) · "
                  f"{fmt(atual['co2_kg_ano'], 1)} kgCO₂/ano · {fmt(atual['agua_l_mes'], 0)} L de água/mês")

    comp = [
        "| Alt. | Alternativa | Renovável | Consumo do chuveiro na rede (kWh/mês) | Energia evitada (kWh/mês) | "
        "Energia compensada na conta (kWh/mês) | Economia R$/mês | Investimento R$ | Manutenção R$/ano | "
        "Retorno (anos) | Saldo 10 anos R$ | R$ por kWh reduzido | CO₂ evitado kg/ano | Água poupada L/mês | "
        "Telhado m² | Reduz pico 18–21h |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in res:
        comp.append(
            f"| {r.codigo} | {r.nome} | {sim(r.renovavel)} | {fmt(r.consumo_kwh_mes, 1)} | "
            f"{fmt(r.energia_evitada_kwh_mes, 1)} | {fmt(r.energia_compensada_kwh_mes, 1)} | {fmt(r.economia_rs_mes)} | "
            f"{fmt(r.investimento_rs)} | {fmt(r.manutencao_rs_ano)} | {fmt(r.payback_anos)} | "
            f"{fmt(r.saldo_horizonte_rs)} | {fmt(r.custo_kwh_evitado_rs, 3)} | {fmt(r.co2_evitado_kg_ano, 1)} | "
            f"{fmt(r.agua_economizada_l_mes, 0)} | {fmt(r.area_telhado_m2, 1)} | {sim(r.reduz_pico_noturno)} |")
    comp += ["",
             "Na alternativa C o chuveiro continua consumindo a mesma energia da rede à noite; a geração solar "
             "diurna vira crédito que **compensa** esse consumo na conta. Supõe-se que a casa consuma ao menos "
             f"{fmt(c.detalhes['geracao_kwh_mes'] + 50, 0)} kWh/mês (geração + 50 kWh de disponibilidade) para "
             "aproveitar todo o crédito. O crédito é valorizado em 85% da tarifa, hipótese simplificada da equipe "
             "(não é percentual fixado em lei).",
             "",
             f"Dimensionamento do aquecedor solar: B usa reservatório de {b.detalhes['volume_l']} L "
             f"({fmt(b.detalhes['demanda_l_dia'], 0)} L/dia de água a 38 °C); A+B usa {ab.detalhes['volume_l']} L "
             f"({fmt(ab.detalhes['demanda_l_dia'], 0)} L/dia).",
             "",
             f"Dica adicional, fora da comparação (muda a temperatura do banho): usar a posição verão de outubro "
             f"a março pouparia mais {fmt(verao['kwh_mes'], 1)} kWh/mês na média anual (R$ {fmt(verao['rs_mes'])}/mês)."]

    sensib = ["| Alt. | Otimista | Base | Pessimista |", "|---|---|---|---|"]
    for codigo, v in sens.items():
        sensib.append(f"| {codigo} | {fmt(v['otimista'])} | {fmt(v['base'])} | {fmt(v['pessimista'])} |")

    readme = ["| Alternativa | Redução na conta/mês | Investimento | Retorno (base, faixa) |", "|---|---|---|---|"]
    for r in res:
        tipo = "compensados" if r.energia_compensada_kwh_mes else "evitados"
        s = sens[r.codigo]
        faixa = (f"{fmt(r.payback_anos, 1)} anos ({fmt(s['otimista'], 1)} a {fmt(s['pessimista'], 1)})"
                 if r.payback_anos >= 1 else _meses(r.payback_anos))
        readme.append(f"| {r.codigo}) {r.nome} | {fmt(r.economia_kwh_mes, 0)} kWh {tipo} · R$ {fmt(r.economia_rs_mes)} | "
                      f"R$ {fmt(r.investimento_rs, 0)} | {faixa} |")

    return {"linha_base": linha_base, "comparacao": "\n".join(comp), "sensibilidade": "\n".join(sensib),
            "readme_resumo": "\n".join(readme)}


def aplicar(texto: str, blocos: dict[str, str]) -> str:
    for nome, conteudo in blocos.items():
        padrao = re.compile(rf"<!-- gerado:{nome} -->\n.*?<!-- /gerado:{nome} -->", re.S)
        texto = padrao.sub(lambda m: f"<!-- gerado:{nome} -->\n{conteudo}\n<!-- /gerado:{nome} -->", texto)
    return texto


def documentos_desatualizados() -> list[str]:
    blocos = tabelas()
    return [d.name for d in DOCUMENTOS
            if aplicar(d.read_text(encoding="utf-8"), blocos) != d.read_text(encoding="utf-8")]


def gravar_csv(perfil: calc.Perfil) -> None:
    PASTA.mkdir(exist_ok=True)
    res = alt.comparar(perfil)
    campos = ["codigo", "nome", "renovavel", "consumo_kwh_mes", "energia_evitada_kwh_mes",
              "energia_compensada_kwh_mes", "economia_kwh_mes", "economia_rs_mes", "investimento_rs",
              "manutencao_rs_ano", "payback_anos", "saldo_horizonte_rs", "custo_kwh_evitado_rs",
              "co2_evitado_kg_ano", "agua_economizada_l_mes", "area_telhado_m2", "reduz_pico_noturno"]
    with open(PASTA / "comparacao_alternativas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for r in res:
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.dicionario().items()})
    with open(PASTA / "sensibilidade_payback.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["codigo", "otimista_anos", "base_anos", "pessimista_anos"])
        for codigo, v in alt.sensibilidade(perfil).items():
            w.writerow([codigo] + [round(v[c], 2) if not math.isinf(v[c]) else "" for c in
                                   ("otimista", "base", "pessimista")])


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--checar" in sys.argv:
        desatualizados = documentos_desatualizados()
        print("Documentos em dia." if not desatualizados else f"Desatualizados: {', '.join(desatualizados)}")
        sys.exit(1 if desatualizados else 0)

    perfil = calc.Perfil()
    gravar_csv(perfil)
    blocos = tabelas(perfil)
    resumo = ["# Resultados – família de referência (4 pessoas, banho de 10 min, São Paulo)", "",
              blocos["linha_base"], "", blocos["comparacao"], "", "## Sensibilidade do retorno (anos)", "",
              blocos["sensibilidade"]]
    (PASTA / "resumo.md").write_text("\n".join(resumo) + "\n", encoding="utf-8")
    for doc in DOCUMENTOS:
        doc.write_text(aplicar(doc.read_text(encoding="utf-8"), blocos), encoding="utf-8")
    print("\n".join(resumo))


if __name__ == "__main__":
    main()
