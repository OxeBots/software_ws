# Visão geral do software

Este capítulo apresenta a pilha de software do OxeBots como um todo: quais pacotes existem, quais processos rodam durante uma partida, como os dados circulam entre eles e como tudo é iniciado. É o mapa que você deve ter na cabeça antes de entrar nos detalhes dos capítulos seguintes.

## O workspace e seus pacotes

O código vive em um *workspace* ROS 2 (`software_ws`) que reúne vários repositórios como submódulos Git dentro da pasta `src/`. Cada submódulo é um pacote com uma responsabilidade clara:

| Pacote | O que faz |
|---|---|
| `ssl_ros_bridge` | Pontes entre a rede da liga e o ROS 2: recebe os pacotes UDP/multicast do SSL-Vision e do Game Controller (formato Protobuf) e os publica como mensagens ROS 2. Também define as mensagens `ssl_league_msgs` e contém um cliente para os serviços do GC. |
| `oxebots_interfaces` | Mensagens, serviços e o protocolo binário do rádio: `GameData`, `RobotGoal`, `RobotCmd`, `RobotMotionOverride`, `RoleAssignment` e muitas outras. É a "língua comum" de todos os nós. |
| `oxebots_observers` | O `game_observer_node`, que converte a visão para o referencial interno e publica o estado de jogo, a geometria do campo e o mapa de obstáculos; e o `field_visualizer_node`, que desenha o campo no RViz. |
| `oxebots_prediction` | O `kalman_filter_node`: filtros de Kalman dedicados para a bola (com atrito do carpete) e para os robôs. |
| `oxebots_strategy` | O coração da estratégia: o `strategy_node` (Behavior Trees), o `role_assigner_node`, o planejador `d_star_planner_node`, o controlador `movement_calculation_node`, o `trajectory_setpoint_node`, todas as folhas de árvore e todos os arquivos XML. |
| `oxebots_comms` | Drivers de atuação: `grSim_controller_node` (simulador grSim), `ra_controller_node` (simulador ER-Force Ra) e `nrf24_bridge_node` (rádio dos robôs reais). |
| `oxebots_bringup` | Arquivos de *launch* e de configuração YAML: o comando único que sobe tudo. |
| `oxebots_trajectory_analysis` | Ferramenta Python de análise de rotas (não participa do jogo). |

## Os processos em execução

Durante uma partida rodam dois tipos de processo, como mostra a {{fig:arquitetura_processos}}.

![Os processos do sistema e os principais tópicos entre eles](figuras/arquitetura_processos.png)

**Processos únicos da equipe.** Existe uma única instância de cada um: as pontes SSL (visão e árbitro), o observador, o filtro de Kalman, o atribuidor de papéis e o driver de comunicação. Eles produzem informação que serve a todos os robôs ao mesmo tempo.

**Um conjunto de processos por robô.** Para cada robô (identificadores 0, 1 e 2), o sistema sobe quatro processos independentes:

- `strategy_node_<i>`: a Behavior Tree do robô e sua *blackboard* (a memória compartilhada da árvore).
- `d_star_planner_node_<i>`: o planejador de rotas.
- `path_follower_node_<i>`: o controlador de movimento (executável `movement_calculation_node`).
- `trajectory_setpoint_node_<i>`: converte a velocidade comandada em um ponto-alvo futuro, usado apenas quando o rádio opera em modo "ponto".

Essa estrutura tem uma consequência importante, que será retomada muitas vezes: **cada robô tem a sua própria árvore, com a sua própria blackboard**. Não existe uma "árvore do time". A coordenação entre robôs acontece por mensagens (por exemplo, o atribuidor de papéis diz quem é o atacante) e, de forma implícita, pelo fato de todas as árvores lerem os mesmos dados do jogo.

!!! note "Tópicos compartilhados entre os robôs"
    Vários tópicos (`/robot_goal`, `/robot_motion_override`, `/robot_commands`, `/robot_motion_status`) são **compartilhados**: os três robôs publicam e assinam no mesmo nome. Cada mensagem carrega o identificador do robô e cada receptor filtra o que não é seu. Isso simplifica a configuração, mas significa que um erro de identificação (um nó que comanda o robô errado) afeta o time inteiro.

## O caminho dos dados

A {{fig:fluxo_dados}} mostra, em ordem, o que acontece com a informação desde a câmera até o robô.

![O caminho de uma informação, da câmera ao robô](figuras/fluxo_dados.png)

1. **Câmeras → observer.** O SSL-Vision publica a cerca de 60 Hz. A ponte de visão traduz o pacote para uma mensagem ROS 2 e o `game_observer_node` a converte para milímetros e radianos, escolhe a detecção de bola de maior confiança, aplica a inversão de lado quando necessária e publica `/game_data`. Um detalhe relevante: o observer **só publica quando enxerga a bola** (com confiança mínima de 0,3).
2. **`/game_data` → Kalman.** O filtro estima posição, velocidade e aceleração da bola e dos robôs e publica `ball_predicted` e `robot_predicted`.
3. **Tudo → `strategy_node`.** A árvore de cada robô lê o estado do jogo, as predições e o comando do árbitro (que ela assina diretamente do Game Controller) e decide.
4. **`/robot_goal`.** As folhas de movimento publicam um alvo. Só republicam quando o alvo muda de forma relevante (mais de 2 mm ou cerca de 1° de orientação).
5. **D\*.** O planejador, a 10 Hz (40 Hz quando a bola está a menos de 40 cm do robô), calcula uma rota e a publica como `nav_msgs/Path`.
6. **Path follower.** A cada 50 ms (20 Hz), o controlador segue a rota, aplica controle proporcional, repulsão de contato e travas de área, e publica `/robot_commands`.
7. **Driver.** O driver de comunicação entrega o comando ao simulador ou ao rádio.

Além desse caminho principal existe um **canal de exceção**: as folhas que precisam de uma ação física especial (parar, chutar, girar) enviam um `RobotMotionOverride` direto ao controlador, que o executa em lugar de seguir a rota. O Capítulo 7 detalha esse mecanismo.

## Como o sistema é iniciado

Tudo é iniciado por um único arquivo de launch, `ssl-new.launch.py`, do pacote `oxebots_bringup`:

```bash
ros2 launch oxebots_bringup ssl-new.launch.py
```

O comportamento é controlado por argumentos. Os principais:

| Argumento | Valores | O que muda |
|---|---|---|
| `mode` | `grsim` (padrão), `ra`, `game` | Escolhe o driver de comunicação: simulador grSim, simulador ER-Force Ra, ou jogo real pelo rádio NRF24. |
| `command_mode` | `velocity` (padrão), `point` | Formato do comando enviado pelo rádio (velocidades locais ou ponto-alvo de trajetória). |
| `invert_sides` | `True`, `False` | Espelha o campo (`x = −x`, `y = −y`, `θ += π`). Por padrão é `True` apenas no modo `ra`. |
| `team_color` / `config_file` | `blue`, `yellow` / caminho | Escolhe o arquivo YAML de configuração do time. |
| `bt_xml` | nome de arquivo `.xml` | Substitui a árvore executada, sem editar o YAML. |
| `use_rviz` | `True`, `False` | Abre o RViz. |
| `match` | `True`, `False` | Sobe **os dois times** na mesma máquina, isolados por `ROS_DOMAIN_ID` (0 = azul, 1 = amarelo). |

O script `run_match.sh`, na raiz do workspace, é um atalho para uma partida simulada completa entre azul e amarelo: ele redireciona a execução para o *devcontainer* se estiver no hospedeiro e chama o launch com `match:=True`. O Apêndice E reúne os parâmetros e exemplos de comando.

### A configuração em YAML

Os arquivos `match_config*.yaml` centralizam os parâmetros. Para a estratégia, os mais importantes são:

- `is_yellow_team`: a cor do time (influencia as portas do simulador e o lado em que o time defende).
- `bt_xml_path`: o arquivo da árvore principal; por padrão, `master_strategy_carry.xml`.
- `execution_rate`: a frequência do tick da árvore, 60 Hz por padrão.
- `gc_topic`: o tópico de onde vem o comando do árbitro.

## O referencial de coordenadas

Todo o software compartilha o mesmo referencial de campo, ilustrado na {{fig:sistemas_de_coordenadas}}: origem no centro do campo, eixo x ao longo do comprimento, eixo y ao longo da largura, ângulos em radianos no sentido anti-horário a partir de +x. **Posições são mantidas em milímetros**; a conversão para metros acontece uma única vez, quando a folha de movimento monta o `RobotGoal`.

![O referencial de campo e as unidades do software](figuras/sistemas_de_coordenadas.png)

Um ponto exige atenção especial: o **lado do campo**. O referencial é fixo, mas o gol que cada time defende depende da cor (e do simulador). No código atual, o time amarelo defende o gol de +x e o time azul o de −x; a chave `my_goal_x` da blackboard guarda esse valor, calculado a partir da geometria do campo. O Capítulo 8 explica a inversão de lado, e o Capítulo 13 discute as armadilhas que o lado fixo cria para o jogo completo.
