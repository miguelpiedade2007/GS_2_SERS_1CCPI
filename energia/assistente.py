"""Assistente de energia do Citizen Assist AI.

Recebe a mensagem do cidadão, identifica a intenção, atualiza o perfil da família
com os números informados e devolve uma resposta em linguagem simples, sempre com
fontes e limitações. Funciona sem internet e sem modelo de linguagem externo; as
respostas vêm dos cálculos de ``alternativas.py``.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field

from . import alternativas as alt
from . import calculos as calc
from .dados import citar, valor

AVISO_GERAL = ("Os valores são estimativas para uma família média em São Paulo. "
               "A economia real depende do seu chuveiro, dos seus hábitos e da tarifa da sua conta.")


@dataclass
class Resposta:
    intencao: str
    texto: str
    referencias: list[dict] = field(default_factory=list)
    limitacoes: list[str] = field(default_factory=list)
    dados: dict = field(default_factory=dict)

    def formatada(self) -> str:
        partes = [self.texto]
        if self.limitacoes:
            partes.append("Importante:\n" + "\n".join(f"  • {l}" for l in self.limitacoes))
        if self.referencias:
            partes.append("Fontes:\n" + "\n".join(
                f"  • {r['titulo']}" + (f" – {r['url']}" if r["url"] else "") for r in self.referencias))
        return "\n\n".join(partes)

    def dicionario(self) -> dict:
        return {"intencao": self.intencao, "texto": self.texto, "referencias": self.referencias,
                "limitacoes": self.limitacoes, "dados": self.dados, "texto_formatado": self.formatada()}


@dataclass
class Sessao:
    """Guarda o perfil da família durante a conversa (sem dados pessoais)."""
    perfil: calc.Perfil = field(default_factory=calc.Perfil)
    ultima_intencao: str = ""


# ---------------------------------------------------------------- utilidades

def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def rs(v: float) -> str:
    texto = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def num(v: float, casas: int = 1) -> str:
    texto = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


def anos(v: float) -> str:
    if math.isinf(v):
        return "não se paga no período"
    if v < 1:
        meses = max(1, round(v * 12))
        return f"cerca de {meses} {'mês' if meses == 1 else 'meses'}"
    return f"cerca de {num(v)} anos"


# ---------------------------------------------------------------- intenções

INTENCOES: dict[str, list[str]] = {
    "saudacao": ["oi", "ola", "bom dia", "boa tarde", "boa noite", "e ai"],
    "ajuda": ["ajuda", "menu", "o que voce faz", "o que voce sabe", "como funciona", "opcoes"],
    "consumo": ["quanto gasta", "quanto consome", "consumo", "gasta muito", "chuveiro", "conta de luz",
                "quanto custa o banho", "kwh", "gasto"],
    "comparar": ["comparar", "compara", "alternativa", "qual a melhor", "qual melhor", "vale a pena",
                 "compensa", "melhor opcao", "o que fazer", "recomenda", "recomendacao"],
    "banho_consciente": ["economizar", "economia", "dica", "reduzir", "diminuir", "banho rapido",
                         "banho curto", "modo verao", "posicao verao", "temporizador", "sem gastar"],
    "aquecedor_solar": ["aquecedor solar", "aquecimento solar", "solar termico", "boiler", "coletor",
                        "reservatorio", "agua quente solar"],
    "fotovoltaica": ["fotovolta", "placa solar", "placas solares", "painel solar", "paineis", "modulo",
                     "energia solar", "gerar energia", "geracao distribuida"],
    "tarifa_social": ["tarifa social", "cadunico", "cad unico", "baixa renda", "gratuidade", "bolsa familia",
                      "desconto na conta"],
    "ambiente": ["co2", "carbono", "ambiente", "ambiental", "emissao", "emissoes", "sustentavel",
                 "planeta", "poluicao", "pico"],
    "calculo": ["como calculou", "calculo", "conta feita", "formula", "como chegou"],
    "fontes": ["fonte", "referencia", "de onde", "onde voce tirou", "confiar"],
    "limitacoes": ["limitac", "premissa", "garantia", "garantido", "certeza", "precis", "estimativa"],
}


# Assuntos específicos pesam mais que expressões genéricas como "vale a pena".
PESO_ASSUNTO = {"aquecedor_solar": 2, "fotovoltaica": 2, "tarifa_social": 2}


def detectar_intencao(texto_norm: str) -> str:
    pontos: dict[str, int] = {}
    for intencao, palavras in INTENCOES.items():
        p = 0
        for palavra in palavras:
            if re.search(rf"(?<![a-z]){re.escape(palavra)}", texto_norm):
                p += len(palavra.split()) + 1
        if p:
            pontos[intencao] = p * PESO_ASSUNTO.get(intencao, 1)
    if "aquecedor_solar" in pontos and "fotovoltaica" in pontos:
        return "comparar"  # pergunta envolve as duas tecnologias solares
    return max(pontos, key=pontos.get) if pontos else ""


# Faixas aceitas para cada dado informado: (mínimo, máximo, descrição para o usuário)
LIMITES = {
    "pessoas": (1, 20, "o número de pessoas deve ficar entre 1 e 20"),
    "minutos_por_banho": (1, 60, "o tempo de banho deve ficar entre 1 e 60 minutos"),
    "potencia_chuveiro_w": (1000, 10000, "a potência do chuveiro deve ficar entre 1.000 e 10.000 W"),
    "tarifa_kwh": (0.20, 3.00, "a tarifa deve ficar entre R$ 0,20 e R$ 3,00 por kWh"),
    "consumo_total_kwh_mes": (1, 3000, "o consumo da casa deve ficar entre 1 e 3.000 kWh/mês"),
    "banhos_por_pessoa_dia": (0.1, 5, "informe pelo menos 1 banho por dia, e no máximo 5 por pessoa"),
}


def extrair_perfil(texto_norm: str, perfil: calc.Perfil) -> tuple[calc.Perfil, list[str], list[str]]:
    """Lê números da mensagem e atualiza o perfil.

    Retorna (perfil, dados_lidos, avisos). Valores fora das faixas de LIMITES são
    ignorados e geram um aviso pedindo um valor válido.
    """
    candidatos: dict = {}
    numero = r"(\d+(?:[.,]\d+)?)"

    def para_float(s: str) -> float:
        return float(s.replace(",", "."))

    if m := re.search(rf"{numero}\s*(?:pessoas|moradores|pessoa|morador)", texto_norm):
        candidatos["pessoas"] = int(para_float(m.group(1)))
    if m := re.search(rf"{numero}\s*(?:minutos|minuto|min)\b", texto_norm):
        candidatos["minutos_por_banho"] = para_float(m.group(1))
    if m := re.search(rf"{numero}\s*(?:kw|quilowatts?)\b", texto_norm):
        candidatos["potencia_chuveiro_w"] = para_float(m.group(1)) * 1000
    elif m := re.search(r"(\d+(?:[.]\d{3})?)\s*(?:w|watts?)\b", texto_norm):
        candidatos["potencia_chuveiro_w"] = float(m.group(1).replace(".", ""))
    if m := re.search(rf"(?:r\$|tarifa(?: de)?|kwh custa)\s*{numero}", texto_norm):
        candidatos["tarifa_kwh"] = para_float(m.group(1))
    if m := re.search(rf"(?:consumo|gasto|conta)[^0-9]*{numero}\s*kwh", texto_norm):
        candidatos["consumo_total_kwh_mes"] = para_float(m.group(1))
    if m := re.search(rf"{numero}\s*banhos?\s*por\s*dia", texto_norm):
        pessoas = candidatos.get("pessoas", perfil.pessoas) or 1
        candidatos["banhos_por_pessoa_dia"] = para_float(m.group(1)) / pessoas

    mudancas: dict = {}
    avisos: list[str] = []
    for campo, v in candidatos.items():
        minimo, maximo, mensagem = LIMITES[campo]
        if minimo <= v <= maximo:
            mudancas[campo] = v
        else:
            avisos.append(mensagem)

    lidos: list[str] = []
    if "pessoas" in mudancas:
        lidos.append(f"{mudancas['pessoas']} pessoa(s)")
    if "minutos_por_banho" in mudancas:
        lidos.append(f"banho de {num(mudancas['minutos_por_banho'], 0)} min")
    if "potencia_chuveiro_w" in mudancas:
        lidos.append(f"chuveiro de {num(mudancas['potencia_chuveiro_w'], 0)} W")
    if "tarifa_kwh" in mudancas:
        lidos.append(f"tarifa de {rs(mudancas['tarifa_kwh'])}/kWh")
    if "consumo_total_kwh_mes" in mudancas:
        lidos.append(f"consumo da casa de {num(mudancas['consumo_total_kwh_mes'], 0)} kWh/mês")
    if "banhos_por_pessoa_dia" in mudancas:
        lidos.append(f"{num(mudancas['banhos_por_pessoa_dia'] * mudancas.get('pessoas', perfil.pessoas), 0)} banhos por dia")

    if re.search(r"(nao|sem) (tenho|temos|tem) (a )?tarifa social|nao (sou|somos) (do )?cad", texto_norm):
        mudancas["tarifa_social"] = False
        lidos.append("sem Tarifa Social")
    elif re.search(r"(tenho|temos|tem|recebo|recebemos|sou|somos).{0,20}(tarifa social|cadunico|cad unico)",
                   texto_norm):
        mudancas["tarifa_social"] = True
        lidos.append("com Tarifa Social")
    return (perfil.com(**mudancas) if mudancas else perfil), lidos, avisos


# ---------------------------------------------------------------- respostas

def _resumo_perfil(p: calc.Perfil) -> str:
    chuveiro = f"chuveiro de {num(p.potencia_chuveiro_w, 0)} W" if p.potencia_chuveiro_w \
        else f"vazão de {num(p.vazao_l_min)} L/min"
    return (f"{p.pessoas} pessoa(s), {num(p.banhos_por_pessoa_dia * p.pessoas, 0)} banho(s) por dia "
            f"de {num(p.minutos_por_banho, 0)} min, {chuveiro}, tarifa de {rs(p.tarifa_kwh)}/kWh")


def _aviso_tarifa_social(p: calc.Perfil) -> list[str]:
    if not p.tarifa_social:
        return []
    franquia = calc.franquia_social()
    if p.consumo_total_kwh_mes is None:
        return [f"Com a Tarifa Social os primeiros {num(franquia, 0)} kWh do mês são gratuitos, então os valores "
                "em reais acima são equivalentes, sem o benefício. Diga o consumo da sua conta "
                "(ex.: 'consumo de 150 kWh') para eu calcular o valor efetivamente cobrado."]
    return [f"Considerei a Tarifa Social: só a parte acima de {num(franquia, 0)} kWh/mês é cobrada, "
            "então a economia em reais é limitada a esse excedente."]


def _bloco_conta(p: calc.Perfil, atual: dict) -> str:
    """Explica custo equivalente x valor efetivamente cobrado quando há Tarifa Social."""
    if not p.tarifa_social or p.consumo_total_kwh_mes is None:
        return (f"• Por mês, o chuveiro consome cerca de {num(atual['consumo_kwh_mes'], 0)} kWh, "
                f"o que equivale a {rs(atual['custo_rs_mes'])} na conta ({rs(atual['custo_rs_ano'])} por ano).\n")
    franquia = calc.franquia_social()
    return (
        f"• Por mês, o chuveiro consome cerca de {num(atual['consumo_kwh_mes'], 0)} kWh. Sem benefício, "
        f"isso equivaleria a {rs(atual['custo_rs_mes'])}.\n"
        f"• Com a Tarifa Social, dos {num(p.consumo_total_kwh_mes, 0)} kWh da casa só "
        f"{num(atual['kwh_cobrados_casa_mes'], 0)} kWh são cobrados (acima de {num(franquia, 0)} kWh): "
        f"{rs(atual['energia_cobrada_casa_rs_mes'])} de energia na conta, antes de outras cobranças.\n"
        f"• Se o chuveiro não fosse usado, a conta cairia no máximo {rs(atual['custo_faturado_chuveiro_rs_mes'])} "
        "por mês: esse é o peso real do chuveiro no valor cobrado.\n"
    )


def responder_consumo(s: Sessao) -> Resposta:
    p = s.perfil
    atual = alt.situacao_atual(p)
    metodo = ("calculado pela potência informada, E = P × t" if p.metodo == "potencia"
              else f"o que corresponde a uma potência média de {num(atual['potencia_media_kw'])} kW")
    texto = (
        f"Para {_resumo_perfil(p)}:\n\n"
        f"• Cada banho usa cerca de {num(atual['kwh_por_banho'], 2)} kWh ({metodo}).\n"
        + _bloco_conta(p, atual) +
        f"• São cerca de {num(atual['agua_l_mes'], 0)} litros de água por mês.\n\n"
        "O chuveiro elétrico costuma ser um dos aparelhos que mais gastam numa casa porque aquece a água "
        "na hora, com potência muito alta. Quer saber como economizar? Pergunte 'quais as alternativas?'."
    )
    return Resposta("consumo", texto,
                    citar(["IDEC_USP_CHUVEIRO", "HALLIDAY", "FATURAS_ENEL_2026", "PROCEL_PPH"]
                          + (["ANEEL_TARIFA_SOCIAL"] if p.tarifa_social else [])),
                    [AVISO_GERAL] + _aviso_tarifa_social(p), {"situacao_atual": atual})


def _linha_alternativa(r) -> str:
    if r.energia_compensada_kwh_mes:
        tipo = (f"~{num(r.energia_compensada_kwh_mes, 0)} kWh/mês compensados na conta "
                "(o chuveiro segue consumindo o mesmo)")
    else:
        tipo = f"~{num(r.energia_evitada_kwh_mes, 0)} kWh/mês a menos da rede"
    return (f"{r.codigo}) {r.nome}\n"
            f"   {tipo} ≈ {rs(r.economia_rs_mes)}/mês | Investimento: {rs(r.investimento_rs)} | "
            f"Retorno: {anos(r.payback_anos)}")


def responder_comparar(s: Sessao) -> Resposta:
    p = s.perfil
    atual = alt.situacao_atual(p)
    resultados = alt.comparar(p)
    a, b, c = resultados[0], resultados[1], resultados[2]
    texto = (
        f"Hoje o chuveiro usa {num(atual['consumo_kwh_mes'], 0)} kWh/mês "
        f"(≈ {rs(atual['custo_rs_mes'])}/mês sem benefícios). "
        f"Comparando as opções para a mesma família, mesma temperatura de banho, no mês médio e em "
        f"{alt.horizonte()} anos:\n\n"
        + "\n".join(_linha_alternativa(r) for r in resultados)
        + "\n\nRecomendação:\n"
        f"1. Comece pelo banho consciente (A): custa quase nada, economiza ~{rs(a.economia_rs_mes)}/mês "
        f"e ainda poupa ~{num(a.agua_economizada_l_mes, 0)} litros de água.\n"
        "2. Se a casa for sua e tiver telhado livre, as duas opções solares são renováveis:\n"
        f"   • Fotovoltaica (C): retorno {'mais rápido' if c.payback_anos < b.payback_anos else 'mais lento'} "
        f"({anos(c.payback_anos)}) e créditos para a casa toda, "
        f"mas ocupa ~{num(c.area_telhado_m2)} m² e não tira o chuveiro do horário de pico.\n"
        f"   • Aquecedor solar (B): retorno {anos(b.payback_anos)}, ocupa ~{num(b.area_telhado_m2)} m², "
        "não depende de aprovação da distribuidora e reduz o consumo à noite, quando a rede está mais carregada.\n"
        "Peça 'detalhes do aquecedor solar' ou 'detalhes da placa solar' para saber mais."
    )
    limites = [AVISO_GERAL,
               "Retorno calculado sem reajuste de tarifa e sem juros; se a tarifa subir, o retorno fica mais rápido.",
               "Na fotovoltaica, o crédito foi valorizado em 85% da tarifa (hipótese da equipe, não percentual da lei).",
               "Preços de equipamentos variam bastante: confira a faixa pessimista/otimista em 'limitações'."]
    return Resposta("comparar", texto,
                    citar(["IDEC_USP_CHUVEIRO", "FATURAS_ENEL_2026", "CRONOSHARE_PRECO_SOLAR", "NBR15569",
                           "CRESESB_SUNDATA", "GREENER_PRECOS", "LEI_14300", "MCTI_FATOR_EMISSAO"]),
                    limites + _aviso_tarifa_social(p),
                    {"situacao_atual": atual, "alternativas": [r.dicionario() for r in resultados]})


def responder_banho_consciente(s: Sessao) -> Resposta:
    p = s.perfil
    a = alt.banho_consciente(p)
    meta = alt.minutos_meta(p)
    verao = alt.modo_verao_adicional(p, minutos=meta)
    if meta < p.minutos_por_banho:
        resultado = (f"Reduzir de {num(p.minutos_por_banho, 0)} para {num(meta, 0)} minutos, com a mesma "
                     f"temperatura, economiza cerca de {num(a.economia_kwh_mes, 0)} kWh por mês "
                     f"({num(a.detalhes['reducao_percentual'], 0)}% de energia e de água): "
                     f"{rs(a.economia_rs_mes)}/mês ({rs(a.economia_rs_mes * 12)} por ano) e "
                     f"~{num(a.agua_economizada_l_mes, 0)} litros de água por mês.")
    else:
        resultado = f"Seus banhos já têm até {num(meta, 0)} minutos. Ótimo! As outras dicas ainda ajudam."
    potencia_verao = num(verao["razao_potencia"] * 100, 0)
    texto = (
        "Dicas que funcionam sem gastar quase nada:\n\n"
        f"• Banho de até {num(valor('alternativa_banho_consciente', 'minutos_meta'), 0)} minutos. "
        "Um temporizador ou uma música de referência ajuda.\n"
        "• Feche o chuveiro enquanto se ensaboa.\n"
        "• Evite banhos no horário de pico (18h às 21h) quando puder; isso alivia a rede elétrica.\n\n"
        + resultado + "\n\n"
        "Dica extra (posição verão): nos dias quentes, de outubro a março, se a família aceitar um banho "
        f"um pouco menos quente, a posição verão usa cerca de {potencia_verao}% da potência. "
        f"Isso pouparia mais ~{num(verao['kwh_mes'], 0)} kWh/mês na média do ano (≈ {rs(verao['rs_mes'])}/mês). "
        "Esse valor fica fora da comparação porque muda a temperatura do banho."
    )
    return Resposta("banho_consciente", texto, citar(["IDEC_USP_CHUVEIRO", "HALLIDAY", "INMETRO_PBE"]),
                    [AVISO_GERAL] + a.limitacoes + _aviso_tarifa_social(p),
                    {"alternativa": a.dicionario(), "modo_verao_adicional": verao})


def responder_aquecedor_solar(s: Sessao) -> Resposta:
    p = s.perfil
    b = alt.aquecedor_solar(p)
    d = b.detalhes
    sens = alt.sensibilidade(p)["B"]
    texto = (
        "O aquecedor solar de água usa placas (coletores) no telhado para esquentar a água, que fica "
        "guardada num reservatório térmico (boiler). O chuveiro elétrico fica como apoio para dias frios "
        "ou nublados.\n\n"
        f"• Sua família usa ~{num(d['demanda_l_dia'], 0)} L de água quente por dia, então o sistema estimado tem "
        f"reservatório de {num(d['volume_l'], 0)} L e ~{num(b.area_telhado_m2)} m² de coletores.\n"
        f"• O sol fornece cerca de {num(d['fracao_solar'] * 100, 0)}% do aquecimento no ano.\n"
        f"• Economia: ~{num(b.economia_kwh_mes, 0)} kWh/mês a menos da rede ≈ {rs(b.economia_rs_mes)}/mês.\n"
        f"• Investimento: cerca de {rs(b.investimento_rs)} instalado; manutenção ~{rs(b.manutencao_rs_ano)}/ano.\n"
        f"• Retorno: {anos(b.payback_anos)} (entre {anos(sens['otimista'])} e {anos(sens['pessimista'])} "
        "conforme preço e insolação).\n"
        f"• Saldo em {alt.horizonte()} anos: {rs(b.saldo_horizonte_rs)}.\n\n"
        "Vantagens: " + " ".join(b.viabilidade)
    )
    return Resposta("aquecedor_solar", texto,
                    citar(["NBR15569", "CRONOSHARE_PRECO_SOLAR", "ABRAVA", "INMETRO_PBE", "FATURAS_ENEL_2026"]),
                    [AVISO_GERAL] + b.limitacoes + _aviso_tarifa_social(p), {"alternativa": b.dicionario()})


def responder_fotovoltaica(s: Sessao) -> Resposta:
    p = s.perfil
    c = alt.fotovoltaica(p)
    d = c.detalhes
    sens = alt.sensibilidade(p)["C"]
    texto = (
        "Placas solares fotovoltaicas transformam a luz do sol em eletricidade. A energia gerada durante o dia "
        "vai para a rede e vira crédito que abate a conta. O chuveiro continua consumindo a mesma energia.\n\n"
        f"• Sistema para cobrir o consumo do chuveiro ({num(c.consumo_kwh_mes, 0)} kWh/mês): "
        f"{num(d['kwp'], 2)} kWp, {d['modulos']} módulos, ~{num(c.area_telhado_m2)} m² de telhado.\n"
        f"• Geração estimada: ~{num(d['geracao_kwh_mes'], 0)} kWh/mês; compensados na conta: "
        f"~{num(c.energia_compensada_kwh_mes, 0)} kWh/mês ≈ {rs(c.economia_rs_mes)}/mês de desconto.\n"
        f"• Investimento: cerca de {rs(c.investimento_rs)}; manutenção ~{rs(c.manutencao_rs_ano)}/ano.\n"
        f"• Retorno: {anos(c.payback_anos)} (entre {anos(sens['otimista'])} e {anos(sens['pessimista'])}).\n\n"
        "Se o seu interesse é só a água do banho, o aquecedor solar não depende de aprovação da distribuidora "
        "e reduz o consumo no horário de pico. Pergunte 'comparar' para ver as duas lado a lado."
    )
    return Resposta("fotovoltaica", texto,
                    citar(["CRESESB_SUNDATA", "GREENER_PRECOS", "PV_MAGAZINE_2026", "LEI_14300", "ANEEL_REN1000",
                           "FATURAS_ENEL_2026"]),
                    [AVISO_GERAL] + c.limitacoes + _aviso_tarifa_social(p), {"alternativa": c.dicionario()})


def responder_tarifa_social(s: Sessao) -> Resposta:
    franquia = calc.franquia_social()
    texto = (
        "Desde 2025, famílias inscritas no CadÚnico com renda de até meio salário mínimo por pessoa "
        f"(ou com BPC) não pagam pelos primeiros {num(franquia, 0)} kWh do mês. O que passar disso é cobrado "
        "normalmente.\n\n"
        "O que isso muda nas recomendações:\n"
        f"• Se a casa toda gasta menos de {num(franquia, 0)} kWh, economizar no chuveiro não reduz a conta "
        "(mas continua poupando água e aliviando a rede).\n"
        f"• Se gasta mais, cada kWh economizado acima de {num(franquia, 0)} vale a tarifa cheia.\n\n"
        "O benefício é aplicado automaticamente quando o CadÚnico está atualizado. Para confirmar, procure o "
        "CRAS ou a distribuidora. Diga, por exemplo, 'temos tarifa social e consumo de 150 kWh' para eu recalcular."
    )
    return Resposta("tarifa_social", texto,
                    citar(["ANEEL_TARIFA_SOCIAL", "LEI_15235", "AGENCIA_GOV_TARIFA_SOCIAL"]),
                    ["As regras da Tarifa Social podem mudar; confira na distribuidora ou no site da ANEEL."])


def responder_ambiente(s: Sessao) -> Resposta:
    p = s.perfil
    atual = alt.situacao_atual(p)
    a, b, c, ab = alt.comparar(p)
    texto = (
        f"O chuveiro da família está associado a cerca de {num(atual['co2_kg_ano'], 0)} kg de CO₂ por ano, "
        "porque a eletricidade brasileira já é majoritariamente renovável (hidrelétricas, eólicas e solar).\n\n"
        f"• Banho consciente evita ~{num(a.co2_evitado_kg_ano, 0)} kg de CO₂/ano e "
        f"~{num(a.agua_economizada_l_mes * 12 / 1000, 1)} mil litros de água/ano.\n"
        f"• Aquecedor solar evita ~{num(b.co2_evitado_kg_ano, 0)} kg de CO₂/ano.\n"
        f"• Fotovoltaica: a geração renovável equivale a ~{num(c.co2_evitado_kg_ano, 0)} kg de CO₂/ano, "
        "mas acontece de dia, não no horário do banho.\n\n"
        "O maior ganho ambiental está no horário de pico: entre 18h e 21h milhões de chuveiros ligados ao mesmo "
        "tempo exigem mais usinas, muitas vezes termelétricas, que poluem mais. Banho mais curto e aquecedor solar "
        "reduzem esse pico; a fotovoltaica gera de dia e não reduz o pico noturno.\n\n"
        "Também há impactos na fabricação: placas e reservatórios usam metais, vidro e plástico. "
        "Sistemas com selo Inmetro duram mais (15 a 25 anos) e devem ser descartados em pontos de reciclagem."
    )
    return Resposta("ambiente", texto, citar(["MCTI_FATOR_EMISSAO", "INMETRO_PBE", "IDEC_USP_CHUVEIRO"]),
                    ["O fator de emissão é a média anual da rede; no horário de pico e em anos de seca, com mais "
                     "termelétricas, as emissões evitadas podem ser duas vezes maiores."])


def responder_calculo(s: Sessao) -> Resposta:
    """Explica a conta com o MESMO método e os MESMOS dados usados para o perfil atual."""
    p = s.perfil
    e_banho = calc.energia_por_banho_kwh(p)
    total = calc.consumo_mensal_kwh(p)
    if p.metodo == "potencia":
        kw = p.potencia_chuveiro_w / 1000
        horas = p.minutos_por_banho / 60
        passos = (
            f"1. Você informou um chuveiro de {num(p.potencia_chuveiro_w, 0)} W = {num(kw, 2)} kW.\n"
            f"2. Tempo de banho: {num(p.minutos_por_banho, 0)} min = {num(horas, 3)} h.\n"
            f"3. Energia por banho: E = P × t = {num(kw, 2)} kW × {num(horas, 3)} h = {num(e_banho, 3)} kWh.\n"
        )
        ref = ["INMETRO_PBE", "HALLIDAY", "FATURAS_ENEL_2026"]
    else:
        dt = calc.delta_t()
        massa = p.minutos_por_banho * p.vazao_l_min
        passos = (
            f"1. Água por banho: {num(p.vazao_l_min)} L/min × {num(p.minutos_por_banho, 0)} min = "
            f"{num(massa)} L (≈ {num(massa)} kg).\n"
            f"2. Aquecer de {num(valor('chuveiro', 'temperatura_agua_fria'), 0)} °C para "
            f"{num(valor('chuveiro', 'temperatura_banho'), 0)} °C: ΔT = {num(dt, 0)} °C.\n"
            f"3. Energia térmica: Q = m·c·ΔT = {num(massa)} × 4,186 × {num(dt, 0)} = {num(massa * 4.186 * dt, 0)} kJ. "
            f"Energia elétrica: Q ÷ 3.600 ÷ eficiência 0,95 = {num(e_banho, 3)} kWh por banho "
            f"(equivale a um chuveiro de ~{num(e_banho / (p.minutos_por_banho / 60), 1)} kW).\n"
        )
        ref = ["HALLIDAY", "IDEC_USP_CHUVEIRO", "INMETRO_PBE", "FATURAS_ENEL_2026"]
    social = " (com Tarifa Social, só a parte acima de 80 kWh da casa é cobrada)" if p.tarifa_social else ""
    texto = (
        "Como o cálculo foi feito para a sua família:\n\n" + passos +
        f"4. Banhos no mês: {p.pessoas} pessoa(s) × {num(p.banhos_por_pessoa_dia, 2)} banho/dia × "
        f"{calc.dias_mes()} dias = {num(p.banhos_por_mes, 0)} banhos.\n"
        f"5. Mês: {num(e_banho, 3)} kWh × {num(p.banhos_por_mes, 0)} = {num(total, 1)} kWh.\n"
        f"6. Custo equivalente: {num(total, 1)} kWh × {rs(p.tarifa_kwh)}/kWh = {rs(calc.custo(total, p))}/mês"
        f"{social}.\n"
        "7. Retorno de um investimento = investimento ÷ (economia anual − manutenção anual)."
    )
    return Resposta("calculo", texto, citar(ref), [AVISO_GERAL],
                    {"metodo": p.metodo, "kwh_por_banho": e_banho, "consumo_kwh_mes": total})


def responder_fontes(s: Sessao) -> Resposta:
    texto = ("Estas são as fontes usadas nos cálculos e nas recomendações. Valores marcados como estimativa "
             "estão explicados no arquivo data/premissas.json do projeto.")
    from .dados import referencias
    return Resposta("fontes", texto, citar(list(referencias().keys())))


def responder_limitacoes(s: Sessao) -> Resposta:
    p = s.perfil
    sens = alt.sensibilidade(p)
    texto = (
        "Os resultados são estimativas, não garantias. Principais premissas:\n\n"
        "• Água da rede a 20 °C e banho a 38 °C (média anual em São Paulo), iguais em todos os cenários.\n"
        "• Vazão de 4,2 L/min medida pela USP; chuveiros e pressões diferentes mudam o resultado.\n"
        f"• Tarifa de {rs(p.tarifa_kwh)}/kWh com impostos, sem bandeira tarifária e sem iluminação pública.\n"
        "• Aquecedor solar com dimensionamento simplificado (volume proporcional à água quente usada).\n"
        "• Fotovoltaica: crédito valorizado em 85% da tarifa (hipótese da equipe para as regras de transição "
        "da Lei 14.300/2022) e irradiação estimada para a cidade de São Paulo.\n"
        "• Sem reajuste de tarifa, sem juros e sem perda de rendimento dos equipamentos com o tempo.\n\n"
        "Retorno do investimento nos cenários otimista / base / pessimista:\n"
        f"• Aquecedor solar: {anos(sens['B']['otimista'])} / {anos(sens['B']['base'])} / "
        f"{anos(sens['B']['pessimista'])}\n"
        f"• Fotovoltaica: {anos(sens['C']['otimista'])} / {anos(sens['C']['base'])} / "
        f"{anos(sens['C']['pessimista'])}\n\n"
        "Antes de investir, confira a potência do seu chuveiro na etiqueta, sua tarifa na conta de luz e "
        "peça orçamentos a instaladores com selo Inmetro."
    )
    return Resposta("limitacoes", texto, citar(["INMETRO_PBE", "ANEEL_TARIFAS", "CRONOSHARE_PRECO_SOLAR",
                                                 "CRESESB_SUNDATA", "LEI_14300"]),
                    [], {"sensibilidade": sens})


def responder_ajuda(s: Sessao) -> Resposta:
    texto = (
        "Sou o assistente de energia do Citizen Assist AI. Posso ajudar a gastar menos com o banho:\n\n"
        "• 'Quanto gasta meu chuveiro?'\n"
        "• 'Quais as alternativas?' (compara banho consciente, aquecedor solar e placa solar)\n"
        "• 'Dicas para economizar'\n"
        "• 'Aquecedor solar vale a pena?' ou 'E a placa solar?'\n"
        "• 'Tenho tarifa social' • 'Impacto ambiental' • 'Como você calculou?' • 'Fontes' • 'Limitações'\n\n"
        "Para um cálculo da sua casa, conte: '5 pessoas, banho de 12 minutos, chuveiro de 7500 W, tarifa 0,95'."
    )
    return Resposta("ajuda", texto)


def responder_perfil_atualizado(s: Sessao, lidos: list[str]) -> Resposta:
    base = responder_consumo(s)
    base.intencao = "perfil"
    base.texto = "Anotei: " + ", ".join(lidos) + ".\n\n" + base.texto
    return base


RESPOSTAS = {
    "consumo": responder_consumo,
    "comparar": responder_comparar,
    "banho_consciente": responder_banho_consciente,
    "aquecedor_solar": responder_aquecedor_solar,
    "fotovoltaica": responder_fotovoltaica,
    "tarifa_social": responder_tarifa_social,
    "ambiente": responder_ambiente,
    "calculo": responder_calculo,
    "fontes": responder_fontes,
    "limitacoes": responder_limitacoes,
    "ajuda": responder_ajuda,
    "saudacao": responder_ajuda,
}


def responder(mensagem: str, sessao: Sessao | None = None) -> Resposta:
    """Ponto de entrada usado pelo Citizen Assist AI."""
    sessao = sessao or Sessao()
    texto = normalizar(mensagem)
    sessao.perfil, lidos, avisos = extrair_perfil(texto, sessao.perfil)
    intencao = detectar_intencao(texto)

    if avisos and not lidos:
        resposta = Resposta(
            "valor_invalido",
            "Não consegui usar esse valor: " + "; ".join(avisos) + ". "
            "Pode me dizer de novo? Exemplo: '4 pessoas, banho de 8 minutos, chuveiro de 5500 W'.")
        sessao.ultima_intencao = resposta.intencao
        return resposta

    if lidos and intencao in ("", "consumo", "saudacao", "tarifa_social"):
        if intencao == "tarifa_social" and not sessao.perfil.consumo_total_kwh_mes:
            resposta = responder_tarifa_social(sessao)
        else:
            resposta = responder_perfil_atualizado(sessao, lidos)
    elif intencao in RESPOSTAS:
        resposta = RESPOSTAS[intencao](sessao)
        if lidos:
            resposta.texto = "Anotei: " + ", ".join(lidos) + ".\n\n" + resposta.texto
    else:
        resposta = Resposta("nao_entendi",
                            "Não entendi a pergunta. " + responder_ajuda(sessao).texto)
    if avisos:
        resposta.texto = ("Ignorei um valor fora da faixa: " + "; ".join(avisos) + ".\n\n" + resposta.texto)
    sessao.ultima_intencao = resposta.intencao
    return resposta
