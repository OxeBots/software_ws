# Plano de implementação

Este capítulo transforma a arquitetura em trabalho: as frentes em que a equipe pode se dividir, a ordem das dependências, o que é obrigatório para jogar (o MVP) e um cronograma de **quatro semanas**. O backlog detalhado (49 tarefas, com contratos e critérios de aceite) acompanha o manual em `docs/manual/anexos/backlog.csv`.

## Frentes de trabalho

Como não há uma lista de pessoas definida, o plano fala em **frentes** (perfis de trabalho). Cada uma pode ser assumida por uma ou mais pessoas:

| Frente | Escopo | Tarefas (prefixo) |
|---|---|---|
| **GC** — Game Controller | `GameState`, `referee_state_node`, lançamento | G01–G06 |
| **MASTER** — Arquitetura | `MainTreeEL`, condições novas, observabilidade, limpeza | A01–A06 |
| **DADOS** — Blackboard | `GameData` com carimbo, `refresh()`, lado, fim das coordenadas literais | D01–D04 |
| **MOV** — Movimento | SafetyGate, `GoToPoint`, `KeepDistance`, `PrecisionKick`, D\* | M01–M06 |
| **ESTRAT** — Estratégia | Stop, reinícios, placement, ataque, defesa | E01–E10 |
| **GK** — Goleiro | goleiro, pênalti | K01–K02 |
| **PAPEIS** — Papéis | atribuidor ampliado, degradação | P01–P04 |
| **TESTE** — Testes | validador, *harness*, *replay*, cenários, partidas | T01–T09 |
| **DOC** — Documentação | READMEs, catálogos | X01–X02 |

## O MVP: o que é obrigatório para jogar

Distinguem-se três níveis de prioridade:

- **P0 — segurança e legalidade**: sem isso, o time comete faltas ou perde o controle. Inclui o `GameState` correto, os ramos de HALT/STOP/TIMEOUT, o SafetyGate (velocidade, watchdog, chute), o tratamento de lado e a validação mínima.
- **P1 — MVP jogável**: a Master integrada, ataque e defesa por papéis, o goleiro, os reinícios obrigatórios e a bateria de testes de integração.
- **P2 — evolução**: ball placement próprio, passe coordenado, uso do *team client* do GC, ajuste fino de histereses.

Dos reinícios, **kick-off, free kick e pênalti são obrigatórios**; o posicionamento próprio da bola é opcional por regra (a categoria permite o *opt-out*).

## Dependências e o caminho crítico

O grafo abaixo mostra a precedência entre as tarefas mais importantes ({{fig:grafo_dependencias}}):

![Dependências entre as tarefas principais (laranja: contratos; verde: marcos)](figuras/grafo_dependencias.png)

Alguns pontos orientam a organização do trabalho:

- **O que destrava o resto**: o contrato do `GameState` (G01), o esquema de blackboard e lado (D03) e o SafetyGate (M01). São as primeiras tarefas.
- **Componentes compartilhados**: `GoToPoint` (M03), `KickOnce`/`RestartKickerTree` (E08), `ComputeLegalSlot` e `HasRole`. Cada um tem uma frente dona; as demais usam **dublês** (publicar um `GameState` falso com `ros2 topic pub`, injetar uma blackboard em um teste) para não esperar.
- **Contratos a fechar antes de codar** (semana 1): `GameState.msg`, `RoleAssignment` ampliada, portas de `ComputeLegalSlot`, `KickOnce` e `CheckGameState`, o esquema de blackboard (Capítulo 20), o campo `max_speed` do `RobotGoal` e o tópico `/robot_motion_limit`.
- **Conflitos de arquivo**: `strategy_node.cpp` é tocado por várias tarefas (A01, A05, D03, P02): um dono (MASTER) e *pull requests* pequenos. As mudanças de mensagens (G01, D01, P02) devem entrar em **um único PR de interfaces** no início da semana 1, porque obrigam a recompilar o `oxebots_interfaces` e todos que dependem dele.
- **Caminho crítico**: G01 → G02 → condições novas (A01) → StopTree (E01) → Master v2 esqueleto (A02) → Kick-off (E05) → Pênalti/Free kick (E06, E07) → Master completa (A06) → Conformidade (T07) → Partidas (T09).

## Cronograma de quatro semanas

![Cronograma indicativo, por semana e por frente](figuras/gantt_4_semanas.png)

**Semana 1 — Contratos e base segura.** Congelar as interfaces e entregar o núcleo de segurança.
- `GameState.msg` e `referee_state_node` com dedupe, contexto de reinício, lado e `stale` (G01–G05).
- `GameData` com carimbo, esquema da blackboard e `side_sign` (D01, D03).
- SafetyGate e correções do movimento (M01–M04).
- Master v2 com SafetyGuard, HALT, TIMEOUT e STOP funcionando (A01, A02, E01, E02).
- Validador estático, *harness* de semântica e captura de um log real do GC (T01–T03).
- **Marco**: o robô pára com HALT, obedece ao STOP e entra em modo seguro sem dados.

**Semana 2 — Núcleo de jogo.** Reinícios básicos, papéis e goleiro.
- Kick-off, free kick unificado e `BallPlacementTheirTree` (E03, E05, E07, E08).
- Atacante e defensor reorganizados (E09, E10), goleiro por `HasRole` (K01), papéis conscientes da fase (P01, P02).
- Limpeza dos IDs duplicados, observabilidade, atualização de READMEs (A03–A05, D02, X01).
- **Marco**: kick-off e free kick corretos para os dois lados; ataque e defesa por papéis.

**Semana 3 — Integração e regras.** Fechar o regulamento e a robustez.
- Pênalti completo, goleiro do pênalti (E06, K02), degradação de papéis (P03).
- Montagem final da Master (A06) e testes de integração e de ramos (T05, T06).
- (Se houver capacidade) ball placement próprio (E04, M05).
- **Marco**: todas as fases implementadas; cenários SC-01 a SC-26 executáveis.

**Semana 4 — Ponta a ponta e estabilização.**
- Checklist de conformidade, testes de robustez, partidas completas e correções (T07–T09).
- Ajuste fino de histereses (P04), manutenção dos catálogos (X02).
- **Marco**: os critérios de aceitação globais do Capítulo 23 atendidos.

!!! warning "Sobre o escopo"
    Este cronograma pressupõe **pelo menos cinco pessoas** em paralelo, uma por frente principal. Com menos de quatro, o escopo é inviável em quatro semanas. A ordem de corte recomendada, sem sacrificar a segurança nem a legalidade, é: ball placement próprio (E04, M05), *team client* (G06), ajuste fino de papéis (P04) e, por último, a redução dos testes P1 aos cenários P0.

## Riscos principais

| Risco | Efeito | Mitigação |
|---|---|---|
| Comando em `Run` desconhecido (Capítulo 15) | fase `RUN` detectada errado | capturar um log real do GC na semana 1 e manter o cálculo local parametrizável |
| Mudança de mensagens | recompilar todo o stack; *bags* antigos incompatíveis | um único PR de interfaces; manter campos antigos |
| Semântica 4.6 × versão instalada 4.10 | segurança baseada em comportamento não confirmado | *harness* de semântica (T01) |
| Submódulos em *branches* de feature | build não reproduzível | fixar tags antes da competição (D02) |
| Árvore ou controlador travado | robô se move sem comando | SafetyGate (M01) |
| Visão real com ruído e confiança não calibrada | decisões instáveis | calibrar `min_ball_confidence`; usar o Kalman também para a defesa |
| Escopo maior que a equipe | cronograma estoura | ordem de corte acima |

## Como começar

1. Escolha uma tarefa da sua frente em `backlog.csv` e leia o contrato nos Capítulos 15 a 21.
2. Combine, com as frentes vizinhas, os contratos de interface da semana 1.
3. Implemente com *dublês* para não depender de ninguém; escreva o teste junto.
4. Valide o XML com o validador estático; rode o cenário correspondente (Capítulo 23).
5. Atualize este manual (o catálogo do Apêndice B) no mesmo *pull request*.
