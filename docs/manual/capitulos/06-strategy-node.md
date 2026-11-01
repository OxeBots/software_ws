<!-- parte: Parte III — O sistema atual | Como cada peça do sistema funciona hoje, do nó de estratégia ao movimento, da percepção ao ataque, da defesa aos papéis, e uma lista honesta dos pontos que precisam de atenção. -->
# O strategy_node

O `strategy_node` é o processo que hospeda a Behavior Tree de um robô. Ele faz três coisas: mantém a **blackboard** sempre atualizada com o que o mundo informa, **registra** todas as folhas e subárvores na fábrica e **ticka** a árvore a 60 Hz. Este capítulo percorre o seu código na ordem em que ele acontece. O arquivo é `oxebots_strategy/src/strategy_node.cpp`.

![A estrutura interna de um strategy_node: duas linhas de execução compartilham a blackboard](figuras/strategy_node_estrutura.png)

## Parâmetros

O nó declara os seguintes parâmetros ROS 2 (valores padrão entre parênteses; os YAMLs de `oxebots_bringup` sobrescrevem alguns):

| Parâmetro | Padrão | Significado |
|---|---|---|
| `bt_xml_path` | `""` | Arquivo da árvore. Vazio: usa `master_strategy.xml`. Só o nome (sem `/`): procura em `behavior_trees/` do pacote. |
| `is_yellow_team` | `false` | Cor do time. |
| `invert_sides` | `false` | Espelhamento do campo (simulador Ra). A cor "efetiva" é `is_yellow_team` XOR `invert_sides`. |
| `robot_id` | `1` | Identificador do robô que este processo controla. |
| `execution_rate` | `60.0` | Frequência do tick (Hz). |
| `gc_topic` | `/gc_multicast_bridge/referee_messages` | Tópico do comando do árbitro. |
| `possession_distance` | `220.0` | Distância (mm) usada para decidir se o adversário "tem a bola". |

Cada robô é iniciado por `strategy.launch.py` com o seu próprio `robot_id` (0, 1, 2) e o mesmo arquivo de configuração.

## O que o nó assina e publica

| Direção | Tópico | Tipo | Para quê |
|---|---|---|---|
| assina | `/role_assignment` | `RoleAssignment` | quem é atacante e quem é defensor |
| assina | `game_data` | `GameData` | poses de robôs e posição da bola |
| assina | `gc_topic` | `ssl_league_msgs/Referee` | comando, estágio e ponto designado do árbitro |
| assina | `/field_geometry` | `SSLGeometryData` (transient_local) | dimensões do campo |
| publica | `/robot_motion_override` | `RobotMotionOverride` | pedido de parada (usado pela ação `Halt`) |

As **folhas** (`GoToPoint`, `KickBall`, `Goalkeeper`…) criam seus próprios publicadores e assinantes **usando este mesmo nó ROS 2** (ele é passado a elas no registro). Por isso o `strategy_node` é, ao mesmo tempo, o "dono" de várias dezenas de publicadores — um por uso de folha no XML.

## A blackboard: o que é escrito e por quem

Em `setup_blackboard()`, antes de qualquer dado chegar, o nó cria as chaves com valores iniciais. Em seguida, quatro *callbacks* a mantêm atualizada:

### Dados do jogo (`game_callback`)

A cada `GameData`, o nó:

- escreve a pose do próprio robô (`robot_x`, `robot_y`, `robot_yaw`);
- calcula a **velocidade da bola** por diferença finita entre duas leituras consecutivas (`ball_vx`, `ball_vy`) — uma estimativa ruidosa, usada pelo defensor;
- escreve a bola como `ball_x`, `ball_y`, `ball` (`Pose2D`) e `ball_vel` (`Vector2D`);
- calcula `opponent_controlling` (**posse do adversário**): verdadeiro quando o robô adversário mais próximo da bola está a menos de `possession_distance` e **pelo menos 30 mm mais perto** do que o aliado mais próximo.

### Comando do árbitro (`gc_callback`)

A cada mensagem do GC, o nó escreve `gc_command` (inteiro cru), `gc_stage` e o ponto designado (`designated_x`, `designated_y`, em mm). Ele também calcula `is_free_kick`, verdadeiro quando o comando é `DIRECT_FREE` (8 ou 9) **para a nossa cor**. Nenhum outro tipo de comando é pré-processado: as árvores comparam `gc_command` com números.

### Geometria (`geometry_callback`)

Com a geometria oficial, o nó escreve `field_length`, `field_width`, `penalty_area_depth/width`, `goal_width`, `center_circle_radius` e, importante, `my_goal_x` e `opponent_goal_x`. O gol próprio é calculado pela cor efetiva: **amarelo defende +x, azul defende −x** (`my_goal_x = ±field_length/2`).

### Papéis (`role_callback`)

Escreve `attacker_id` e `defender_id` e `is_attacker`. Antes da primeira mensagem do atribuidor de papéis, os valores iniciais são `attacker_id = 2` e `defender_id = 1`.

!!! note "O tick só começa com dados"
    O laço principal só ticka a árvore quando já chegaram pelo menos um `GameData` **e** a geometria do campo. Enquanto isso, loga a cada 5 s que está aguardando. O comando do árbitro, porém, **não** é pré-requisito: se ele nunca chegar, `gc_command` permanece `-1` e a árvore cai no ramo de jogo normal (veja o Capítulo 13).

## O registro das folhas

No método `init()`, o nó:

1. resolve o caminho da árvore (`bt_xml_path`);
2. configura o contexto de controle usado pelas folhas defensivas (`configureDefenderController`);
3. registra as **29 folhas**: 18 classes de movimento/estratégia (`GoToPoint`, `KickBall`, `AlignToBall`, `UpdateBallPosition`, `CalculateInterception`, `IsBallClose`, `Goalkeeper`, `PrecisionKick`, `GoalLineDefend`, `IsBallInArea`, `IsBallInOurHalf`, `LateralClear`, `PositionBisector`, `SmotherSave`, `CalculateKickOffPose`, `KeepDistance`, `AimAt`, `HasLineOfSight`), 5 de defesa (`IsBallInOpponentField`, `IsOpponentControllingBall`, `ShadowBall`, `MarkOpponent`, `GoToClamped`), 5 condições simples em *lambda* (`IsValueTrue`, `IsThisNodeID`, `IsMyRole`, `CheckGCCommand`, `IsRobotId`) e a ação `Halt`;
4. registra **todos os outros arquivos `.xml`** do diretório como subárvores (falhas viram apenas aviso no log);
5. cria a árvore principal a partir do arquivo escolhido, com a blackboard do robô;
6. inicia o publicador do Groot2 (porta 1667 + id no azul, 1677 + id no amarelo).

O catálogo completo de folhas, com portas e comportamento, é o Capítulo 7 e o Apêndice B.

### A ação `Halt`

Registrada como *lambda*, a ação `Halt` é a forma padrão de "deixar o robô parado". Ela publica um `RobotMotionOverride` com `MODE_HALT` para o controlador, registra (a cada 2 s) o motivo (`reason`) e **devolve sempre SUCCESS**. Como o override expira em 200 ms se não for renovado, `Halt` precisa ser ticada **a cada tick** para manter o robô parado — o que acontece naturalmente, porque ela é folha síncrona dentro de um ramo reativo.

## O laço principal

O `main()` cria um executor multithread para as *callbacks* do ROS 2 em uma *thread* separada, e o laço de tick roda na *thread* principal:

```cpp
while (rclcpp::ok()) {
  if (has_data_ && has_geometry_) tree_.tickOnce();
  rate.sleep();   // 60 Hz
}
```

O resultado dessa arquitetura de duas linhas de execução (figura acima) é que a árvore sempre lê dados "do último instante", mas **sem garantia de consistência entre chaves** e **sem informação de idade**: se a visão parar de publicar, os valores na blackboard simplesmente deixam de mudar — a árvore não percebe. Esse ponto é o tema central do Capítulo 17.

## Resumindo

O `strategy_node` é um adaptador fino: converte mensagens ROS 2 em chaves de blackboard, expõe as folhas à árvore e ticka. Toda a inteligência está nos arquivos XML e nas folhas. Para estender o comportamento — por exemplo, para a Master Tree de jogo completo — as mudanças naturais são: trocar a leitura direta do árbitro por um estado de jogo pré-processado, ler a idade dos dados e passar a registrar as folhas novas.
