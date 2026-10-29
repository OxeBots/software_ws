<!-- apendice -->
# Referência de nós, mensagens e tópicos

## Catálogo das folhas existentes

As 29 folhas registradas em `strategy_node.cpp`. "Usos" é o número de ocorrências nos XMLs do repositório. Tipos: **Cond** = condição; **Sync** = ação síncrona; **SA** = ação assíncrona (stateful).

### Movimento e chute

| Folha | Tipo | Portas de entrada (tipo, padrão) | Saídas | Retornos | `onHalted` | Usos |
|---|---|---|---|---|---|---|
| `GoToPoint` | SA | `robot_id` (uint), `x`, `y` (double), `face_x`, `face_y` (double, opcionais), `tolerance` (−1), `planner` ("dstar"), `ball_contact_threshold_mm` (−1), `ignore_area` (false), `ball_side_check` (false) | — | RUNNING; SUCCESS na tolerância; FAILURE por contato/lado/portas | vazio | 93 |
| `KickBall` | SA | `robot_id` (uint), `kick_speed` (3,0; limitado a 3,0) | — | RUNNING; SUCCESS quando o chute conclui | libera o override | 17 |
| `AlignToBall` | SA | `robot_id`, `angle_threshold_deg` (10), `max_angular_speed` (3), `p_gain` (4) | — | RUNNING; SUCCESS alinhado | libera o override | 0 |
| `PrecisionKick` | SA | `robot_id`, `target_x`, `target_y`, `kick_speed` (3,5; **sem limite**) | — | RUNNING; SUCCESS 150 ms após o chute | comando zero | 4 |
| `Goalkeeper` | SA | `robot_id` (uint32, 0), `kick_speed` (3,0) | — | sempre RUNNING | libera o chute | 4 |

### Dados da bola e ataque

| Folha | Tipo | Portas de entrada | Saídas | Retornos | Usos |
|---|---|---|---|---|---|
| `UpdateBallPosition` | SA | `robot_id`, `goal_x`, `goal_y` | `ball_x`, `ball_y`, `pre_kick_x/y`, `is_ready_to_kick`, `ball_in_enemy_half` | SUCCESS; RUNNING sem dados | 44 |
| `CalculateInterception` | SA | `robot_id`, `goal_x` (0), `goal_y` (0), `carry_distance_mm` (−120), `carry_face_lookahead_mm` (400) | `intercept_x/y`, `intercept_pk_x/y`, `intercept_pk_safe_x/y`, `intercept_capture_x/y`, `intercept_carry_x/y`, `intercept_carry_face_x/y`, `is_ready_to_kick` | SUCCESS; RUNNING sem predição | 4 |
| `IsBallClose` | Cond | `robot_id`, `distance_threshold` (180), `angle_threshold_deg` (−1) | — | SUCCESS/FAILURE | 24 |
| `IsBallInOurHalf` | Cond | `ball_x` | — | SUCCESS/FAILURE (histerese 100 mm) | 3 |
| `IsBallInArea` | Cond | `ball_x`, `ball_y` | — | SUCCESS/FAILURE | 0 |

### Defesa

| Folha | Tipo | Portas de entrada | Retornos | Usos |
|---|---|---|---|---|
| `IsBallInOpponentField` | Cond | `ball_x`, `is_yellow` | SUCCESS/FAILURE | 1 |
| `IsOpponentControllingBall` | Cond | `opponent_controlling` | SUCCESS/FAILURE | 1 |
| `ShadowBall` | Sync | `ball` (Pose2D), `ball_vel` (Vector2D), `my_goal_x`, `follow_distance` (1200), `predict_time` (0,3), `penalty_area_depth`, `y_limit` (900) | SUCCESS (publica o alvo) | 2 |
| `MarkOpponent` | Sync | `ball`, `my_goal_x`, `block_distance` (400), `penalty_area_depth`, `y_limit` (1200) | SUCCESS | 1 |
| `GoToClamped` | SA | `x`, `y`, `my_goal_x`, `penalty_area_depth` | sempre RUNNING | 0 |
| `GoalLineDefend` | SA | `robot_id`, `ball_y` | RUNNING | 0 |
| `LateralClear` | SA | `robot_id`, `ball_x`, `ball_y` | RUNNING; SUCCESS ao concluir | 0 |
| `PositionBisector` | SA | `robot_id`, `ball_x`, `ball_y`, `goal_width` | RUNNING | 0 |
| `SmotherSave` | SA | `robot_id`, `ball_x`, `ball_y` | RUNNING | 0 |

### Utilitários e condições simples

| Folha | Tipo | Portas | O que faz | Usos |
|---|---|---|---|---|
| `CheckGCCommand` | Cond | `expected` (int) | `gc_command == expected` | 31 |
| `IsValueTrue` | Cond | `value` (bool) | FAILURE se ausente ou falso | 30 |
| `IsThisNodeID` | Cond | `id` (uint) | o robô do processo é `id` | 30 |
| `IsMyRole` | Cond | `role` (string: `attacker` / `defender`) | compara `robot_id` com `attacker_id`/`defender_id` | 24 |
| `IsRobotId` | Cond | `robot_id` (uint32) | `robot_id` da blackboard é igual | 7 |
| `Halt` | Sync | `reason` (string) | pede `MODE_HALT`; sempre SUCCESS | 36 |
| `KeepDistance` | Sync | `robot_id`, `distance`, `ball_x`, `ball_y`, `robot_x`, `robot_y` (todas obrigatórias) | calcula ponto de recuo em `target_x/y` | 4 |
| `AimAt` | Sync | `robot_id`, `target_x`, `target_y`, `robot_x`, `robot_y` | calcula `target_angle` | 2 |
| `HasLineOfSight` | Cond | `robot_id`, `target_x`, `target_y` | *stub*: sempre SUCCESS | 2 |
| `CalculateKickOffPose` | Sync | `robot_id` | posição fixa x = −1000 | 0 |

## Mensagens principais

### `GameData`

| Campo | Tipo | Observação |
|---|---|---|
| `robots.allies[]`, `robots.enemies[]` | `RobotGameData { x, y, orientation, id }` | mm, rad |
| `ball` | `BallPosition { x, y, z, confidence }` | mm |

(Proposta: acrescentar `header` e o carimbo de cada robô — Capítulo 20.)

### `RobotGoal`

| Campo | Tipo | Observação |
|---|---|---|
| `robot_id` | int32 | |
| `pose` | `PoseStamped` | **metros**; orientação por quaternion |
| `planner_type` | uint8 | 0 = D\*, 1 = A\* (hoje equivale ao D\*), 2 = linha reta |
| `disable_arrival_latch` | bool | verdadeiro quando `tolerance ≤ 0` |

### `RobotMotionOverride` e `RobotMotionStatus`

| Mensagem | Campos principais |
|---|---|
| `RobotMotionOverride` | `robot_id`; `mode` (0 NONE, 1 ALIGN_TO_BALL, 2 ALIGN_TO_ANGLE, 3 KICK, 4 HALT); `target_angle`; `angle_threshold_deg`; `max_angular_speed`; `p_gain`; `kick_speed` |
| `RobotMotionStatus` | `robot_id`; `active_mode`; `aligned`; `kick_fire_count` |

### `RobotCmd` / `RobotCmdData`

`id`, `kick_speed` (m/s; zero fora do chute), `x_velocity`, `y_velocity` (m/s, referencial global), `angular_velocity` (rad/s).

### `RoleAssignment`

Atual: `attacker_id`, `defender_id`. Proposta: acrescenta `goalkeeper_id`, `kicker_id`, `epoch`, `active_ids[]`.

### Predições

`BallPrediction`: `x, y, vx, vy, ax, ay`. `RobotPrediction`: listas `allies[]`/`enemies[]` de `RobotPredictionData` com `id, x, y, vx, vy, ax, ay, orientation, vorientation`.

## Tópicos

| Tópico | Tipo | Quem publica | Quem assina |
|---|---|---|---|
| `…/vision_messages` | `VisionWrapper` | `ssl_vision_bridge` | `game_observer_node` |
| `…/referee_messages` | `ssl_league_msgs/Referee` | `gc_multicast_bridge` | `strategy_node`, observer (e `referee_state_node` na proposta) |
| `/game_data` | `GameData` | observer | quase todos |
| `/field_geometry` | `SSLGeometryData` (TL) | observer | `strategy_node`, folhas, D\*, controlador |
| `/map` | `OccupancyGrid` (TL) | observer | D\* |
| `ball_data`, `robot_data` | `BallPosition`, `RobotPosition` | observer | Kalman |
| `ball_predicted`, `robot_predicted` | `BallPrediction`, `RobotPrediction` | Kalman | `CalculateInterception`, `trajectory_setpoint_node` |
| `/role_assignment` | `RoleAssignment` | `role_assigner_node` | `strategy_node` |
| `/robot_goal` | `RobotGoal` (TL) | folhas de movimento | D\*, controlador, setpoint |
| `/robot_<i>/path` | `nav_msgs/Path` | D\* | controlador |
| `/robot_motion_override` | `RobotMotionOverride` | `Halt`, `KickBall`, `Goalkeeper`, `AlignToBall` | controlador |
| `/robot_motion_status` | `RobotMotionStatus` | controlador | `KickBall`, `AlignToBall` |
| `/robot_commands` | `RobotCmd` | controlador (e `PrecisionKick`) | driver, setpoint |
| `/robot_trajectory_setpoints` | `RobotTrajectorySetpoint` | `trajectory_setpoint_node` | rádio (modo ponto) |
| `/robot_telemetry` | `RobotTelemetry` | rádio NRF24 | (ninguém na estratégia) |
| `/game_state` *(proposto)* | `GameState` (TL) | `referee_state_node` | `strategy_node`, controlador |
| `/robot_motion_limit` *(proposto)* | a definir | `SetMotionLimit` | SafetyGate |
| `/strategy/active_branch` *(proposto)* | `std_msgs/String` | `strategy_node` | rosbag, depuração |
