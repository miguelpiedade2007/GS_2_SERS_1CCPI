"""Servidor web do assistente de energia (somente biblioteca padrão do Python).

Execução:  python -m app.servidor            → http://localhost:8000
API usada pelo Citizen Assist AI:
    POST /api/energia/mensagem   {"sessao": "abc", "mensagem": "quanto gasta meu chuveiro?"}
        → {"intencao", "texto", "referencias", "limitacoes", "dados", "texto_formatado"}
    POST /api/energia/feedback   {"participante", "pergunta", "intencao", "entendeu", "util", "comentario"}
    GET  /api/energia/comparacao → tabela das alternativas para a família de referência
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from energia import Sessao, responder
from energia import alternativas as alt
from energia.feedback import registrar

PAGINA = Path(__file__).resolve().parent.parent / "web" / "index.html"
SESSOES: dict[str, Sessao] = {}


class Manipulador(BaseHTTPRequestHandler):
    def _json(self, dados: dict, status: int = 200) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _ler_json(self) -> dict:
        tamanho = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(tamanho) or b"{}")
        except json.JSONDecodeError:
            return {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            corpo = PAGINA.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        elif self.path == "/api/energia/comparacao":
            self._json({"situacao_atual": alt.situacao_atual(alt.calc.Perfil()),
                        "alternativas": [r.dicionario() for r in alt.comparar()],
                        "sensibilidade_payback_anos": alt.sensibilidade()})
        else:
            self._json({"erro": "rota não encontrada"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        dados = self._ler_json()
        if self.path == "/api/energia/mensagem":
            mensagem = str(dados.get("mensagem", "")).strip()
            if not mensagem:
                self._json({"erro": "mensagem vazia"}, 400)
                return
            sessao = SESSOES.setdefault(str(dados.get("sessao", "padrao"))[:64], Sessao())
            self._json(responder(mensagem, sessao).dicionario())
        elif self.path == "/api/energia/feedback":
            registrar(str(dados.get("participante", "")), str(dados.get("pergunta", "")),
                      str(dados.get("intencao", "")), bool(dados.get("entendeu")), bool(dados.get("util")),
                      str(dados.get("comentario", "")))
            self._json({"ok": True})
        else:
            self._json({"erro": "rota não encontrada"}, 404)

    def log_message(self, formato: str, *args) -> None:
        return  # não registra IPs nem conteúdo das mensagens


def main() -> None:
    porta = int(os.environ.get("PORTA", 8000))
    print(f"Assistente de energia em http://localhost:{porta}  (Ctrl+C para encerrar)")
    ThreadingHTTPServer(("127.0.0.1", porta), Manipulador).serve_forever()


if __name__ == "__main__":
    main()
