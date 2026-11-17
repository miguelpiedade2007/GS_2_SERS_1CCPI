"""Cálculos de energia para o aquecimento de água do banho.

Conceitos aplicados:
- Energia térmica para aquecer a água:  Q = m · c · ΔT
- Energia elétrica consumida:           E = Q / η   (η = eficiência do chuveiro)
- Energia pela potência do chuveiro:    E = P · Δt
- Custo:                                C = E · tarifa
- Emissões:                             CO2 = E · fator de emissão do SIN

Método usado: se o usuário informa a potência do chuveiro, E = P · Δt (reflete o
aparelho dele). Caso contrário, usa-se o método físico com a vazão de referência.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .dados import premissas, valor


@dataclass
class Perfil:
    """Situação de uma família. Valores não informados usam a família de referência."""

    pessoas: int = field(default_factory=lambda: int(valor("familia_referencia", "pessoas")))
    banhos_por_pessoa_dia: float = field(default_factory=lambda: valor("familia_referencia", "banhos_por_pessoa_dia"))
    minutos_por_banho: float = field(default_factory=lambda: valor("familia_referencia", "minutos_por_banho"))
    vazao_l_min: float = field(default_factory=lambda: valor("chuveiro", "vazao"))
    tarifa_kwh: float = field(default_factory=lambda: valor("tarifa", "tarifa_kwh"))
    potencia_chuveiro_w: float | None = None  # quando informada, o consumo é calculado por P·t
    tarifa_social: bool = False
    consumo_total_kwh_mes: float | None = None  # consumo da casa inteira (conta de luz)

    def com(self, **alteracoes) -> "Perfil":
        return replace(self, **alteracoes)

    @property
    def banhos_por_mes(self) -> float:
        return self.pessoas * self.banhos_por_pessoa_dia * dias_mes()

    @property
    def metodo(self) -> str:
        return "potencia" if self.potencia_chuveiro_w else "fisico"


def dias_mes() -> int:
    return int(premissas()["periodo_referencia"]["dias_por_mes"])


def delta_t() -> float:
    """Aquecimento necessário (K): mesma condição de conforto em todos os cenários."""
    return valor("chuveiro", "temperatura_banho") - valor("chuveiro", "temperatura_agua_fria")


def energia_banho_kwh(minutos: float, vazao_l_min: float, dt: float | None = None,
                      eficiencia: float | None = None) -> float:
    """Energia elétrica (kWh) de um banho pelo método físico Q = m·c·ΔT / η."""
    dt = delta_t() if dt is None else dt
    eficiencia = valor("chuveiro", "eficiencia_chuveiro") if eficiencia is None else eficiencia
    massa_kg = minutos * vazao_l_min * valor("fisica", "densidade_agua")
    calor_kj = massa_kg * valor("fisica", "calor_especifico_agua") * dt
    return calor_kj / valor("fisica", "kj_por_kwh") / eficiencia


def energia_banho_por_potencia_kwh(potencia_w: float, minutos: float) -> float:
    """Energia elétrica (kWh) de um banho pela potência: E = P · Δt."""
    return potencia_w / 1000 * minutos / 60


def energia_por_banho_kwh(perfil: Perfil, minutos: float | None = None) -> float:
    minutos = perfil.minutos_por_banho if minutos is None else minutos
    if perfil.metodo == "potencia":
        return energia_banho_por_potencia_kwh(perfil.potencia_chuveiro_w, minutos)
    return energia_banho_kwh(minutos, perfil.vazao_l_min)


def consumo_mensal_kwh(perfil: Perfil, minutos: float | None = None) -> float:
    """Consumo mensal médio do chuveiro (kWh/mês), mesma temperatura de banho em todos os cenários."""
    return energia_por_banho_kwh(perfil, minutos) * perfil.banhos_por_mes


def custo(kwh: float, perfil: Perfil) -> float:
    return kwh * perfil.tarifa_kwh


# ------------------------------------------------------------- Tarifa Social

def franquia_social() -> float:
    return valor("tarifa", "franquia_tarifa_social")


def kwh_cobrados_casa(perfil: Perfil) -> float | None:
    """kWh efetivamente cobrados da casa (Tarifa Social isenta os primeiros 80 kWh)."""
    if perfil.consumo_total_kwh_mes is None:
        return None
    if not perfil.tarifa_social:
        return perfil.consumo_total_kwh_mes
    return max(0.0, perfil.consumo_total_kwh_mes - franquia_social())


def kwh_faturavel_evitado(kwh_economizado: float, perfil: Perfil) -> float:
    """Parte de uma redução de consumo que realmente diminui o valor cobrado.

    Na Tarifa Social (Lei 15.235/2025) os primeiros 80 kWh/mês são isentos; só a
    redução que incide sobre o excedente diminui a conta.
    """
    if not perfil.tarifa_social or perfil.consumo_total_kwh_mes is None:
        return kwh_economizado
    return min(kwh_economizado, kwh_cobrados_casa(perfil))


def custo_chuveiro_faturado(perfil: Perfil) -> float:
    """Quanto a conta cairia se o chuveiro não fosse usado (visão marginal).

    Sem Tarifa Social é o custo equivalente (kWh × tarifa). Com Tarifa Social e
    consumo informado, só a parte do chuveiro acima da franquia é cobrada.
    """
    return custo(kwh_faturavel_evitado(consumo_mensal_kwh(perfil), perfil), perfil)


# ------------------------------------------------------------- outros

def co2_kg(kwh: float, campo: str = "valor") -> float:
    return kwh * valor("emissoes", "fator_emissao_sin", campo)


def agua_litros_mes(perfil: Perfil, minutos: float | None = None) -> float:
    minutos = perfil.minutos_por_banho if minutos is None else minutos
    return minutos * perfil.vazao_l_min * perfil.banhos_por_mes


def payback_anos(investimento: float, economia_anual: float, manutencao_anual: float) -> float:
    liquido = economia_anual - manutencao_anual
    if investimento <= 0:
        return 0.0
    if liquido <= 0:
        return float("inf")
    return investimento / liquido
