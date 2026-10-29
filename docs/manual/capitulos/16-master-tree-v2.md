# A Master Tree v2

Com o `GameState` em mãos, a árvore mestre pode ser reescrita de forma limpa: **um ramo por fase do jogo**, em ordem de prioridade, sem números mágicos e sem comandos "esquecidos". Este capítulo apresenta a estrutura, justifica as escolhas de nós e acompanha a árvore em ação ao longo de uma sequência de fases.

## A estrutura

A raiz da `MainTreeEL` é um `ReactiveFallback` com doze filhos, mostrados na {{fig:arvore_mestre_v2}}. Cada ramo (exceto o último) é uma `ReactiveSequence` composta de uma **guarda** (a condição `phase == ...`) e de uma **subárvore** com o comportamento daquela fase.

![A Master Tree v2: um ramo por fase, em ordem de prioridade](figuras/arvore_mestre_v2.png)

| # | Ramo | Guarda | Comportamento |
|---|---|---|---|
| 1 | `SafetyGuard` | os dados **não** estão frescos (`Inverter(IsDataFresh)`) | `DegradedModeTree`: parar |
| 2 | `HaltBranch` | `phase == HALT` | `HaltSubTree` |
| 3 | `TimeoutBranch` | `phase == TIMEOUT` | `TimeoutTree` |
| 4 | `StopBranch` | `phase == STOP` | `StopSubTree` |
| 5 | `BallPlacementBranch` | `phase == BALL_PLACEMENT` | nosso: `BallPlacementOurTree`; deles: `BallPlacementTheirTree` |
| 6 | `PrepareKickoffBranch` | `phase == PREPARE_KICKOFF` | nosso/deles |
| 7 | `KickoffBranch` | `phase == KICKOFF` | nosso: executa; deles: espera |
| 8 | `PreparePenaltyBranch` | `phase == PREPARE_PENALTY` | nosso/deles |
| 9 | `PenaltyBranch` | `phase == PENALTY` | nosso: executa; deles: defende |
| 10 | `FreeKickBranch` | `phase == FREE_KICK` | nosso/deles (inclui lateral, escanteio e tiro de meta) |
| 11 | `RunBranch` | `phase == RUN` | `NormalPlayTree` |
| 12 | `Halt (unknown_phase)` | — | parar |

A ordem não é arbitrária. Os ramos 1 a 4 formam o **bloco de segurança**: se qualquer um se aplica, nada abaixo executa. Os ramos 5 a 10 tratam os **reinícios**, e o ramo 11 é o jogo propriamente dito. O ramo 12 é a **rede de segurança**: se nenhuma fase conhecida casa, o robô **pára** — o oposto do comportamento atual, em que o "default" é jogar.

## "Nosso" ou "deles": o padrão do favorecido

Quase todo reinício tem dois lados: o time que **bate** e o time que **defende**. A árvore trata essa dicotomia com um padrão repetido em cada ramo de reinício:

```xml
<ReactiveSequence name="FreeKickBranch">
  <CheckGameState phase="FREE_KICK"/>
  <ReactiveFallback>
    <ReactiveSequence>
      <WeAreFavored/>
      <SubTree ID="FreeKickOurTree" _autoremap="true"/>
    </ReactiveSequence>
    <SubTree ID="FreeKickTheirTree" _autoremap="true"/>
  </ReactiveFallback>
</ReactiveSequence>
```

Lê-se: *"se a fase é FREE_KICK: se somos o favorecido, execute a árvore de quem bate; senão, a de quem defende."* A cor do time **não aparece** em nenhum ramo: ela já foi resolvida pelo `referee_state_node` em `we_favored`. Este é o fim da série de condições `is_yellow ∧ cmd == 4 ∨ ¬is_yellow ∧ cmd == 5` do mestre atual.

Um detalhe elegante: se a subárvore "nossa" **falhar** (por exemplo, um posicionamento de bola que estoura o prazo), a `ReactiveFallback` cai para a subárvore "deles", que é um comportamento seguro de retirada.

## Por que as guardas são `ReactiveSequence`

Este é o ponto de projeto mais sutil, e vale um exemplo. Suponha que a guarda do ramo `KickoffBranch` fosse uma `Sequence` comum. Durante um kick-off, o filho `KickoffExecuteOurTree` está em andamento (RUNNING). Quando o jogo passa para `RUN`, o `ReactiveFallback` raiz tenta primeiro os ramos de cima; chega ao `KickoffBranch` e o ticka. Mas a `Sequence` **lembra** que estava no segundo filho e retoma diretamente nele — **sem reavaliar** a guarda `phase == KICKOFF`, que agora seria falsa. O robô continuaria executando o kick-off por um tick a mais do que deveria.

Com uma `ReactiveSequence`, a guarda é reavaliada a cada tick; no instante em que a fase muda, ela falha, a subárvore é interrompida (`halt`) e o fallback passa ao ramo seguinte. É por isso que **toda guarda de ramo** é reativa, sem exceção.

!!! note "O mestre atual já escapa disso, por outro motivo"
    No mestre atual, os ramos usam `Sequence` comum, mas funcionam porque o `ReactiveFallback` raiz reavalia os ramos de *maior prioridade* a cada tick (o HALT é sempre reavaliado). O que **não** é reavaliado é a guarda do **próprio** ramo em andamento. Para a arquitetura de jogo completo, com guardas por fase, a regra "guarda reativa" elimina essa classe de problemas.

## A árvore ao longo de uma sequência de fases

A {{fig:preempcao_timeline}} acompanha o ramo ativo da Master em uma sequência típica: o jogo corre, o árbitro manda parar, prepara um kick-off nosso, autoriza a jogada e o jogo volta a correr.

![A fase do jogo (em cima) e o ramo ativo da Master (embaixo) ao longo de uma sequência de comandos](figuras/preempcao_timeline.png)

O que acontece, em cada transição:

1. **`RUN → STOP`.** O atacante está com um `GoToPoint` em andamento. No tick seguinte à mudança de fase, o ramo `StopBranch` (prioridade 4) casa antes do `RunBranch` (11): `NormalPlayTree` é interrompida, o `GoToPoint` recebe `onHalted` (que publica "fique onde está") e a `StopTree` assume, limitando a velocidade e afastando o robô da bola.
2. **`STOP → PREPARE_KICKOFF`.** O ramo 6 casa. Como `we_favored` é verdadeiro, vale `PrepareKickoffOurTree`: o cobrador vai para o círculo central; os outros, para a própria metade.
3. **`PREPARE_KICKOFF → KICKOFF`** (chegou o `NORMAL_START`). O `referee_state_node` lembrou que era kick-off nosso, então a fase é `KICKOFF` com `we_favored`. O cobrador executa `KickOnce`.
4. **`KICKOFF → RUN`** (a bola se moveu). A fase vira `RUN`, o ramo 11 assume, e os papéis normais voltam.

Em nenhum momento a árvore precisou "saber" o histórico: o `GameState` carrega todo o contexto necessário.

## Efeitos colaterais e *starvation*

Dois cuidados acompanham o uso de `ReactiveFallback` na raiz:

- **Reticks de folhas síncronas.** Como os ramos de cima são reavaliados a cada tick, as folhas síncronas que eles contêm são reexecutadas 60 vezes por segundo. A ação `Halt`, por exemplo, reenvia o override de parada a cada tick — o que é **necessário** (o override expira em 200 ms) e inofensivo. Folhas com efeito colateral custoso não devem ficar em ramos reativos de alta prioridade.
- ***Starvation***. Um ramo de alta prioridade que devolve SUCCESS **sempre** impede que os de baixo executem. É o comportamento desejado para `HaltBranch` (só casa em HALT), mas seria um erro em um ramo cuja guarda fosse sempre verdadeira.

## Três trajetórias de verificação

Para checar o projeto, é útil "executar" mentalmente a árvore em trajetórias completas:

**Trajetória 1 — partida começa e termina em parada.** Sem GC ainda: `IsDataFresh` falha (o `GameState` é `stale` ou inexistente) → `DegradedModeTree` → robôs parados. Chega o primeiro `STOP`: ramo 4. `PREPARE_KICKOFF` nosso → cobrador no círculo. `NORMAL_START` → `KICKOFF` → o cobrador toca a bola. A bola se move → `RUN` → ataque. Chega um `STOP` com o atacante em movimento → `StopTree`. Chega um `HALT` → `HaltTree`: velocidade zero.

**Trajetória 2 — perda de posse e troca de papéis.** Em `RUN`, o adversário rouba a bola. O atribuidor publica novos papéis (`epoch + 1`): o atacante vira defensor. No tick seguinte, `HasRole(attacker)` falha no ramo do atacante, que é interrompido; `HasRole(defender)` casa e a `DefenderTree` assume com `ShadowBall`/`MarkOpponent`. O novo `GoToPoint` ou `ShadowBall` publica um alvo no mesmo tick.

**Trajetória 3 — dado velho com uma ação em andamento.** O atacante está com `GoToPoint` em andamento; a visão cai. `IsDataFresh` passa a falhar (a idade da pose supera 150 ms): o ramo 1 assume e o robô pára. Se a própria árvore estiver travada, o **SafetyGate** do controlador zera os comandos por *watchdog* em até 500 ms. Quando os dados voltam, o ramo 1 deixa de casar, e os ramos de baixo recomeçam (o `onStart` de cada folha recalcula o alvo).

As três trajetórias são sustentadas pela arquitetura; a primeira e a segunda dependem apenas de o `GameState` estar correto, e a terceira, do carimbo de tempo nos dados (Capítulo 20).
