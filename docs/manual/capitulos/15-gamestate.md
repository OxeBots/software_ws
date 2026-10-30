# GameState e o referee_state_node

A peça que destrava todo o resto é um **estado de jogo único, tipado e confiável**. Este capítulo descreve o problema que ele resolve, o conteúdo da mensagem `GameState` e o funcionamento do nó que a produz, o `referee_state_node`.

## O problema: um número não é um estado

Hoje cada `strategy_node` lê o campo `command` do `Referee` e as árvores comparam esse inteiro com literais. Isso falha de três maneiras:

- **Comandos não identificam a situação.** `NORMAL_START` (2) tanto pode ser um kick-off quanto um pênalti. Quem lê "o comando atual" não sabe qual.
- **Os comandos dependem da cor.** Para saber se um kick-off é nosso é preciso comparar o comando (4 ou 5) com a nossa cor, em cada ramo, em cada árvore.
- **Nada protege contra mensagens ruins.** Repetições, atrasos e a falta total de mensagens não são tratados; o valor inicial `−1` ("nunca recebi") cai no jogo corrido.

A solução é um componente que **interpreta uma vez, corretamente**, e entrega o resultado já pronto para todos os robôs.

## A mensagem GameState

`GameState` é publicado em `/game_state` (QoS confiável e `transient_local`, para que um nó que entre depois receba o último estado). Seus campos:

| Campo | Tipo | Significado |
|---|---|---|
| `header.stamp` | tempo | instante de recepção, no relógio local |
| `command_counter` | `uint32` | contador do `Referee`; usado para descartar repetições |
| `command` | `uint8` | comando cru, só para diagnóstico |
| `phase` | `uint8` (enum) | **a fase de jogo**: `PHASE_HALT` (0), `PHASE_TIMEOUT` (1), `PHASE_STOP` (2), `PHASE_BALL_PLACEMENT` (3), `PHASE_PREPARE_KICKOFF` (4), `PHASE_KICKOFF` (5), `PHASE_PREPARE_PENALTY` (6), `PHASE_PENALTY` (7), `PHASE_FREE_KICK` (8), `PHASE_RUN` (9) |
| `restart_ctx` | `uint8` (enum) | contexto do reinício: `RESTART_NONE` (0), `RESTART_KICKOFF` (1), `RESTART_PENALTY` (2), `RESTART_FREE_KICK` (3), `RESTART_FORCE` (4) |
| `we_favored` | `bool` | o reinício em curso é **a nosso favor** |
| `stage` | `uint8` | estágio da partida (tempo, intervalo…) |
| `our_goal_positive_x` | `bool` | o nosso gol está no lado de x positivo |
| `designated_position`, `has_designated` | ponto (mm), `bool` | posição designada (ball placement, free kick) |
| `speed_limit_mps` | `float` | teto de velocidade na fase atual |
| `ball_min_distance_mm` | `float` | distância mínima à bola exigida dos adversários (500) |
| `can_place_ball` | `bool` | nosso time pode posicionar a bola |
| `max_allowed_bots` | `uint8` | número de robôs permitidos (cartões) |
| `our_goalkeeper_id` | `uint32` | identificador do nosso goleiro, segundo o árbitro |
| `stale` | `bool` | o Game Controller deixou de enviar mensagens |

As **fases** reproduzem os estados da máquina de estados do regulamento (Capítulo 2). Observe a diferença que isso faz: onde antes havia o inteiro `2`, agora há `KICKOFF` ou `PENALTY`, e `we_favored` diz a quem favorece.

## O pipeline do nó

O `referee_state_node` assina o `Referee`, aplica seis passos e publica o `GameState` ({{fig:game_state_pipeline}}).

![Os seis passos que transformam um Referee em um GameState](figuras/game_state_pipeline.png)

### 1. Descartar repetições e mensagens antigas

O GC publica o mesmo comando várias vezes por segundo. O nó só processa uma mensagem quando o `command_counter` **avança**; mensagens com contador igual ou menor são ignoradas. Isso impede que uma mensagem atrasada ou duplicada sobrescreva um estado mais novo.

### 2. Mapear o comando para a fase

O mapeamento está na {{fig:mapa_comando_fase}} e detalhado na tabela oficial abaixo (considerando `is_yellow_team` e o contexto anterior `prev_ctx` / `prev_favored`):

![Como cada comando do árbitro é traduzido para uma fase do jogo](figuras/mapa_comando_fase.png)

| `Referee.command` (ID) | `phase` resultante | `restart_ctx` resultante | `we_favored` | `speed_limit_mps` | `ball_min_distance_mm` | Observação |
|---|---|---|---|---|---|---|
| *(Inicial — sem GC)* | `PHASE_HALT` (0) | `RESTART_NONE` (0) | `false` | `0,0` | `0,0` | `stale = true` até o 1º pacote |
| `HALT` (0) | `PHASE_HALT` (0) | *(mantém `prev_ctx`)* | *(mantém `prev_favored`)* | `0,0` | `0,0` | Preserva contexto de preparação |
| `STOP` (1) | `PHASE_STOP` (2) | *(mantém `prev_ctx`)* | *(mantém `prev_favored`)* | `0,75` | `500,0` | Preserva contexto de preparação |
| `NORMAL_START` (2) c/ `prev_ctx == KICKOFF` | `PHASE_KICKOFF` (5) | `RESTART_KICKOFF` (1) | *(herda `prev_favored`)* | `1,5` | `0,0` se `we_favored` senão `500,0` | Vai a `PHASE_RUN` quando bola move ≥ 50 mm ou 10 s |
| `NORMAL_START` (2) c/ `prev_ctx == PENALTY` | `PHASE_PENALTY` (7) | `RESTART_PENALTY` (2) | *(herda `prev_favored`)* | `1,5` | `0,0` (regra de 1 m atrás da bola) | Até 10 s (GC encerra com STOP/GOAL) |
| `NORMAL_START` (2) c/ outro `prev_ctx` | `PHASE_RUN` (9) | `RESTART_NONE` (0) | `false` | `1,5` | `0,0` | Fallback caso o nó inicie sem ter visto o `PREPARE_*` |
| `FORCE_START` (3) | `PHASE_RUN` (9) | `RESTART_FORCE` (4) | `false` | `1,5` | `0,0` | Bola em jogo imediatamente |
| `PREPARE_KICKOFF_YELLOW` (4) | `PHASE_PREPARE_KICKOFF` (4) | `RESTART_KICKOFF` (1) | `is_yellow_team` | `0,75` | `500,0` | — |
| `PREPARE_KICKOFF_BLUE` (5) | `PHASE_PREPARE_KICKOFF` (4) | `RESTART_KICKOFF` (1) | `!is_yellow_team` | `0,75` | `500,0` | — |
| `PREPARE_PENALTY_YELLOW` (6) | `PHASE_PREPARE_PENALTY` (6) | `RESTART_PENALTY` (2) | `is_yellow_team` | `0,75` | `500,0` | — |
| `PREPARE_PENALTY_BLUE` (7) | `PHASE_PREPARE_PENALTY` (6) | `RESTART_PENALTY` (2) | `!is_yellow_team` | `0,75` | `500,0` | — |
| `DIRECT_FREE_YELLOW` (8) | `PHASE_FREE_KICK` (8) | `RESTART_FREE_KICK` (3) | `is_yellow_team` | `1,5` | `0,0` se `we_favored` senão `500,0` | Vai a `PHASE_RUN` quando bola move ≥ 50 mm ou 10 s |
| `DIRECT_FREE_BLUE` (9) | `PHASE_FREE_KICK` (8) | `RESTART_FREE_KICK` (3) | `!is_yellow_team` | `1,5` | `0,0` se `we_favored` senão `500,0` | Idem |
| `INDIRECT_FREE_YELLOW` (10, legado) | `PHASE_FREE_KICK` (8) | `RESTART_FREE_KICK` (3) | `is_yellow_team` | `1,5` | `0,0` se `we_favored` senão `500,0` | Normalizado para `FREE_KICK` |
| `INDIRECT_FREE_BLUE` (11, legado) | `PHASE_FREE_KICK` (8) | `RESTART_FREE_KICK` (3) | `!is_yellow_team` | `1,5` | `0,0` se `we_favored` senão `500,0` | Normalizado para `FREE_KICK` |
| `TIMEOUT_YELLOW` (12) | `PHASE_TIMEOUT` (1) | *(mantém `prev_ctx`)* | `is_yellow_team` | `0,0` | `0,0` | Equipes paradas |
| `TIMEOUT_BLUE` (13) | `PHASE_TIMEOUT` (1) | *(mantém `prev_ctx`)* | `!is_yellow_team` | `0,0` | `0,0` | Equipes paradas |
| `GOAL_YELLOW` (14, legado) | `PHASE_STOP` (2) | `RESTART_NONE` (0) | `is_yellow_team` | `0,75` | `500,0` | Normalizado para `STOP` |
| `GOAL_BLUE` (15, legado) | `PHASE_STOP` (2) | `RESTART_NONE` (0) | `!is_yellow_team` | `0,75` | `500,0` | Normalizado para `STOP` |
| `BALL_PLACEMENT_YELLOW` (16) | `PHASE_BALL_PLACEMENT` (3) | *(mantém `prev_ctx`)* | `is_yellow_team` | `0,75` | `0,0` se `(we_favored && can_place_ball)` senão `500,0` | `has_designated = !designated_position.empty()` |
| `BALL_PLACEMENT_BLUE` (17) | `PHASE_BALL_PLACEMENT` (3) | *(mantém `prev_ctx`)* | `!is_yellow_team` | `0,75` | `0,0` se `(we_favored && can_place_ball)` senão `500,0` | Idem |

Os comandos legados (`INDIRECT_FREE` 10/11 e `GOAL` 14/15) são normalizados: os primeiros viram `FREE_KICK`; os segundos, `STOP`.

### 3. Lembrar o contexto do reinício

Este é o passo que resolve o `NORMAL_START`. O nó mantém uma pequena memória:

- ao receber `PREPARE_KICKOFF_*`, guarda `restart_ctx = KICKOFF` e `we_favored` conforme a cor;
- ao receber `PREPARE_PENALTY_*`, guarda `restart_ctx = PENALTY`;
- ao receber `NORMAL_START`, a fase vira `KICKOFF` ou `PENALTY` conforme o contexto guardado, e `we_favored` é herdado;
- ao receber `HALT` ou `STOP`, o contexto **não** é apagado (o HALT é sempre seguido de STOP, e depois pode vir o `NORMAL_START` que o árbitro tinha preparado). O contexto só é substituído por um novo `PREPARE_*`, `DIRECT_FREE` ou `FORCE_START`.

A mensagem do GC também traz o campo `next_command`, que informa o comando que virá depois da parada atual. Ele pode ser usado, no futuro, para pré-posicionar os robôs durante o STOP.

### 4. Derivar as flags

Com a fase e a cor, o nó calcula os campos derivados:

- **`we_favored`**: o sufixo do comando (`_YELLOW`/`_BLUE`) comparado com a cor do nosso time.
- **`speed_limit_mps`**: 0 em `HALT` e `TIMEOUT`; **0,75** nos estados de parada (`STOP`, `BALL_PLACEMENT`, `PREPARE_*`); 1,5 nos estados de jogo (o limite do regulamento). A escolha de aplicar 0,75 também às preparações é conservadora e configurável.
- **`ball_min_distance_mm`**: 500 em `STOP`, `BALL_PLACEMENT`, `PREPARE_*` e, para quem não é o favorecido, em `KICKOFF` e `FREE_KICK`.
- **`can_place_ball`, `max_allowed_bots`, `our_goalkeeper_id`**: copiados de `TeamInfo` do nosso time.

### 5. Resolver o lado do campo

O nó lê `blue_team_on_positive_half` do `Referee` e, com a nossa cor, calcula `our_goal_positive_x`. É isso que permite ao time **trocar de lado entre os tempos** sem nenhuma outra mudança. (O que a estratégia faz com esse valor está no Capítulo 20.)

### 6. Marcar o estado como velho

Um temporizador de 100 ms verifica há quanto tempo chegou a última mensagem. Se passou de 500 ms, o `GameState` é republicado com `stale = true`. Quem consome (a condição `IsDataFresh`, o SafetyGate) trata esse caso como falha de comunicação.

## Quando o jogo volta a "correr"

Os estados `KICKOFF` e `FREE_KICK` terminam quando a bola entra em jogo: ela se move pelo menos 0,05 m **ou** passam 10 s (regra 5.4). O nó precisa decidir quando emitir a fase `RUN`. Há duas fontes possíveis: (a) o **próprio Game Controller**, se ele mudar o comando ao detectar a bola em jogo; (b) o **cálculo local**, comparando a posição da bola (entrada `ball_data`) com a posição de partida do reinício.

!!! warning "Uma pergunta que o regulamento não responde"
    O regulamento descreve o *estado* `Run`, mas não diz **qual valor** do campo `command` o Game Controller publica durante ele (se o `DIRECT_FREE` permanece, se vira `NORMAL_START`, ou outro). Por isso o nó implementa a opção (b), parametrizável, e o plano de implementação (Capítulo 24) começa com a **captura de um log real do GC** (a ferramenta `log2bag` do `ssl_ros_bridge` converte logs da liga em *rosbags*) para confirmar o comportamento.

## Um exemplo: um pênalti a nosso favor

A tabela mostra o que o nó publica a cada comando recebido, num pênalti a favor do time amarelo, visto pelo nosso time (amarelo):

| Comando recebido | `phase` | `restart_ctx` | `we_favored` | `speed_limit` |
|---|---|---|---|---|
| `HALT` | `HALT` | — | — | 0 |
| `STOP` | `STOP` | — | — | 0,75 |
| `PREPARE_PENALTY_YELLOW` | `PREPARE_PENALTY` | `PENALTY` | **sim** | 0,75 |
| `NORMAL_START` | `PENALTY` | `PENALTY` | **sim** | 1,5 |
| (bola move ≥ 0,05 m, ou 10 s) | `STOP` (o GC pára o jogo) ou `RUN` | — | — | — |

Compare com o sistema atual: ali, o `NORMAL_START` apagava a informação de que era um pênalti nosso.

## Configuração e testes

Parâmetros do nó: `is_yellow_team` (a cor), `stale_timeout_ms` (500), `ball_moved_mm` (50), `kick_timeout_s` (10), `stop_speed_mps` (0,75) e `play_speed_mps` (1,5). Por ser um nó pequeno e sem dependência de hardware, ele é a primeira peça a receber testes automatizados: uma tabela de comandos de entrada e fases de saída, mais *replays* de logs reais do GC (Capítulo 23).
