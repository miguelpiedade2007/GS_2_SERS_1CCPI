# Citizen Assist AI · Módulo de Energia no Banho

**Global Solution 2026.2 – Ciência da Computação (1CC)**
**Disciplina: Soluções em Energias Renováveis e Sustentáveis**

Este repositório contém a contribuição de energia ao **Citizen Assist AI**. É um assistente que ajuda o cidadão a entender quanto o chuveiro elétrico gasta e a escolher entre três caminhos: economizar no hábito, aquecer a água com o sol ou gerar a própria eletricidade. As recomendações vêm de cálculos documentados e sempre trazem fontes e limitações.

## Integrante

| Nome completo | RM |
|Miguel Anção Rotílio Piedade|572445|


## Público e problema

- **Público:** famílias da cidade de São Paulo que usam chuveiro elétrico, com foco nas de baixa e média renda, incluindo as beneficiárias da Tarifa Social.
- **Necessidade energética:** aquecer a água do banho gastando menos. O chuveiro elétrico é um dos equipamentos que mais consomem numa casa. Ele trabalha com 4 a 7,5 kW e se concentra no horário de pico (18h às 21h).
- **Situação de referência:** família de 4 pessoas com banhos de 10 minutos consome **111 kWh/mês** no chuveiro, cerca de **R$ 100 por mês** na conta.

## Funcionalidades de energia

| Pergunta do cidadão | O que o assistente faz |
|---|---|
| "Quanto gasta meu chuveiro?" | Calcula kWh e R$ por banho, por mês e por ano (Q = m·c·ΔT, conferido por E = P·t) |
| "5 pessoas, banho de 12 minutos, chuveiro de 7500 W, tarifa 0,95" | Atualiza o perfil da família e refaz todos os cálculos |
| "Quais as alternativas?" | Compara banho consciente, aquecedor solar, fotovoltaica e a combinação: economia, investimento, retorno, CO₂, água e telhado |
| "Dicas para economizar" | Orientações de custo quase zero e economia estimada |
| "Aquecedor solar vale a pena?" / "E a placa solar?" | Detalha cada fonte renovável, com faixa otimista e pessimista do retorno |
| "Temos tarifa social e consumo de 150 kWh" | Aplica a franquia de 80 kWh da Lei 15.235/2025 e recalcula a economia real em reais |
| "Impacto ambiental" | Emissões evitadas, água poupada, efeito no pico de demanda e ciclo de vida |
| "Como você calculou?" / "Fontes" / "Limitações" | Mostra a conta passo a passo, as referências e as premissas |

## Resultado principal

Família de referência: 4 pessoas, banho de 10 min, mesma temperatura de banho em todas as alternativas. Tabela gerada pelo código.

<!-- gerado:readme_resumo -->
| Alternativa | Redução na conta/mês | Investimento | Retorno (base, faixa) |
|---|---|---|---|
| A) Banho consciente (7 min, mesma temperatura) | 33 kWh evitados · R$ 29,98 | R$ 30 | ≈ 1 mês |
| B) Aquecedor solar de água (200 L, termossifão) | 78 kWh evitados · R$ 69,95 | R$ 5.000 | 7,3 anos (3,1 a 18,3) |
| C) Energia solar fotovoltaica (1,10 kWp, 2 módulos) | 111 kWh compensados · R$ 85,20 | R$ 3.850 | 4,2 anos (2,3 a 7,8) |
| A+B) Banho consciente + aquecedor solar (150 L) | 88 kWh evitados · R$ 78,95 | R$ 4.155 | 5,2 anos (2,4 a 11,4) |
<!-- /gerado:readme_resumo -->

A análise completa está em [`docs/analise_energetica.md`](docs/analise_energetica.md): contexto, dados, cálculos, comparação, custos, viabilidade, impactos ambientais e limitações.

## Como executar

Requer **Python 3.10 ou superior** e nenhuma biblioteca externa.

```bash
# Chat no terminal
python -m app.cli

# Interface web e API (abre em http://localhost:8000)
python -m app.servidor

# Gerar as tabelas da análise (pasta resultados/)
python -m scripts.gerar_analise

# Testes automatizados
python -m unittest discover -s tests -t .
```

## Integração com o Citizen Assist AI

O módulo é independente e pode ser chamado de duas formas.

**Em Python** (mesmo processo do assistente):

```python
from energia import Sessao, responder

sessao = Sessao()                       # uma por conversa
r = responder("Quais as alternativas?", sessao)
r.formatada()      # texto pronto para o chat, com "Importante" e "Fontes"
r.dicionario()     # {intencao, texto, referencias, limitacoes, dados}
```

**Por HTTP** (outro serviço ou front-end):

```http
POST /api/energia/mensagem
{"sessao": "id-da-conversa", "mensagem": "quanto gasta meu chuveiro?"}
```

A resposta traz `texto`, `referencias` (título e URL), `limitacoes` e `dados` (números usados). O assistente principal pode encaminhar ao módulo as mensagens sobre energia, conta de luz, chuveiro ou energia solar. `GET /api/energia/comparacao` devolve a tabela completa das alternativas.

## Estrutura do repositório

```
├── energia/                 # Código do módulo (contribuição da disciplina)
│   ├── calculos.py          # Energia, potência, custo, CO2, água, Tarifa Social, payback
│   ├── alternativas.py      # Alternativas A, B, C e A+B, com sensibilidade
│   ├── assistente.py        # Intenções, leitura do perfil e respostas com fontes e limitações
│   ├── feedback.py          # Registro anônimo dos testes com usuários
│   └── dados.py             # Leitura das premissas e referências
├── data/
│   ├── premissas.json       # Dados usados: valor, unidade, tipo (público/estimado), fonte e justificativa
│   └── referencias.json     # Fontes citadas pelo assistente
├── docs/
│   ├── analise_energetica.md  # Cálculos, comparação e justificativas
│   └── referencias.md         # Lista de referências
├── resultados/              # Tabelas geradas (CSV e Markdown)
├── testes/                  # Protocolo, registros dos testes com usuários e ajustes
├── app/                     # Chat no terminal e servidor web/API
├── web/index.html           # Interface do chat
└── tests/                   # Testes automatizados (unittest)
```

## Limitações

Os valores são **estimativas** para uma família de referência em São Paulo, não garantias de economia. Os resultados dependem do chuveiro, dos hábitos, da tarifa e do preço cobrado por instaladores. A lista completa está na seção 7 da [análise](docs/analise_energetica.md#7-limitações) e o assistente a mostra quando o cidadão pergunta "limitações".
