"""Módulo de Energia do Citizen Assist AI – Soluções em Energias Renováveis e Sustentáveis.

Uso pelo assistente principal:

    from energia import Sessao, responder
    sessao = Sessao()
    resposta = responder("Quanto gasta meu chuveiro?", sessao)
    print(resposta.formatada())      # texto pronto para o chat
    resposta.dicionario()            # JSON com texto, fontes, limitações e números
"""

from .assistente import Resposta, Sessao, responder
from .calculos import Perfil

__all__ = ["Perfil", "Resposta", "Sessao", "responder"]
