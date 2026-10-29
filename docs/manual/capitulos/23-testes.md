# Testes e validação

Uma árvore "carregar sem erro" não significa que ela funciona. Este capítulo propõe uma estratégia de testes em camadas — das verificações mais baratas (um arquivo XML) às mais caras (uma partida inteira) — e a lista de cenários que cobrem as regras do regulamento.

## A pirâmide de testes

A {{fig:piramide_testes}} organiza os tipos de teste: muitos testes pequenos e rápidos na base, poucos testes grandes e lentos no topo.

![A pirâmide de testes proposta](figuras/piramide_testes.png)

| Camada | Ferramenta | O que prova |
|---|---|---|
| **Validação estática dos XMLs** | script que carrega todos os XML numa `BehaviorTreeFactory` com os nós registrados | IDs únicos; nós registrados; portas existentes; **portas de entrada obrigatórias sem valor** (o problema do `KeepDistance`); subárvores resolvíveis |
| **Unitário** | gtest + `BehaviorTreeFactory` (sem robôs) | retornos de cada folha (SUCCESS/FAILURE/RUNNING), `onHalted` idempotente, dados ausentes |
| **Blackboard** | gtest | `refresh()`, idades, `side_sign`, chaves ausentes |
| **Integração ROS 2** | `launch_testing` | HALT zera os comandos em tempo; cancelamento; QoS; SafetyGate |
| **Master Tree** | gtest com a árvore real e nós falsos | o ramo ativo para cada fase; preempção entre fases |
| **Papéis** | gtest com `GameData` sintético | exclusividade, histerese, época, cobrador travado, degradação |
| **Conformidade regulamentar** | cenários no grSim com o Game Controller real | cada regra do regulamento (tabela abaixo) |
| **Partida completa** | `./run_match.sh` | todas as transições, sem faltas por causa do software |
| **Regressão** | *replay* de *rosbags* | mesma entrada → mesmos ramos ativos |
| **Robustez** | falhas injetadas | comportamento seguro com a visão ou o GC caídos |

## Validar primeiro: o validador estático

O custo-benefício mais alto está na base. Um script de ~100 linhas que carregue os XMLs de `behavior_trees/` e valide as regras acima teria detectado, de uma só vez: o `KeepDistance` sem portas (e o `AimAt`), os IDs duplicados, e qualquer nó novo esquecido no registro. Ele deve rodar a cada mudança (e, idealmente, antes de cada *commit*). O resultado esperado, depois das correções do Capítulo 21, é **zero avisos**.

## Teste de semântica da biblioteca

Boa parte da segurança do projeto depende de **semânticas** da BehaviorTree.CPP: que `ReactiveSequence` halta os filhos seguintes, que `RetryUntilSuccessful(-1)` com filho síncrono faz uma tentativa por tick, que `Parallel` interrompe os filhos ao decidir, que `getInput` falha com porta sem valor. Como parte dessas semânticas foi confirmada na série 4.6 e a instalada é a 4.10, um conjunto de pequenos testes ("harness") que reproduza cada caso das figuras do Capítulo 4 **na versão do container** elimina a dúvida e protege contra mudanças em atualizações.

## Cenários de conformidade

Cada cenário descreve uma situação de jogo, a entrada, o ramo esperado e o que se mede:

| ID | Situação | Entrada | Esperado |
|---|---|---|---|
| SC-01 | Partida inicia sem nenhum comando do árbitro | só dados de visão | robôs **parados** (`DegradedModeTree`) |
| SC-02 | HALT com robôs a 1 m/s | `HALT` | velocidade zero em ≤ 300 ms |
| SC-03 | STOP durante um ataque | `STOP` | v < 0,75 m/s; ≥ 0,5 m da bola; sem chute em curso |
| SC-04 | STOP seguido de FORCE_START | `STOP`, `FORCE_START` | jogo retomado com os papéis |
| SC-05 | Kick-off nosso | `PREPARE_KICKOFF` → `NORMAL_START` | todos na própria metade; só o cobrador no círculo e toca a bola. **Repetir para amarelo e azul** |
| SC-06 | Kick-off do adversário | idem | ninguém no círculo; ≥ 0,5 m da bola |
| SC-07 | Free kick nosso, bola perto da área adversária | `DIRECT_FREE` | cobra em ≤ 10 s; apoio ≥ 0,2 m da área |
| SC-08 | Free kick do adversário | `DIRECT_FREE` | ≥ 0,5 m da bola |
| SC-09 | Pênalti nosso | `PREPARE_PENALTY` → `NORMAL_START` | demais ≥ 1 m atrás da bola; bola só rumo ao gol adversário |
| SC-10 | Pênalti do adversário | idem | goleiro na linha de gol; demais ≥ 1 m atrás |
| SC-11 | Ball placement do adversário | `BALL_PLACEMENT` | ≥ 0,5 m do corredor; v < 0,75 |
| SC-12 | Ball placement nosso | idem | bola a ≤ 0,15 m do alvo em ≤ 30 s |
| SC-13 | TIMEOUT | `TIMEOUT_*` | robôs parados |
| SC-14 | STOP chega com um `GoToPoint` em andamento | `STOP` | o objetivo antigo **não** persiste |
| SC-15 | Troca de ataque para defesa | perda de posse | defensor assume em ≤ 1 tick |
| SC-16 | Troca de papéis com ação em andamento | RA troca papéis | o ramo antigo recebe `halt` |
| SC-17 | Goleiro ausente | `goalkeeper_id` inativo | o defensor **não** entra na área |
| SC-18 | Dois robôs disputando a mesma função | custos iguais | histerese e exclusividade |
| SC-19 | Destino inacessível | alvo dentro de obstáculo | rota vazia ⇒ o robô pára |
| SC-20 | Perda de visão por 1 s | corte do bridge | robôs param em ≤ 500 ms |
| SC-21 | GC repetido/fora de ordem | mensagens duplicadas e reordenadas | estado correto; antigo não sobrescreve |
| SC-22 | Troca de lado no 2º tempo | `blue_team_on_positive_half` inverte | defendem o gol certo |
| SC-23 | Cartão amarelo | `max_allowed_bots` 3 → 2 | degradação para 2 robôs |
| SC-24 | Muitos chutes | 10+ chutes | `kick_speed ≤ 3,0` em 100% |
| SC-25 | Bola na área própria | bola parada > 8 s | goleiro limpa antes de 10 s |
| SC-26 | Árvore travada | `SIGSTOP` no `strategy_node` | velocidade zero em ≤ 500 ms (SafetyGate) |

## Critérios de aceitação globais

Os limiares abaixo são **propostas** a calibrar em simulação; não são exigências do regulamento (que dá, por exemplo, 2 s para frear o HALT):

1. **HALT**: velocidade zero em `/robot_commands` em até **300 ms**.
2. **STOP**: ≥ 99% das amostras com |v| ≤ 0,75 m/s; distância à bola ≥ 0,5 m em até 2 s.
3. **Chute**: `kick_speed ≤ 3,0 m/s` em **100%** dos comandos gravados.
4. **Áreas**: nenhum robô, exceto o goleiro, com o centro dentro da própria área (mais 90 mm); nenhum a < 0,2 m da área adversária em STOP/free kick.
5. **Ramos**: em cada fase, o ramo ativo corresponde ao esperado (tópico `/strategy/active_branch`).
6. **Dados velhos**: robô parado em ≤ 500 ms, **mesmo com a árvore travada**.
7. **Papéis**: troca de papel em ≤ 1 tick; nunca dois robôs com o mesmo papel exclusivo por mais de um ciclo do atribuidor.
8. **Partida completa**: duas partidas simuladas de 5 min cada, sem eventos de falta atribuíveis ao software.

Alguns itens dependem de laboratório (latência real do rádio, atrito do carpete, visão real); os 1 a 7 e o 8 podem ser comprovados em simulação.

## Observabilidade para os testes

Dois instrumentos tornam os testes possíveis e a depuração rápida:

- **Um tópico de ramo ativo.** Um nó de log escreve, a cada **transição** de ramo da Master, uma linha com a fase, o ramo e o motivo (a guarda que mudou), e o publica em `/strategy/active_branch`. Responde "que ramo estava ativo, por que e por que foi interrompido".
- **Gravação de *rosbags***. Gravando `…/referee_messages`, `/game_data`, `/field_geometry` e `/role_assignment`, é possível **reexecutar** a árvore com a mesma entrada e comparar a sequência de ramos com uma sequência "dourada" — o teste de regressão mais valioso.

## Definição de pronto

Uma subárvore ou folha só está **pronta** quando: o contrato está documentado; a implementação está integrada e registrada; o XML passa no validador estático; há teste de comportamento; há teste de `halt` e de falha de dados; a interface foi revisada; existe evidência de execução (log ou *bag*); e os catálogos deste manual foram atualizados.
