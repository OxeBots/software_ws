# Percepção, predição e geometria

Toda decisão da árvore parte de uma imagem do mundo. Este capítulo descreve como o software constrói essa imagem — o que o observador faz com os dados da visão, como o filtro de Kalman estima velocidades, como o campo é descrito e como o "lado" do campo é tratado — e quais são as limitações que a estratégia precisa levar em conta.

## O game_observer_node

O `game_observer_node` (pacote `oxebots_observers`) é o **tradutor central**: recebe as mensagens da ponte de visão e produz o que o resto do sistema consome.

### Entradas e saídas

| Entrada | Saída |
|---|---|
| `ssl_vision_bridge/vision_messages` (`VisionWrapper`) | `/game_data` (`GameData`): robôs aliados e adversários e bola, em mm |
| `gc_multicast_bridge/referee_messages` (`Referee`) | `/field_geometry` (`SSLGeometryData`, `transient_local`): dimensões do campo |
| | `/map` (`OccupancyGrid`, `transient_local`): grade de obstáculos para o D\* |
| | `ball_data` (`BallPosition`) e `robot_data` (`RobotPosition`): entrada do Kalman |

(O observer também assina o comando do árbitro, mas hoje apenas o registra em log.)

### O que ele faz com cada detecção

- **Unidades e orientação.** Converte metros para milímetros e o quaternion para o ângulo de guinada (*yaw*).
- **Aliados e adversários.** Conforme `is_yellow_team`, as detecções de robôs amarelos e azuis são separadas em "aliados" e "adversários". Os robôs são guardados em um mapa por identificador: cada nova detecção **atualiza** o identificador, sem apagar os outros.
- **Melhor bola.** Quando há várias bolas candidatas, usa a de maior confiança, e **só aceita** a detecção se a confiança for de pelo menos **0,3** (`min_ball_confidence`; o próprio código comenta que esse valor é um ponto de partida e deve ser calibrado com dados reais). Detecções piores são descartadas e a última posição boa é mantida.
- **Inversão de lado**, quando `invert_sides` está ativo (veja adiante).
- **Publicação.** O `GameData` é publicado **sempre que há uma bola aceita**. Em outras palavras: se a bola desaparece (oclusão, falha de visão), o observer *deixa de publicar* — inclusive a posição dos robôs.

### A geometria do campo

O observer converte a geometria recebida (`geometry[0]`) para milímetros e a publica. Como alguns simuladores (grSim) não preenchem a profundidade e a largura da área de defesa nem o raio do círculo central, o observer os **deduz** das linhas do campo e, em último caso, usa os valores regulamentares: para campos de até 5500 mm, área de **500 × 1350 mm** (SSL-EL) e círculo de 500 mm de raio. Assim, as árvores não precisam de números mágicos: tudo vem de `/field_geometry` e é copiado para a blackboard pelo `strategy_node`.

### A grade de obstáculos

A cada atualização, o observer constrói uma `OccupancyGrid` de resolução 0,05 m (`map_resolution`), com margem de 0,6 m ao redor do campo, marcando cada robô — aliado ou adversário — como um quadrado de raio `robot_inflation_radius` (150 mm). A grade é a única fonte de obstáculos "estáticos" do D\* (a bola e os aliados são tratados também como obstáculos dinâmicos pelo próprio planejador).

## A inversão de lado

Alguns simuladores (como o ER-Force Ra) colocam o time em lados do campo opostos aos esperados pelo software. Para não duplicar lógica, o observer pode **espelhar tudo** quando `invert_sides` está ativo: cada posição passa de `(x, y)` para `(−x, −y)` e cada ângulo de `θ` para `θ + π` ({{fig:inversao_lado}}).

![A inversão de lado: posições são espelhadas pelo centro e ângulos giram 180°](figuras/inversao_lado.png)

Por padrão, `invert_sides` é verdadeiro apenas em `mode:=ra`. É preciso distinguir dois conceitos que o código mistura em um só:

- **Cor do time** (`is_yellow_team`): decide quem é aliado e quem é adversário na visão e quais portas do simulador usar.
- **Espelhamento de coordenadas** (`invert_sides`): decide se o referencial é espelhado.

A blackboard guarda `is_yellow` como a **cor efetiva** (`is_yellow_team` XOR `invert_sides`) e calcula `my_goal_x` a partir dela. O efeito prático: independentemente de o simulador espelhar ou não, o gol que a estratégia chama de "meu" é `+L/2` para a cor efetiva amarela e `−L/2` para a azul.

## Predição: o filtro de Kalman

Os dados da visão chegam com ruído e sem velocidade. O `kalman_filter_node` (`oxebots_prediction`) resolve isso com filtros **dedicados**:

- **Bola**: modelo de 4 estados (posição e velocidade em x e y) com **atrito do carpete** (aceleração de frenagem configurável, 800 mm/s² por padrão) e detecção de chute (limiar de 80 mm), para reiniciar a estimativa quando a bola é chutada.
- **Robôs**: modelo cinemático de 6 estados (posição, velocidade e orientação com sua taxa).

A saída é publicada em `ball_predicted` (`BallPrediction`: posição, velocidade e aceleração) e `robot_predicted` (`RobotPrediction`). O principal consumidor é a folha `CalculateInterception` (Capítulo 9), que usa velocidade e aceleração para prever onde a bola estará. O `trajectory_setpoint_node` também usa a predição dos robôs.

!!! note "Predição do Kalman × diferença finita"
    O defensor não usa o Kalman: o `strategy_node` calcula a velocidade da bola por **diferença finita** entre duas leituras consecutivas de `/game_data` (`ball_vel`). É uma estimativa bem mais ruidosa que a do filtro. Unificar as duas fontes é uma melhoria natural (Capítulo 19).

## Limitações que a estratégia precisa respeitar

Reunindo o que vimos, a imagem do mundo que chega à árvore tem quatro limitações que não podem ser esquecidas:

1. **Sem carimbo de tempo.** `GameData` não carrega *timestamp*: não há como saber quão velha é uma leitura. Se a visão cair, a árvore continua a "ver" os últimos valores.
2. **Sem expiração de robôs.** Um robô que deixa de ser detectado permanece no mapa de aliados ou adversários com a última pose conhecida.
3. **Publicação condicionada à bola.** Sem bola aceita, nada é publicado.
4. **Leitura não atômica.** Valores relacionados na blackboard são atualizados e lidos em instantes ligeiramente diferentes.

Cada uma delas tem uma correção proposta na Parte IV, e a mais importante — o carimbo de tempo — é pré-requisito para a **supervisão de segurança** da Master Tree.
