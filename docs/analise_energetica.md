# Análise energética – Água quente no banho

Contribuição da disciplina **Soluções em Energias Renováveis e Sustentáveis** ao Citizen Assist AI.

As tabelas de resultados deste documento e do README são geradas pelo código (`python -m scripts.gerar_analise`) a partir de [`data/premissas.json`](../data/premissas.json). Um teste automatizado falha se algum documento ficar com números diferentes dos calculados. As respostas do assistente usam as mesmas funções.

---

## 1. Contexto

**Público:** famílias que moram na cidade de São Paulo e usam chuveiro elétrico. O foco são as famílias de baixa e média renda, para quem a conta de luz pesa mais no orçamento, e isso inclui as beneficiárias da Tarifa Social.

**Necessidade energética:** aquecer a água do banho gastando menos. O chuveiro elétrico está presente na grande maioria das casas brasileiras e é um dos equipamentos de maior consumo residencial, segundo a Pesquisa de Posse e Hábitos (PPH) do Procel. Ele aquece a água no instante do uso, com potência de 4 a 7,5 kW, e o uso se concentra entre 18h e 21h, o horário de pico do sistema elétrico.

**Como as orientações ajudam:** o cidadão pergunta ao Citizen Assist AI quanto o banho custa e o que pode fazer. O assistente calcula a situação da família com os dados que ela informa, compara as alternativas e recomenda a mais adequada ao caso (inquilino ou proprietário, com ou sem Tarifa Social). Cada resposta informa as fontes e as limitações.

---

## 2. Dados e premissas

| Premissa | Valor | Unidade | Tipo | Origem |
|---|---|---|---|---|
| Moradores | 4 | pessoas | estimado | família de referência, ajustável no chat |
| Banhos | 1 | banho/pessoa/dia | estimado | ajustável no chat |
| Duração do banho | 10 | min | estimado | ajustável no chat |
| Vazão do chuveiro elétrico | 4,2 (3 a 6) | L/min | público | estudo USP divulgado pelo Idec |
| Temperatura da água fria | 20 | °C | estimado | média anual de São Paulo (INMET), **igual em todos os cenários** |
| Temperatura do banho | 38 | °C | estimado | conforto usual em projetos (NBR 15569), **igual em todos os cenários** |
| Eficiência do chuveiro | 0,95 | – | estimado | resistência imersa, perdas pequenas |
| Potência nominal de referência | 5.500 | W | público | potência mais comum no PBE/Inmetro |
| Tarifa com tributos | 0,90 (0,80 a 1,05) | R$/kWh | estimado | TUSD + TE da Enel SP em 2026 (≈ R$ 0,725 sem tributos), mais PIS/COFINS e ICMS |
| Franquia da Tarifa Social | 80 | kWh/mês | público | ANEEL; Lei 15.235/2025 |
| Fator de emissão do SIN | 0,0385 (0,025 a 0,090) | kgCO₂/kWh | público | MCTI/SIRENE, média de 2023 |
| Custo de disponibilidade | 50 | kWh/mês | público | ANEEL REN 1.000/2021 (ligação bifásica) |
| Irradiação no plano inclinado (HSP) | 4,5 (4,1 a 4,9) | kWh/m²·dia | estimado | São Paulo (−23,55°; −46,63°), inclinação próxima da latitude, face norte; faixa de valores publicados para a região |
| Módulo fotovoltaico | 0,55 kWp; 2,6 m² | – | estimado | potência e área típicas de módulos comerciais de 540 a 600 Wp |
| Crédito da energia compensada | 85% (75 a 95%) da tarifa | – | estimado | **hipótese simplificada da equipe** para a transição do "Fio B" (Lei 14.300/2022), não um percentual fixado em lei |
| Período de referência | mês médio do ano e horizonte de 10 anos | – | – | igual para todas as alternativas |

Cada premissa traz no JSON o tipo (`publico`, `estimado` ou `fisico`), a fonte e a justificativa.

---

## 3. Consumo atual (linha de base)

**Conceitos:** energia térmica para aquecer a água, $Q = m \cdot c \cdot \Delta T$. A energia elétrica é $E = Q/\eta$. A potência é energia por tempo, $E = P \cdot \Delta t$.

O método depende do que o usuário informa:
- **Sem potência informada:** método físico, com a vazão de referência.
- **Com potência informada** (por exemplo "chuveiro de 7500 W"): $E = P \cdot \Delta t$, que reflete o aparelho real da família. A explicação "Como você calculou?" mostra sempre o mesmo método e os mesmos dados usados no resultado.

Família de referência (método físico):

| Passo | Cálculo | Resultado |
|---|---|---|
| Água por banho | 4,2 L/min × 10 min | 42 L ≈ 42 kg |
| Aquecimento necessário | 38 − 20 °C | ΔT = 18 K |
| Energia térmica | 42 × 4,186 × 18 | 3.165 kJ |
| Energia elétrica por banho | 3.165 ÷ 3.600 ÷ 0,95 | **0,925 kWh** |
| Conferência pela potência | 5,5 kW × (10/60) h | 0,917 kWh (diferença < 1%) |
| Banhos por mês | 4 × 1 × 30 | 120 |
| **Consumo mensal** | 0,925 × 120 | **111,0 kWh/mês** |

<!-- gerado:linha_base -->
Situação atual: **111,0 kWh/mês** · **R$ 99,94/mês** (R$ 1.199,22/ano) · 51,3 kgCO₂/ano · 5.040 L de água/mês
<!-- /gerado:linha_base -->

O método físico e o método pela potência chegam a valores praticamente iguais. Isso confirma que as premissas de vazão e de temperatura são coerentes com um chuveiro real de 5.500 W.

**Custo equivalente × valor cobrado:** o custo acima é o custo equivalente, kWh × tarifa, sem benefícios. Para família com Tarifa Social que informa o consumo da casa, o assistente mostra também o que é efetivamente cobrado. Exemplo com consumo de 150 kWh: (150 − 80) × R$ 0,90 = R$ 63,00 de energia, antes de outras cobranças. O peso real do chuveiro na conta fica limitado a esses R$ 63,00, mesmo que o custo equivalente dele seja R$ 99,94.

---

## 4. Alternativas comparadas

Todas atendem à **mesma necessidade** (120 banhos por mês a 38 °C, com água fria a 20 °C) no **mesmo período** (mês médio, horizonte de 10 anos).

### A) Banho consciente – economia de energia, sem fonte nova
- O banho passa de 10 para 7 minutos, com a **mesma temperatura**, usando um temporizador de R$ 30.
- Energia e água caem na mesma proporção do tempo, 30%: 111,0 × 0,7 = **77,7 kWh/mês**.
- **Posição verão (dica adicional, fora da comparação):** nos meses quentes, a família pode aceitar um banho menos quente usando a posição verão, que tem cerca de 55% da potência da posição inverno (hipótese explícita). Isso muda a condição de conforto, então o valor é mostrado à parte e não entra no retorno de A.

### B) Aquecedor solar de água (termossifão) – fonte renovável térmica
- **Dimensionamento:** demanda diária de água a 38 °C = pessoas × banhos × minutos × vazão = 4 × 1 × 10 × 4,2 = 168 L/dia. Reservatório = 168 × 1,19 ≈ 200 L, arredondado para o tamanho comercial acima. A área de coletores é cerca de 1 m² por 100 L.
- **Custo proporcional ao tamanho:** R$ 1.500 de custo fixo + R$ 17,50 por litro. Para 200 L, isso dá R$ 5.000, o centro da faixa de mercado de R$ 3.000 a R$ 8.000. A faixa de preço entre instaladores (×0,6 a ×1,6) entra na sensibilidade.
- **Fração solar anual de 70%** (faixa de 55 a 80%): o sol fornece 70% da energia de aquecimento no ano, e o resto vem do chuveiro como apoio. Consumo restante: 111,0 × 0,30 = **33,3 kWh/mês**.
- Como o sistema é redimensionado para cada família, famílias maiores recebem reservatório, área e investimento maiores. Acima de 1.000 L, o assistente avisa que é preciso projeto específico.

### C) Energia solar fotovoltaica – fonte renovável elétrica
- Geração por kWp: HSP 4,5 × 30 dias × PR 0,75 = 101,25 kWh/kWp·mês.
- Para cobrir 111,0 kWh são necessários 111,0 ÷ (101,25 × 0,55) = 1,99, ou seja, **2 módulos de 550 Wp (1,10 kWp)**, que geram 111,4 kWh/mês.
- **Consumo × compensação:** o chuveiro continua consumindo os mesmos 111,0 kWh da rede à noite. A geração diurna é injetada na rede e vira crédito que **compensa** esse consumo na conta.
- **Aproveitamento do crédito:** a conta nunca fica abaixo do custo de disponibilidade (50 kWh bifásico). Por isso todo o crédito só é aproveitado se a casa consumir pelo menos 111,4 + 50 ≈ 161 kWh/mês. Quando o usuário informa o consumo da casa, o assistente limita a compensação ao que pode ser abatido.
- **Valor do crédito:** a Lei 14.300/2022 prevê a cobrança gradual de parte da tarifa (o "Fio B") sobre a energia compensada. Adotamos a **hipótese simplificada** de que cada kWh compensado vale 85% da tarifa (faixa de 75 a 95% na sensibilidade). Isso não é um percentual fixado em lei, e as regras de transição tornam o retorno de 10 anos menos preciso.
- Investimento: 1.100 Wp × R$ 3,50/Wp = R$ 3.850. Manutenção de R$ 100 por ano.

### A+B) Combinação
O banho consciente é aplicado primeiro. A demanda cai para 117,6 L/dia, o que permite um aquecedor menor (150 L), que atende o consumo restante: 77,7 × 0,30 = **23,3 kWh/mês**.

---

## 5. Resultados

<!-- gerado:comparacao -->
| Alt. | Alternativa | Renovável | Consumo do chuveiro na rede (kWh/mês) | Energia evitada (kWh/mês) | Energia compensada na conta (kWh/mês) | Economia R$/mês | Investimento R$ | Manutenção R$/ano | Retorno (anos) | Saldo 10 anos R$ | R$ por kWh reduzido | CO₂ evitado kg/ano | Água poupada L/mês | Telhado m² | Reduz pico 18–21h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | Banho consciente (7 min, mesma temperatura) | não | 77,7 | 33,3 | 0,0 | 29,98 | 30,00 | 0,00 | 0,08 | 3.567,67 | 0,008 | 15,4 | 1.512 | 0,0 | sim |
| B | Aquecedor solar de água (200 L, termossifão) | sim | 33,3 | 77,7 | 0,0 | 69,95 | 5.000,00 | 150,00 | 7,25 | 1.894,56 | 0,697 | 35,9 | 0 | 2,0 | sim |
| C | Energia solar fotovoltaica (1,10 kWp, 2 módulos) | sim | 111,0 | 0,0 | 111,4 | 85,20 | 3.850,00 | 100,00 | 4,17 | 5.374,23 | 0,363 | 51,5 | 0 | 5,2 | não |
| A+B | Banho consciente + aquecedor solar (150 L) | sim | 23,3 | 87,7 | 0,0 | 78,95 | 4.155,00 | 150,00 | 5,21 | 3.818,86 | 0,537 | 40,5 | 1.512 | 1,5 | sim |

Na alternativa C o chuveiro continua consumindo a mesma energia da rede à noite; a geração solar diurna vira crédito que **compensa** esse consumo na conta. Supõe-se que a casa consuma ao menos 161 kWh/mês (geração + 50 kWh de disponibilidade) para aproveitar todo o crédito. O crédito é valorizado em 85% da tarifa, hipótese simplificada da equipe (não é percentual fixado em lei).

Dimensionamento do aquecedor solar: B usa reservatório de 200 L (168 L/dia de água a 38 °C); A+B usa 150 L (118 L/dia).

Dica adicional, fora da comparação (muda a temperatura do banho): usar a posição verão de outubro a março pouparia mais 17,5 kWh/mês na média anual (R$ 15,74/mês).
<!-- /gerado:comparacao -->

**Fórmulas:** retorno = investimento ÷ (economia anual − manutenção anual). Saldo em 10 anos = economia anual × 10 − investimento − manutenção × 10. R$ por kWh reduzido = (investimento + manutenção × 10) ÷ kWh reduzidos na conta em 10 anos.

### Sensibilidade do retorno (anos)

<!-- gerado:sensibilidade -->
| Alt. | Otimista | Base | Pessimista |
|---|---|---|---|
| A | 0,07 | 0,08 | 0,09 |
| B | 3,10 | 7,25 | 18,34 |
| C | 2,28 | 4,17 | 7,85 |
| A+B | 2,38 | 5,21 | 11,43 |
<!-- /gerado:sensibilidade -->

- **Otimista:** tarifa de R$ 1,05, menor investimento, fração solar de 80%, HSP de 4,9 e crédito de 95%.
- **Pessimista:** tarifa de R$ 0,80, maior investimento, fração solar de 55%, HSP de 4,1 e crédito de 75%.

O aquecedor solar sozinho é a alternativa mais sensível ao preço de compra. No cenário pessimista, o retorno passa da vida útil esperada (cerca de 15 anos). Por isso o assistente recomenda pedir três orçamentos. Combinado ao banho consciente (A+B), o sistema fica menor e mais barato, e o retorno melhora.

---

## 6. Justificativa das recomendações

### Custos
- **A** tem o menor custo por kWh reduzido e se paga em cerca de um mês. É a primeira recomendação para qualquer família.
- **C** tem hoje o melhor retorno entre as renováveis isoladas, porque o preço dos módulos caiu muito. A condição é a casa consumir o suficiente para aproveitar os créditos.
- **B** custa mais por kWh reduzido com os preços de referência. **A+B** reduz o tamanho do aquecedor e o investimento, e o retorno chega a ficar próximo do da fotovoltaica.

### Viabilidade
| Critério | A | B | C |
|---|---|---|---|
| Serve para quem mora de aluguel ou em apartamento | sim | depende do proprietário ou do condomínio | depende do proprietário ou do condomínio |
| Precisa de obra | não | hidráulica e telhado | elétrica e telhado |
| Precisa de aprovação da distribuidora | não | não | sim (projeto de geração distribuída) |
| Área de telhado (família de referência) | 0 | 2,0 m² | 5,2 m² |
| Energia útil por m² de telhado | – | 77,7 ÷ 2,0 = **38,9 kWh/m²·mês** (evitada) | 111,4 ÷ 5,2 = **21,4 kWh/m²·mês** (compensada) |
| Depende do consumo total da casa | não | não | sim (créditos só abatem acima da disponibilidade) |
| Efeito com Tarifa Social e consumo perto de 80 kWh | pequeno ou nulo na conta; poupa água | idem | idem, e créditos podem sobrar |

O coletor térmico aproveita cerca de 50% da radiação na forma de calor. O módulo fotovoltaico aproveita cerca de 20% na forma de eletricidade. Com pouco telhado, o aquecedor solar entrega quase o dobro de energia útil por metro quadrado.

### Impactos ambientais
- **Emissões:** a matriz elétrica brasileira é majoritariamente renovável, então o CO₂ evitado é pequeno, de 15 a 52 kg por ano por família. Em anos secos, com mais termelétricas, o fator pode passar de 0,09 kgCO₂/kWh e esse ganho mais que dobra.
- **Pico de demanda:** é o ganho sistêmico mais relevante. Cada chuveiro ligado demanda cerca de 5,5 kW entre 18h e 21h, quando o sistema recorre a usinas despacháveis, muitas delas termelétricas. **A** e **B** reduzem a energia retirada da rede nesse horário. **C** gera ao meio-dia e não reduz o pico noturno, apenas compensa a energia na conta.
- **Água:** **A** poupa cerca de 1.512 L por mês (18 mil litros por ano), um ganho importante em São Paulo, que já teve crises hídricas.
- **Ciclo de vida:** coletores, reservatórios e módulos usam metais, vidro e polímeros. Equipamentos com etiqueta Inmetro duram de 15 a 25 anos. No fim da vida útil devem ir para reciclagem; os módulos fotovoltaicos têm logística reversa em expansão.

### Recomendação adotada pelo assistente

1. **Todas as famílias:** banho consciente (A), com efeito imediato e custo próximo de zero.
2. **Proprietário com telhado que quer reduzir o gasto com banho e o pico de consumo:** aquecedor solar junto com o banho consciente (A+B). Ocupa pouco telhado e não depende da distribuidora.
3. **Proprietário com telhado e conta alta, que quer abater a conta inteira:** fotovoltaica (C), que tem o melhor retorno financeiro isolado hoje.
4. **Família com Tarifa Social e consumo perto de 80 kWh por mês:** só A. A economia em reais é pequena ou zero, mas a família economiza água e ganha folga para não passar da franquia.

---

## 7. Limitações

- Os resultados são **estimativas**, não garantias. A economia real depende do chuveiro, da pressão da água, dos hábitos e da tarifa de cada família.
- As temperaturas de água fria e de banho são médias anuais, iguais em todos os cenários. Na prática, a água fria é mais quente no verão e mais fria no inverno.
- O cálculo não considera reajuste de tarifa, juros ou financiamento, nem a perda de rendimento dos equipamentos com o tempo (cerca de 0,5% ao ano nos módulos).
- A tarifa não inclui bandeiras tarifárias nem a contribuição de iluminação pública. A troca do inversor, entre 10 e 15 anos, não entra no horizonte de 10 anos.
- O dimensionamento do aquecedor solar é simplificado: volume proporcional à água quente usada, fração solar média de 70% e custo linear no volume. O projeto real segue a NBR 15569 e depende de orientação, sombreamento e orçamento local.
- A irradiação de 4,5 kWh/m²·dia é uma estimativa para a cidade de São Paulo. O valor exato do ponto deve ser consultado no SunData/CRESESB no projeto de cada casa.
- Na fotovoltaica, o crédito de 85% da tarifa é uma hipótese simplificada. A regra de transição da Lei 14.300/2022 e o consumo total da casa podem reduzir o valor aproveitado, e a taxa mínima de disponibilidade continua sendo cobrada.
- As regras da Tarifa Social podem mudar. É preciso confirmar com a distribuidora ou no CRAS.
