"""Comparação das alternativas para a mesma necessidade (água quente a 38 °C no banho)
e o mesmo período de referência (mês médio e horizonte de 10 anos).

A)   Banho consciente – banho de 7 min, mesma temperatura (economia de energia)
B)   Aquecedor solar de água – termossifão dimensionado para a família (renovável)
C)   Energia solar fotovoltaica – geração distribuída que compensa o chuveiro na conta (renovável)
A+B) Combinação

Separação de conceitos:
- energia_evitada_kwh_mes:    o chuveiro deixa de puxar essa energia da rede (A e B);
- energia_compensada_kwh_mes: o chuveiro continua consumindo, mas a geração solar
                              diurna vira crédito que abate a conta (C).
A posição "verão" é tratada à parte (modo_verao_adicional), porque reduz a
temperatura do banho, ou seja, muda a condição de conforto.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from . import calculos as calc
from .dados import premissas, valor

INVERTER = {"valor": "valor", "min": "max", "max": "min"}  # para custos: cenário pessimista usa o máximo


@dataclass
class Resultado:
    codigo: str
    nome: str
    renovavel: bool
    consumo_kwh_mes: float             # energia que o chuveiro ainda puxa da rede (medida física)
    energia_evitada_kwh_mes: float     # redução física do consumo
    energia_compensada_kwh_mes: float  # créditos de geração usados na conta
    economia_kwh_mes: float            # evitada + compensada (redução nos kWh da conta)
    economia_rs_mes: float
    investimento_rs: float
    manutencao_rs_ano: float
    payback_anos: float
    saldo_horizonte_rs: float          # economia acumulada – investimento – manutenção no horizonte
    custo_kwh_evitado_rs: float        # (investimento + manutenção) / kWh reduzidos no horizonte
    co2_evitado_kg_ano: float
    agua_economizada_l_mes: float
    area_telhado_m2: float
    reduz_pico_noturno: bool
    viabilidade: list[str] = field(default_factory=list)
    limitacoes: list[str] = field(default_factory=list)
    detalhes: dict = field(default_factory=dict)

    def dicionario(self) -> dict:
        d = asdict(self)
        for chave in ("payback_anos", "custo_kwh_evitado_rs"):
            if math.isinf(d[chave]):
                d[chave] = None
        return d


def horizonte() -> int:
    return int(premissas()["periodo_referencia"]["horizonte_anos"])


def _montar(codigo, nome, renovavel, perfil, consumo_kwh, evitada, compensada, investimento, manutencao,
            agua_l, area, reduz_pico, viabilidade, limitacoes, fator_valor=1.0, detalhes=None) -> Resultado:
    economia_kwh = evitada + compensada
    kwh_faturavel = calc.kwh_faturavel_evitado(economia_kwh, perfil)
    economia_rs_mes = calc.custo(kwh_faturavel, perfil) * fator_valor
    economia_ano = economia_rs_mes * 12
    n = horizonte()
    kwh_horizonte = economia_kwh * 12 * n
    return Resultado(
        codigo=codigo, nome=nome, renovavel=renovavel,
        consumo_kwh_mes=consumo_kwh,
        energia_evitada_kwh_mes=evitada,
        energia_compensada_kwh_mes=compensada,
        economia_kwh_mes=economia_kwh,
        economia_rs_mes=economia_rs_mes,
        investimento_rs=investimento,
        manutencao_rs_ano=manutencao,
        payback_anos=calc.payback_anos(investimento, economia_ano, manutencao),
        saldo_horizonte_rs=economia_ano * n - investimento - manutencao * n,
        custo_kwh_evitado_rs=(investimento + manutencao * n) / kwh_horizonte if kwh_horizonte else float("inf"),
        co2_evitado_kg_ano=calc.co2_kg(economia_kwh * 12),
        agua_economizada_l_mes=agua_l,
        area_telhado_m2=area,
        reduz_pico_noturno=reduz_pico,
        viabilidade=viabilidade,
        limitacoes=limitacoes,
        detalhes=detalhes or {},
    )


def situacao_atual(perfil: calc.Perfil) -> dict:
    kwh = calc.consumo_mensal_kwh(perfil)
    dados = {
        "metodo": perfil.metodo,
        "consumo_kwh_mes": kwh,
        "custo_rs_mes": calc.custo(kwh, perfil),              # custo equivalente, sem benefícios
        "custo_rs_ano": calc.custo(kwh, perfil) * 12,
        "custo_faturado_chuveiro_rs_mes": calc.custo_chuveiro_faturado(perfil),
        "co2_kg_ano": calc.co2_kg(kwh * 12),
        "agua_l_mes": calc.agua_litros_mes(perfil),
        "kwh_por_banho": calc.energia_por_banho_kwh(perfil),
        "potencia_media_kw": calc.energia_por_banho_kwh(perfil) / (perfil.minutos_por_banho / 60),
    }
    cobrados = calc.kwh_cobrados_casa(perfil)
    if cobrados is not None:
        dados["kwh_cobrados_casa_mes"] = cobrados
        dados["energia_cobrada_casa_rs_mes"] = calc.custo(cobrados, perfil)
    return dados


# ------------------------------------------------------------- A) banho consciente

def minutos_meta(perfil: calc.Perfil) -> float:
    return min(perfil.minutos_por_banho, valor("alternativa_banho_consciente", "minutos_meta"))


def banho_consciente(perfil: calc.Perfil, campo: str = "valor") -> Resultado:
    base = calc.consumo_mensal_kwh(perfil)
    meta = minutos_meta(perfil)
    novo = calc.consumo_mensal_kwh(perfil, minutos=meta)
    agua = calc.agua_litros_mes(perfil) - calc.agua_litros_mes(perfil, minutos=meta)
    return _montar(
        "A", f"Banho consciente ({meta:g} min, mesma temperatura)", False, perfil, novo, base - novo, 0.0,
        valor("alternativa_banho_consciente", "investimento"),
        valor("alternativa_banho_consciente", "manutencao_anual"),
        agua, 0.0, True,
        ["Pode começar hoje, sem obra e quase sem custo.",
         "Serve para quem mora de aluguel, em apartamento ou sem telhado disponível.",
         "Reduz energia e água na mesma proporção do tempo de banho."],
        ["Depende da mudança de hábito de todos os moradores."],
        detalhes={"minutos_antes": perfil.minutos_por_banho, "minutos_depois": meta,
                  "reducao_percentual": (1 - meta / perfil.minutos_por_banho) * 100},
    )


def modo_verao_adicional(perfil: calc.Perfil, minutos: float | None = None) -> dict:
    """Economia extra (kWh/mês, média anual) de usar a posição verão nos meses quentes.

    Hipótese explícita: nesses meses a família aceita um banho menos quente; a
    posição verão usa ~55% da potência da posição inverno. Não entra na comparação
    principal porque muda a condição de conforto.
    """
    consumo = calc.consumo_mensal_kwh(perfil, minutos=minutos)
    razao = valor("chuveiro", "razao_potencia_verao")
    meses = valor("chuveiro", "meses_modo_verao")
    kwh = consumo * (1 - razao) * meses / 12
    return {"kwh_mes": kwh, "rs_mes": calc.custo(calc.kwh_faturavel_evitado(kwh, perfil), perfil),
            "razao_potencia": razao, "meses": meses}


# ------------------------------------------------------------- B) aquecedor solar

def dimensionar_aquecedor(perfil: calc.Perfil, minutos: float | None = None, campo: str = "valor") -> dict:
    """Dimensionamento simplificado: volume proporcional à água quente usada por dia."""
    minutos = perfil.minutos_por_banho if minutos is None else minutos
    g = "alternativa_aquecedor_solar"
    demanda_l_dia = perfil.pessoas * perfil.banhos_por_pessoa_dia * minutos * perfil.vazao_l_min
    necessario = demanda_l_dia * valor(g, "litros_reservatorio_por_litro_banho")
    tamanhos = premissas()[g]["volumes_comerciais"]["valor"]
    volume = next((v for v in tamanhos if v >= necessario), tamanhos[-1])
    excede = necessario > tamanhos[-1]
    area = volume / 100 * valor(g, "area_coletor_por_100l")
    fator_custo = valor(g, "fator_custo", INVERTER[campo])
    investimento = (valor(g, "custo_fixo") + valor(g, "custo_por_litro") * volume) * fator_custo
    return {"demanda_l_dia": demanda_l_dia, "volume_necessario_l": necessario, "volume_l": volume,
            "area_m2": area, "investimento_rs": investimento, "excede_residencial": excede}


def aquecedor_solar(perfil: calc.Perfil, campo: str = "valor", minutos: float | None = None,
                    codigo: str = "B", nome: str | None = None) -> Resultado:
    base = calc.consumo_mensal_kwh(perfil)
    referencia = calc.consumo_mensal_kwh(perfil, minutos=minutos)
    dim = dimensionar_aquecedor(perfil, minutos, campo)
    fracao = valor("alternativa_aquecedor_solar", "fracao_solar", campo)
    novo = referencia * (1 - fracao)
    limitacoes = [
        "Dimensionamento simplificado: o volume é proporcional à água quente usada por dia. "
        "O projeto real deve ser feito por instalador conforme a NBR 15569.",
        "Exige telhado próprio ou autorização do condomínio/proprietário.",
        "Em dias nublados seguidos e no inverno o chuveiro elétrico continua sendo usado como apoio.",
        "O preço varia muito entre instaladores; peça pelo menos três orçamentos.",
    ]
    if dim["excede_residencial"]:
        limitacoes.insert(0, "O consumo informado passa do maior sistema residencial considerado "
                             f"({dim['volume_l']} L); a estimativa fica otimista e é preciso um projeto específico.")
    return _montar(
        codigo, nome or f"Aquecedor solar de água ({dim['volume_l']} L, termossifão)", True, perfil,
        novo, base - novo, 0.0, dim["investimento_rs"],
        valor("alternativa_aquecedor_solar", "manutencao_anual"), 0.0, dim["area_m2"], True,
        ["Usa o calor do sol diretamente: um coletor converte cerca de metade da radiação em calor, "
         "enquanto um painel fotovoltaico converte cerca de 20% em eletricidade.",
         "Reduz o uso do chuveiro no horário de pico (18h às 21h), aliviando a rede.",
         f"Precisa de cerca de {dim['area_m2']:.1f} m² de telhado voltado para o norte e estrutura "
         "para o reservatório.".replace(".", ",", 1)],
        limitacoes,
        detalhes={**dim, "fracao_solar": fracao},
    )


# ------------------------------------------------------------- C) fotovoltaica

def fotovoltaica(perfil: calc.Perfil, campo: str = "valor") -> Resultado:
    g = "alternativa_fotovoltaica"
    base = calc.consumo_mensal_kwh(perfil)
    hsp = valor(g, "hsp", campo)
    pr = valor(g, "performance_ratio")
    modulo = valor(g, "potencia_modulo_kwp")
    geracao_por_kwp = hsp * calc.dias_mes() * pr
    # o sistema é dimensionado com a irradiação de referência e mantido fixo nos cenários
    modulos = max(1, math.ceil(base / (valor(g, "hsp") * calc.dias_mes() * pr * modulo) - 1e-9))
    kwp = modulos * modulo
    geracao = kwp * geracao_por_kwp

    limitacoes = [
        "O chuveiro continua puxando a mesma energia da rede à noite; a geração acontece de dia e vira crédito.",
        "Cada kWh de crédito foi valorizado em 85% da tarifa. Esse percentual é uma hipótese simplificada da "
        "equipe para a cobrança gradual do 'Fio B' na Lei 14.300/2022, não um valor fixado em lei; "
        "as regras de transição tornam o retorno de 10 anos menos preciso.",
        "A taxa mínima de disponibilidade da conta continua sendo cobrada.",
        "Sistemas muito pequenos custam mais por kWp; exige telhado próprio e projeto aprovado pela distribuidora.",
    ]
    disponibilidade = valor(g, "consumo_minimo_disponibilidade")
    if perfil.consumo_total_kwh_mes is not None:
        aproveitavel = max(0.0, perfil.consumo_total_kwh_mes - disponibilidade)
        compensada = min(geracao, aproveitavel)
        if compensada < geracao:
            limitacoes.insert(0, f"Com consumo de {perfil.consumo_total_kwh_mes:.0f} kWh/mês, só "
                                 f"{compensada:.0f} kWh dos {geracao:.0f} kWh gerados abatem a conta; "
                                 "o restante vira crédito sem uso imediato.")
    else:
        compensada = geracao
        limitacoes.insert(0, f"Supõe que a casa consome pelo menos {geracao + disponibilidade:.0f} kWh/mês "
                             f"(geração + {disponibilidade:.0f} kWh de disponibilidade). "
                             "Informe o consumo da conta para recalcular.")

    preco = valor(g, "preco_wp", INVERTER[campo])
    fator = valor(g, "fator_compensacao", campo)
    nome = f"Energia solar fotovoltaica ({kwp:.2f} kWp, {modulos} módulos)".replace(".", ",")
    return _montar(
        "C", nome, True, perfil, base, 0.0, compensada, kwp * 1000 * preco,
        valor(g, "manutencao_anual"), 0.0, modulos * valor(g, "area_por_modulo"), False,
        ["Gera créditos de energia que abatem a conta da casa toda, não só do chuveiro.",
         "Não muda o hábito de banho nem a instalação hidráulica."],
        limitacoes, fator_valor=fator,
        detalhes={"kwp": kwp, "modulos": modulos, "geracao_kwh_mes": geracao, "fator_compensacao": fator},
    )


# ------------------------------------------------------------- A+B

def combinada(perfil: calc.Perfil, campo: str = "valor") -> Resultado:
    a = banho_consciente(perfil, campo)
    meta = minutos_meta(perfil)
    b = aquecedor_solar(perfil, campo, minutos=meta, codigo="A+B")
    b.nome = f"Banho consciente + aquecedor solar ({b.detalhes['volume_l']} L)"
    b.investimento_rs += a.investimento_rs
    b.agua_economizada_l_mes = a.agua_economizada_l_mes
    economia_ano = b.economia_rs_mes * 12
    n = horizonte()
    b.payback_anos = calc.payback_anos(b.investimento_rs, economia_ano, b.manutencao_rs_ano)
    b.saldo_horizonte_rs = economia_ano * n - b.investimento_rs - b.manutencao_rs_ano * n
    b.custo_kwh_evitado_rs = (b.investimento_rs + b.manutencao_rs_ano * n) / (b.economia_kwh_mes * 12 * n)
    b.viabilidade = ["Começa pelo hábito (custo zero) e depois reduz ainda mais com o sol; "
                     "o aquecedor pode ser menor porque a demanda de água quente cai."]
    return b


def comparar(perfil: calc.Perfil | None = None, campo: str = "valor") -> list[Resultado]:
    perfil = perfil or calc.Perfil()
    return [banho_consciente(perfil, campo), aquecedor_solar(perfil, campo),
            fotovoltaica(perfil, campo), combinada(perfil, campo)]


def sensibilidade(perfil: calc.Perfil | None = None) -> dict[str, dict[str, float]]:
    """Payback (anos) nos cenários pessimista, base e otimista.

    Pessimista: tarifa mínima, investimento máximo, menor fração solar/irradiação/crédito.
    Otimista:   tarifa máxima, investimento mínimo, maior fração solar/irradiação/crédito.
    """
    perfil = perfil or calc.Perfil()
    cenarios = {
        "pessimista": ("min", perfil.com(tarifa_kwh=valor("tarifa", "tarifa_kwh", "min"))),
        "base": ("valor", perfil),
        "otimista": ("max", perfil.com(tarifa_kwh=valor("tarifa", "tarifa_kwh", "max"))),
    }
    tabela: dict[str, dict[str, float]] = {}
    for nome, (campo, p) in cenarios.items():
        for r in comparar(p, campo):
            tabela.setdefault(r.codigo, {})[nome] = r.payback_anos
    return tabela
