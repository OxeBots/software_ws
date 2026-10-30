# Catálogo dos nós novos e das adaptações

Este capítulo é a **especificação** dos componentes novos e das alterações em componentes existentes, em nível suficiente para serem implementados sem ambiguidade. Convenções: posições em mm e ângulos em rad; toda porta de entrada com valor sensato tem **padrão** (para evitar o erro do Capítulo 5); toda ação assíncrona tem `onHalted` idempotente; toda folha que depende de dados devolve FAILURE com log quando eles faltam.

## Os 14 nós novos

### Condições

**`CheckGameState`** — verdadeira se a fase da blackboard é a pedida.
- Porta `phase` (`string`, obrigatória): `HALT`, `TIMEOUT`, `STOP`, `BALL_PLACEMENT`, `PREPARE_KICKOFF`, `KICKOFF`, `PREPARE_PENALTY`, `PENALTY`, `FREE_KICK` ou `RUN`.
- Lê `phase` da blackboard raiz; se a chave não existe, devolve FAILURE com erro.

**`WeAreFavored`** — verdadeira se `we_favored` é verdadeiro. Sem portas.

**`IsDataFresh`** — verdadeira se todas as idades estão dentro dos limites.
- Portas: `max_gc_ms` (500), `max_pose_ms` (150), `max_ball_ms` (300), todas `double`.
- Lê `gc_age_ms`, `pose_age_ms`, `ball_age_ms`; registra qual dado venceu.

**`HasRole`** — verdadeira se o papel do robô na blackboard é o pedido.
- Porta `role` (`string`): `goalkeeper`, `attacker`, `defender` ou `kicker`.
- Substitui `IsMyRole` e `IsRobotId`.

**`BallHeldTimer`** — falha quando a bola está parada dentro da área por mais de `max_s`.
- Portas: `max_s` (`double`, 8), `area` (`string`, `"own_defense"`).
- Usa `ball`, `ball_vel` e a geometria; serve de gatilho para o goleiro afastar a bola.

**`WaitBallInPlay`** — verdadeira quando a bola se moveu `moved_mm` (50) desde o início do reinício **ou** passaram `timeout_s` (10).

### Ações síncronas

**`ComputeLegalSlot`** — calcula a posição legal de um slot (Capítulo 18).
- Entradas: `slot` (`string`), `index` (`uint32`, 0).
- Saídas: `slot_x`, `slot_y`, `slot_w` (`double`).
- Parâmetro ROS: `slot_margin_mm` (150).
- Usa `own_goal_x`, `side_sign`, `ball`, `center_circle_radius`, `penalty_area_*`, `designated`, `robot_pose`.

**`ComputePlacementApproach`** — para o ball placement: calcula o ponto de captura (`pickup_x/y`), o de entrega (`drop_x/y`) e a orientação (`approach_w`) a partir da posição designada. Parâmetro: `pickup_offset_mm` (120).

**`SetMotionLimit`** — informa o teto de velocidade ao SafetyGate: porta `limit_mps` (`double`, 1,5), parâmetro `absolute_max_mps` (1,5). Publica em `/robot_motion_limit`.

### Ações assíncronas

**`HoldPosition`** — mantém o robô onde está: publica `RobotGoal` na pose atual (`straight_line`, `disable_arrival_latch = true`) e fica em RUNNING. `onHalted` não publica nada.

**`PlaceBall`** — empurra a bola até a posição designada.
- Portas: `drop_x`, `drop_y` (`double`), `timeout_s` (30), `tolerance_mm` (150).
- RUNNING; SUCCESS quando a bola está a ≤ `tolerance_mm` do alvo, parada, e o robô a mais de 50 mm; FAILURE no estouro do prazo. `onHalted` solta o override e recua 100 mm.

**`PenaltyKeeperLine`** — leva o goleiro à linha de gol (a 90 mm dela, para dentro) e o mantém. Porta `side` (`string`, `"defend"`); parâmetro `line_offset_mm` (90). RUNNING até a bola entrar em jogo.

**`KickOnce`** — chuta uma vez e confirma o resultado.
- Portas: `robot_id` (`uint32`), `target_x`, `target_y` (`double`), `kick_speed` (2,5; limitado a 3,0), `timeout_s` (10), `ball_moved_mm` (50).
- Envia `MODE_KICK`; SUCCESS quando a bola se moveu `ball_moved_mm`; FAILURE no estouro do prazo. `onHalted` envia `MODE_NONE`.

**`AvoidPlacementCorridor`** — sai do corredor do posicionamento adversário: porta `margin_mm` (550). RUNNING enquanto precisa mover-se, SUCCESS quando já está fora.

## As adaptações

| Alvo | O que muda | Por quê |
|---|---|---|
| **`GoToPoint`** | `onHalted` publica a pose atual; `robot_id` diferente da instância devolve FAILURE com erro (ou a porta é removida); robô ausente por mais de 500 ms → FAILURE; nova porta opcional `max_speed` | a preempção precisa parar o robô; erros de configuração não podem ser silenciosos |
| **`KeepDistance`** | `robot_x`/`robot_y` com padrão `{robot_x}`/`{robot_y}`; ou torná-la uma ação que publica o alvo de afastamento | corrige a falha de portas do STOP |
| **`PrecisionKick`** | aposentar (usar `KickOnce`) ou limitar a 3,0 m/s e passar pelo override | limite de chute; escritor único |
| **`Goalkeeper`** | portas `mode` e `max_hold_s`; identidade via `HasRole`; FAILURE sem dados | regras de pênalti e de 10 s |
| **`UpdateBallPosition`** | `ball_in_enemy_half` usa `side_sign`; FAILURE sem dados; marcadores opcionais | independência de lado |
| **`movement_calculation_node`** | SafetyGate: assina `/game_state` e `/robot_motion_limit`; watchdog de 500 ms; clamp de chute; `MODE_HALT` sem TTL | segurança independente da árvore |
| **`strategy_node`** | assina `/game_state` (remove `gc_callback`); `refresh()` por tick; remove papéis iniciais fixos; registra os novos nós; só carrega XMLs de produção | centralizar estado e consistência |
| **`role_assigner_node`** | mensagem ampliada; cobrador travado; goleiro do GC; robôs ativos | papéis conscientes da fase |
| **`game_observer_node` / `GameData`** | carimbo de tempo; expiração de robôs; publica sem bola; fusão com confiança | idade dos dados |

## O novo nó ROS 2: referee_state_node

| Item | Especificação |
|---|---|
| Assina | `…/referee_messages` (`ssl_league_msgs/Referee`) e, para detectar a bola em jogo, `ball_data` |
| Publica | `/game_state` (`oxebots_interfaces/GameState`, confiável, `transient_local`) |
| Parâmetros | `is_yellow_team`, `stale_timeout_ms` (500), `ball_moved_mm` (50), `kick_timeout_s` (10), `stop_speed_mps` (0,75), `play_speed_mps` (1,5) |
| Lógica | descarte por `command_counter`; mapeamento comando→fase; contexto de reinício; flags; lado; marcação de `stale` (Capítulo 15) |

## A mensagem GameState

Definida em `oxebots_interfaces/msg/GameState.msg`:

```text
std_msgs/Header header
uint32  command_counter
uint8   command

uint8   PHASE_HALT=0
uint8   PHASE_TIMEOUT=1
uint8   PHASE_STOP=2
uint8   PHASE_BALL_PLACEMENT=3
uint8   PHASE_PREPARE_KICKOFF=4
uint8   PHASE_KICKOFF=5
uint8   PHASE_PREPARE_PENALTY=6
uint8   PHASE_PENALTY=7
uint8   PHASE_FREE_KICK=8
uint8   PHASE_RUN=9
uint8   phase

uint8   RESTART_NONE=0
uint8   RESTART_KICKOFF=1
uint8   RESTART_PENALTY=2
uint8   RESTART_FREE_KICK=3
uint8   RESTART_FORCE=4
uint8   restart_ctx

bool    we_favored
uint8   stage
bool    our_goal_positive_x
geometry_msgs/Point32 designated_position   # mm
bool    has_designated
float32 speed_limit_mps
float32 ball_min_distance_mm
bool    can_place_ball
uint8   max_allowed_bots
uint32  our_goalkeeper_id
bool    stale
```
