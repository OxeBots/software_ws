# Reinícios: kick-off, pênalti, free kick e ball placement

Os reinícios são onde as regras mais pesam e onde uma pequena imprecisão vira falta. Este capítulo detalha as subárvores dos ramos 5 a 10 da Master: para cada situação, os dois papéis (quem bate e quem defende), as posições exigidas e como a árvore as obtém.

## Posições legais sem coordenadas literais

O problema central dos reinícios atuais é o das coordenadas fixas (Capítulo 13). A solução proposta é uma folha que **calcula** a posição de cada robô a partir da geometria do campo, do lado e da bola: `ComputeLegalSlot`.

A folha recebe o nome de um **slot** (uma "vaga" tática) e devolve a posição (`slot_x`, `slot_y`) e a orientação (`slot_w`) para ele. Todos os cálculos usam `own_goal_x` e `side_sign` da blackboard, de modo que **o mesmo slot vale para os dois lados do campo** ({{fig:slots_legais}}).

![Os mesmos slots para um time que defende a esquerda (acima) e a direita (abaixo)](figuras/slots_legais.png)

| Slot | Onde fica | Regra que cumpre |
|---|---|---|
| `kickoff_kicker` | dentro do círculo central, atrás da bola, voltado ao gol adversário | só o cobrador pode estar no círculo |
| `kickoff_def` | na **própria metade**, fora do círculo (≥ 500 mm do centro, além da margem), alinhado conforme o `index` do robô | todos na própria metade, fora do círculo |
| `penalty_kicker` | atrás da bola, na linha bola–gol adversário | atacante se aproxima sem tocar |
| `penalty_behind` | **≥ 1 m atrás da bola** (com margem), fora da área de defesa | demais robôs afastados |
| `freekick_support` | posição de apoio longe da bola e **≥ 0,2 m da área adversária** | proximidade da área |
| `wall` | linha de defesa entre a bola e o gol, **≥ 0,5 m da bola** | distância no free kick adversário |
| `retreat` | ponto a 650 mm da bola, na reta bola→robô | distância no STOP |

Todos os slots passam por um *filtro final*: se o ponto calculado cai dentro de uma área proibida (a área de defesa para quem não é goleiro, a adversária para todos), é deslocado para o ponto válido mais próximo, com uma margem configurável (`slot_margin_mm`, padrão 150).

## Kick-off

### Preparação (`PREPARE_KICKOFF`)

As duas versões da preparação são parecidas: o goleiro fica na meta; os outros se posicionam na própria metade, fora do círculo central. A diferença é que, **no nosso kick-off**, um robô — o cobrador, indicado pelo atribuidor de papéis (`kicker_id`) — fica **dentro do círculo**, atrás da bola.

![PrepareKickoffOurTree: goleiro, cobrador e demais robôs](figuras/arvore_prepare_kickoff.png)

A árvore é um `ReactiveFallback` de três ramos por papel ({{fig:arvore_prepare_kickoff}}): goleiro (`GoalkeeperTree`), cobrador (`ComputeLegalSlot` com `kickoff_kicker` e `GoToPoint` olhando para a bola) e o resto (`kickoff_def`). A versão `PrepareKickoffTheirTree` omite o cobrador. Ela também é usada **durante o kick-off do adversário** (fase `KICKOFF` sem `we_favored`): todos continuam na própria metade, fora do círculo, sem tocar a bola.

### Execução (`KICKOFF`)

Quando o `NORMAL_START` chega, a fase vira `KICKOFF` e, se somos o favorecido, vale `KickoffExecuteOurTree`: o goleiro continua; o cobrador executa a subárvore `RestartKickerTree`; os outros **permanecem onde estão** (`HoldPosition`) até a bola entrar em jogo, para não violar a regra de que só o cobrador toca na bola.

## O cobrador: RestartKickerTree e KickOnce

Os três reinícios em que o nosso time bate — kick-off, pênalti e free kick — compartilham a **mesma sequência de cobrança**, extraída como uma subárvore reutilizável, `RestartKickerTree` ({{fig:arvore_restart_kicker}}):

![RestartKickerTree: ir ao pré-chute, olhar o alvo e chutar uma vez](figuras/arvore_restart_kicker.png)

1. **`UpdateBallPosition`** calcula o ponto de pré-chute (400 mm atrás da bola, na reta bola→alvo), para o alvo configurado nas portas `target_x`/`target_y`.
2. **`GoToPoint`** leva o robô até lá, olhando para o alvo, com `ball_contact_threshold_mm=150` (se a bola for tocada no caminho, falha e recomeça).
3. **`KickOnce`** (nova) executa o chute: pede `MODE_KICK` com a velocidade limitada a 3 m/s, devolve SUCCESS quando a bola **se movimentou pelo menos 50 mm** e FAILURE se passar o prazo de 10 s do regulamento.

A diferença em relação a `KickBall` é que `KickOnce` confirma o **resultado** (a bola se moveu), não só a execução do chute, e carrega o prazo do regulamento.

## Pênalti

O pênalti é o reinício com mais restrições e, por isso, tem quatro subárvores.

### Nosso pênalti

- **`PreparePenaltyOurTree`**: o goleiro na meta; o cobrador no slot `penalty_kicker` (atrás da bola, **sem tocá-la**, olhando para o gol); os demais no slot `penalty_behind` (≥ 1 m atrás da bola).
- **`PenaltyExecuteOurTree`** (`phase == PENALTY`, `we_favored`): o cobrador executa `RestartKickerTree` apontando para o gol adversário; os demais **permanecem parados**. A bola só pode se mover em direção ao gol adversário, o que a cobrança direta ao gol respeita.

### Pênalti do adversário

- **`PreparePenaltyTheirTree`**: o goleiro executa `PenaltyKeeperLine` (vai à **linha de gol e a toca**, 90 mm — o raio do robô — para dentro do campo); os demais vão ao slot `penalty_behind`.
- **`PenaltyDefendTheirTree`** ({{fig:arvore_penalty_defesa}}): enquanto a bola **não** entrou em jogo, o goleiro **mantém a linha**; assim que `WaitBallInPlay` indica que a bola se moveu (ou passaram 10 s), o goleiro volta ao comportamento normal (`GoalkeeperTree`) — o regulamento libera o goleiro nesse momento. Os outros robôs seguem parados, ≥ 1 m atrás da bola.

![PenaltyDefendTheirTree: linha de gol até a bola entrar em jogo, depois goleiro normal](figuras/arvore_penalty_defesa.png)

!!! note "Uma ligação importante com o goleiro"
    No pênalti defensivo, o goleiro **não** deve sair da linha para buscar a bola mesmo que ela entre "na área" — algo que o goleiro atual (Capítulo 10) faria. Por isso, as folhas `PenaltyKeeperLine` e `WaitBallInPlay` controlam o goleiro de modo explícito durante essa fase.

## Free kick

Falta, lateral, escanteio e tiro de meta chegam todos como `DIRECT_FREE`, e a bola já está na posição designada. A árvore as trata uniformemente ({{fig:arvore_freekick}}); ela **substitui** `free_kick.xml`, `corner_kick.xml`, `throw_in.xml` e `kick_in.xml`, que dependiam de flags nunca escritas.

![FreeKickOurTree: goleiro, cobrador e apoio](figuras/arvore_freekick.png)

- **Goleiro**: comportamento normal.
- **Cobrador**: `RestartKickerTree`, com o alvo escolhido conforme a situação (por padrão, o gol adversário).
- **Apoio**: vai ao slot `freekick_support`, a ≥ 0,2 m da área adversária.

No free kick **do adversário** (`FreeKickTheirTree`), todos os robôs de linha vão ao slot `wall` (≥ 0,5 m da bola), formando uma barreira entre a bola e o gol, e o goleiro defende normalmente. A distância de 0,5 m deve ser mantida até a bola entrar em jogo; a folha `WaitBallInPlay` sinaliza esse momento.

## Ball placement

O posicionamento da bola é uma tarefa de duas faces.

### Do adversário (ou quando desistimos)

Quando o outro time posiciona a bola, nossos robôs só precisam **não atrapalhar**: ficar a ≥ 0,5 m do segmento entre a bola e o alvo (o "estádio" da {{fig:geometria_stop_placement}}), com velocidade abaixo de 0,75 m/s. A `BallPlacementTheirTree` ({{fig:arvore_ballplacement_deles}}) usa `AvoidPlacementCorridor`: se o robô está dentro do corredor, move-se para fora; senão, fica parado.

![BallPlacementTheirTree](figuras/arvore_ballplacement_deles.png)

### Do nosso time

Quando é a nossa vez de posicionar, `BallPlacementOurTree` ({{fig:arvore_ballplacement_nosso}}) designa um robô (o `kicker`) para a tarefa: `ComputeLegalSlot`/`ComputePlacementApproach` calcula o ponto de captura atrás da bola (do lado oposto ao alvo), `GoToPoint` leva o robô até lá, e `PlaceBall` empurra a bola até a posição designada em até 30 s, devolvendo SUCCESS quando a bola está a ≤ 0,15 m do alvo e parada, e FAILURE no estouro do prazo (e, então, o GC passa o posicionamento ao adversário). Os outros robôs obedecem à `StopSubTree`.

![BallPlacementOurTree](figuras/arvore_ballplacement_nosso.png)

!!! tip "Opção de escopo"
    Na SSL-EL, um time pode **optar por não posicionar a bola** pelo resto do jogo, avisando o árbitro. Implementar o posicionamento próprio é a parte mais trabalhosa e de menor retorno imediato. A recomendação é tratá-lo como **pós-MVP** e, no MVP, combinar com o árbitro o *opt-out*, mantendo apenas o comportamento de não interferir (`BallPlacementTheirTree`) para as duas situações.

## A bola em jogo

Tanto `KickoffExecute`, `PenaltyDefend` quanto `FreeKick` precisam saber **quando a bola entrou em jogo**. A folha `WaitBallInPlay` encapsula a regra do regulamento (§5.4): verdadeira quando a bola se moveu pelo menos 50 mm desde o início do reinício **ou** passaram 10 s. Ela usa a posição de referência registrada quando a fase mudou. Como a fase `RUN` é emitida pelo `referee_state_node` com a mesma regra, `WaitBallInPlay` é útil para as folhas que precisam reagir *dentro* da fase (como o goleiro do pênalti).
