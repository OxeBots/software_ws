<!-- apendice -->
# Parâmetros e comandos de execução

## Subindo o sistema

Todos os comandos abaixo são executados dentro do *devcontainer* do projeto, com o workspace compilado (`./build.sh`) e o ambiente carregado (`source install/setup.bash`).

```bash
# Simulação no grSim (padrão), RViz aberto
ros2 launch oxebots_bringup ssl-new.launch.py

# Escolhendo a cor do time pelo arquivo de configuração
ros2 launch oxebots_bringup ssl-new.launch.py team_color:=blue
ros2 launch oxebots_bringup ssl-new.launch.py team_color:=yellow

# Simulador ER-Force / Ra (inverte os lados por padrão)
ros2 launch oxebots_bringup ssl-new.launch.py mode:=ra

# Jogo real com rádio NRF24 (velocidade ou ponto)
ros2 launch oxebots_bringup ssl-new.launch.py mode:=game
ros2 launch oxebots_bringup ssl-new.launch.py mode:=game command_mode:=point

# Testar outra árvore, sem RViz
ros2 launch oxebots_bringup ssl-new.launch.py bt_xml:=simple_attack.xml use_rviz:=False

# Partida completa simulada, azul × amarelo (domínios ROS 0 e 1)
./run_match.sh
./run_match.sh rviz_team:=blue
```

## Argumentos do launch

| Argumento | Valores | Padrão | Efeito |
|---|---|---|---|
| `mode` | `grsim`, `ra`, `game` | `grsim` | driver de comunicação |
| `command_mode` | `velocity`, `point` | `velocity` | formato do comando do rádio |
| `invert_sides` | `True`, `False`, vazio | automático (`True` só em `ra`) | espelha o campo |
| `config_file` | caminho `.yaml` | `match_config.yaml` | arquivo de configuração |
| `team_color` | `blue`, `yellow` | vazio | atalho para o YAML do time |
| `bt_xml` | nome de `.xml` | valor do YAML | árvore principal |
| `use_rviz` | `True`, `False` | `True` | abre o RViz |
| `match` | `True`, `False` | `False` | dois times, domínios 0 e 1 |
| `rviz_team` | `none`, `blue`, `yellow`, `both` | `none` | RViz por time (com `match`) |
| `enable_blue`, `enable_yellow` | `True`, `False` | `True` | liga/desliga cada time (com `match`) |

## Parâmetros dos nós de estratégia

| Nó | Parâmetro | Padrão | Descrição |
|---|---|---|---|
| `strategy_node` | `bt_xml_path` | `master_strategy_carry.xml` (YAML) | árvore principal |
| | `is_yellow_team` | `false` | cor do time |
| | `invert_sides` | `false` | espelhamento do campo |
| | `robot_id` | 1 (definido por robô no launch) | robô comandado |
| | `execution_rate` | 60,0 Hz | frequência do tick |
| | `gc_topic` | `/gc_multicast_bridge/referee_messages` | comando do árbitro |
| | `possession_distance` | 220,0 mm | limiar de posse do adversário |
| `movement_calculation_node` | `max_linear_speed` | 1,0 m/s | teto de velocidade linear |
| | `p_gain_linear` | 2,0 | ganho linear |
| | `max_angular_speed` | 4,0 rad/s | teto angular |
| | `p_gain_angular` | 3,0 | ganho angular |
| | `angle_tolerance` | 0,1 rad | tolerância angular |
| | `lookahead_distance` | 100,0 mm | distância de perseguição |
| `d_star_planner_node` | `planning_rate_hz` | 10,0 | taxa de replanejamento |
| | `planning_rate_hz_close` | 40,0 | taxa perto da bola |
| | `close_ball_distance_m` | 0,4 | limiar de "perto da bola" |
| | `robot_safety_radius` | 0,20 m | raio de segurança dos aliados |
| | `ball_safety_radius` | 0,15 m | raio de segurança da bola |
| | `occupancy_threshold` | 80 | limiar de ocupação |
| | `max_expansions` | 100000 | limite de expansões do planejador |
| `role_assigner_node` | `goalkeeper_id` | 0 | goleiro (excluído do sorteio) |
| | `w1`, `w2` | 2,0; 1,0 | pesos de distância e alinhamento |
| | `hysteresis` | 2,5 | histerese de custo |
| | `time_hysteresis` | 2,0 s | tempo mínimo entre trocas |
| `game_observer_node` | `team_size` | 3 | robôs por time |
| | `map_resolution` | 0,05 m | resolução da grade |
| | `robot_inflation_radius` | 150,0 mm | inflação dos robôs na grade |
| | `min_ball_confidence` | 0,3 | confiança mínima da bola |
| `kalman_filter_node` | `ball_friction_accel` | 800,0 mm/s² | atrito do carpete |
| | `ball_kick_threshold_mm` | 80,0 | limiar de detecção de chute |
| | `ball_process_noise`, `ball_pos_measurement_noise` | 2000,0; 3,0 | ruídos do modelo da bola |
| | `robot_pos_process_noise`, `robot_pos_measurement_noise` | 4000,0; 3,0 | ruídos do modelo do robô |
| `trajectory_setpoint_node` | `radio_publish_rate_hz`, `lookahead_safety_factor`, `max_lookahead_mm` | — | modo ponto do rádio |

## Portas de rede

| Serviço | Endereço padrão |
|---|---|
| SSL-Vision | multicast `224.5.23.2`, porta `10020` (jogo real: `10006`) |
| Game Controller | multicast `224.5.23.1`, porta `10003` |
| grSim (controle) | UDP `127.0.0.1:10301` (azul) / `10302` (amarelo) |
| Groot2 (por robô) | `1667 + id` (azul), `1677 + id` (amarelo) |

## Parâmetros propostos (Parte IV)

| Componente | Parâmetro | Valor inicial |
|---|---|---|
| `referee_state_node` | `stale_timeout_ms` | 500 |
| | `ball_moved_mm` | 50 |
| | `kick_timeout_s` | 10 |
| | `stop_speed_mps` / `play_speed_mps` | 0,75 / 1,5 |
| `IsDataFresh` | `max_gc_ms` / `max_pose_ms` / `max_ball_ms` | 500 / 150 / 300 |
| SafetyGate | watchdog | 500 ms |
| | teto de chute | 3,0 m/s |
| `ComputeLegalSlot` | `slot_margin_mm` | 150 |
| `KickOnce` | `kick_speed` / `timeout_s` | 2,5 / 10 |
| `BallHeldTimer` | `max_s` | 8 |
