# Do GoToPoint ao comando de roda

Mover um robô parece simples — "vá até aquele ponto" —, mas entre essa frase na árvore e o comando de velocidade no rádio existem várias etapas, cada uma com uma responsabilidade e com sua própria forma de falhar. Este capítulo percorre o caminho completo, esquematizado na {{fig:pipeline_movimento}}.

![As etapas entre a folha GoToPoint e o comando enviado ao robô](figuras/pipeline_movimento.png)

## A folha GoToPoint

`GoToPoint` é a folha mais usada do projeto (93 usos em 25 arquivos XML) e a principal "porta de entrada" do movimento. É uma ação assíncrona (*stateful*) que **pede** ao resto do sistema que leve o robô a um ponto, e depois **observa** se ele chegou.

### Portas

| Porta | Tipo | Padrão | O que faz |
|---|---|---|---|
| `robot_id` | `unsigned int` | — | Robô a comandar. Se diferente do robô desta instância, a folha **devolve SUCCESS sem fazer nada**. |
| `x`, `y` | `double` (mm) | — | Alvo, no referencial do campo. |
| `face_x`, `face_y` | `double` (mm) | ausentes | Ponto para onde o robô deve **olhar** ao chegar (a bola, um companheiro, o gol). Devem ser passados **juntos**. Sem eles, o robô olha para o gol adversário. |
| `tolerance` | `double` (mm) | −1,0 | Raio de chegada. **Se ≤ 0, a folha nunca devolve SUCCESS** (e o controlador não "trava" o robô perto do alvo). |
| `planner` | `string` | `"dstar"` | `"dstar"` (desvia de obstáculos) ou `"straight_line"` (reta). Qualquer outro valor usa o D\*. |
| `ball_contact_threshold_mm` | `double` | −1,0 | Se > 0, a folha **falha** se a bola chegar a menos desse valor do robô por mais de 150 ms — força a árvore a recalcular. |
| `ignore_area` | `bool` | `false` | Desliga a restrição de áreas de defesa (usado nos desafios técnicos). |
| `ball_side_check` | `bool` | `false` | Se verdadeiro, **falha** se o robô estiver, a menos de 600 mm da bola, do lado do gol (isto é, "na frente" da bola) por mais de 150 ms. |

### Ciclo de vida

**`onStart`** — ao ser ativada:
1. verifica se o `robot_id` pedido é o do próprio processo (senão, SUCCESS imediato);
2. lê `x` e `y`;
3. **aplica a restrição de área** (ver adiante);
4. calcula o ângulo de orientação desejado (para `face_*`, ou para o gol adversário);
5. publica um `RobotGoal` e devolve RUNNING.

**`onRunning`** — a cada tick:
1. relê `x` e `y` (eles podem mudar na blackboard) e, se o alvo se moveu mais de **2 mm** ou o ângulo de orientação mais de cerca de **1°**, **republica** o objetivo; caso contrário, não publica nada (o último objetivo continua valendo);
2. avalia os gatilhos de falha (`ball_contact_threshold_mm`, `ball_side_check`);
3. se `tolerance > 0`, verifica se **chegou**: distância menor que `tolerance` *e* erro de orientação menor que 0,15 rad (≈ 8,5°). Só então devolve SUCCESS;
4. senão, devolve RUNNING.

**`onHalted`** — **vazio**. A folha não cancela o objetivo ao ser interrompida. Isso é relevante: quando um ramo de maior prioridade assume, o `RobotGoal` anterior continua publicado e o controlador segue tentando alcançá-lo até que alguém publique outro objetivo ou um override de parada. No Capítulo 13 discutimos a consequência; no Capítulo 21 propomos a correção.

!!! note "O que significa SUCCESS aqui"
    `GoToPoint` devolve SUCCESS quando a **posição e a orientação** estão dentro da tolerância. Se o robô chega ao ponto mas não consegue alinhar com o `face_*` (por exemplo, porque o alvo de orientação está longe e instável), a folha continua RUNNING indefinidamente, sem erro. Há um log a cada segundo com a distância e o erro angular para facilitar o diagnóstico.

### A restrição de áreas

Antes de publicar, `GoToPoint` **corrige o alvo** para que o robô não seja mandado a lugares proibidos ({{fig:clamp_area}}):

- Todos os robôs, inclusive o goleiro, são impedidos de ir para a **área de defesa adversária**.
- Os robôs que **não** são o goleiro são impedidos de ir para a **área de defesa própria**; o goleiro, ao contrário, tem o alvo **limitado a ficar dentro** da própria área.
- A margem usada é de 100 mm além da linha da área.

![O alvo pedido pela árvore é empurrado para fora da área de defesa, com margem de 100 mm](figuras/clamp_area.png)

Esse mecanismo existe em **três camadas** independentes, o que dá segurança, mas também pode surpreender: (1) `GoToPoint` corrige o alvo; (2) o planejador D\* constrói uma "parede" no mapa e também corrige o alvo; (3) o controlador zera a componente de velocidade que levaria o robô para dentro da área. A opção `ignore_area=true` só desliga a camada 1.

## O objetivo do robô: RobotGoal

A comunicação entre a árvore e o resto do sistema é a mensagem `RobotGoal`, publicada em `/robot_goal` com QoS `transient_local` (guarda o último valor):

- `robot_id`: de quem é o objetivo;
- `pose`: posição em **metros** e orientação como quaternion (a conversão de mm para m acontece aqui);
- `planner_type`: `PLANNER_DSTAR` (0), `PLANNER_ASTAR` (1, hoje equivalente ao D\*) ou `PLANNER_STRAIGHT_LINE` (2);
- `disable_arrival_latch`: verdadeiro quando `tolerance ≤ 0`; instrui o controlador a **nunca** "travar" o robô por estar perto do alvo.

## O planejador D\* Lite

O `d_star_planner_node_<i>` calcula, a partir do objetivo, uma **rota livre de colisões**. Ele trabalha sobre uma **grade de ocupação** publicada pelo `game_observer_node` no tópico `/map`: uma grade de células de 5 cm que cobre o campo com 60 cm de margem, onde cada robô (aliado ou adversário, inflado em 150 mm) é marcado como obstáculo.

![Esquema da grade do D\*: obstáculos inflados, a "parede" da área de defesa e o caminho encontrado](figuras/dstar_grade.png)

Além do mapa, o planejador considera como **obstáculos dinâmicos** os aliados (raio de segurança de 0,20 m) e a **bola** (raio de 0,15 m — menor, para não bloquear o ponto de captura do atacante, que fica logo atrás da bola). A parede das áreas de defesa é desenhada no mapa com um valor especial (101), para que o planejador nunca a atravesse.

Pontos de funcionamento relevantes:

- **Replanejamento incremental**: se o objetivo é o mesmo, o D\* Lite apenas atualiza a rota quando o mapa muda — é a razão de ele ser eficiente.
- **Taxa**: 10 Hz normalmente; sobe para 40 Hz quando a bola está a menos de 0,4 m do robô, para que o caminho se atualize rápido o bastante para contornar a bola em vez de empurrá-la.
- **Falha**: se não encontra caminho, publica uma **rota vazia**, o que faz o controlador parar o robô.
- **Chegada**: quando o robô está a menos de 5 cm do alvo, publica uma rota vazia e descarta o objetivo.

### O modo linha reta

Quando `planner="straight_line"`, o planejador **ignora a grade** e interpola pontos a cada 10 cm entre o robô e o alvo. Há um único cuidado: se a bola estiver a menos de 0,20 m dessa reta (e não perto do próprio alvo), é inserido um ponto de desvio lateral. Esse modo é usado nos trechos finais do ataque, quando o robô *quer* chegar perto da bola; mas atenção: ele **não desvia de adversários nem de aliados**.

## O controlador de movimento

O `movement_calculation_node` (por robô, no processo `path_follower_node_<i>`) é o **único** escritor autorizado do tópico `/robot_commands`. A cada 50 ms ele decide o que o robô faz, em ordem de prioridade (veja a {{fig:override_modos}}):

1. **HALT**: velocidades zero.
2. **KICK**: executa a máquina de chute.
3. **ALIGN**: gira no lugar até olhar para a bola ou para um ângulo.
4. **Nenhum override**: segue a rota do D\*.

![A decisão do controlador: o override ativo (se houver) tem prioridade sobre o seguimento de rota](figuras/override_modos.png)

### Seguindo a rota: pure pursuit

O seguimento de rota usa o método **pure pursuit** omnidirecional ({{fig:pure_pursuit}}): o controlador procura, ao longo da rota, o primeiro ponto a mais de **100 mm** do robô (*lookahead*) e aponta a velocidade linear para ele. O módulo da velocidade é proporcional à distância até esse ponto (ganho 2,0), limitado por `max_linear_speed` (**1,0 m/s por padrão** no código). A orientação segue um controle proporcional (ganho 3,0, saturação em 4,0 rad/s, tolerância de 0,1 rad) em direção ao ângulo pedido pelo `RobotGoal` ou, na falta dele, ao ângulo da própria rota.

![Pure pursuit: o robô persegue um ponto da rota a uma distância fixa (lookahead)](figuras/pure_pursuit.png)

Alguns refinamentos importantes:

- **Prioridade ao alinhamento perto do alvo.** A menos de 100 mm do objetivo, a velocidade linear é multiplicada por `cos(erro angular)`: o robô gira antes de avançar, evitando empurrar a bola desalinhado.
- **Trava de chegada.** A menos de 10 mm do alvo final, o robô para e solta o controle angular, a menos que `disable_arrival_latch` esteja ativo (`tolerance ≤ 0`).
- **Repulsão de contato.** Só no modo D\*: se o robô chega a menos de 100 mm da bola (e só "desarma" a 130 mm), a velocidade é substituída por um afastamento proporcional. É uma proteção contra empurrar a bola acidentalmente.
- **Clamp de área.** Ao final, as componentes de velocidade que entrariam na área de defesa proibida são zeradas.

!!! warning "Não há limite de velocidade por fase de jogo"
    O único teto de velocidade é `max_linear_speed`, fixo. Em STOP o regulamento exige menos de 0,75 m/s, e o controlador atual **não** aplica esse limite. A proposta do Capítulo 17 (SafetyGate) resolve isso.

### O canal de override

Algumas ações não são "seguir uma rota" — são ações físicas especiais. Em vez de escreverem direto em `/robot_commands` (o que criaria uma disputa entre várias fontes), as folhas enviam um **pedido de modo** ao controlador por `/robot_motion_override`:

| Modo | Quem pede | Efeito |
|---|---|---|
| `MODE_HALT` | `Halt` | velocidades zero |
| `MODE_KICK` | `KickBall`, `Goalkeeper` | máquina de chute |
| `MODE_ALIGN_TO_BALL` / `MODE_ALIGN_TO_ANGLE` | `AlignToBall` | gira no lugar |
| `MODE_NONE` | qualquer folha, ao terminar | volta ao seguimento de rota |

O override é **"pegajoso"**: continua valendo até a folha liberá-lo (`MODE_NONE`). Como proteção contra uma folha que pare de enviar, o controlador o considera expirado após **200 ms** sem renovação. Isso tem duas consequências: ações que precisam do override devem **reenviá-lo a cada tick** (é o que `KickBall` e `Halt` fazem), e, se a árvore deixar de ticar, o robô **volta a seguir a última rota** em até 200 ms — e não para.

O controlador responde com `RobotMotionStatus` (`aligned`, `kick_fire_count`, modo ativo), que as folhas leem para decidir SUCCESS.

### A máquina de chute

O chute é uma pequena máquina de estados dentro do controlador ({{fig:maquina_chute}}). Ao receber `MODE_KICK` com o controlador ocioso e fora do tempo de espera, ele entra em **FIRING** por 200 ms: publica o `kick_speed` pedido e avança a 0,5 m/s **na direção em que o robô está olhando**, garantindo o contato. Ao fim da janela, incrementa `kick_fire_count` e entra em *cooldown* de 600 ms com o robô parado. A folha `KickBall` guarda o contador no início e devolve SUCCESS quando ele sobe; como cada tick reenvia o pedido, o cooldown evita que o chute vire uma "metralhadora".

![A máquina de chute do controlador](figuras/maquina_chute.png)

!!! tip "O chute é limitado em 3 m/s"
    `KickBall` limita `kick_speed` a 3,0 m/s antes de pedir o chute, o que atende ao limite de velocidade de bola da SSL-EL. Mesmo que o XML peça 6,5 (como em `master_strategy_carry.xml`), o valor efetivo é 3,0.

## O modo "ponto" do rádio

Para os robôs reais, o rádio NRF24 pode operar em dois formatos (`command_mode`): **velocidade** (o rádio envia as velocidades locais) ou **ponto** (o rádio envia um alvo cinemático e o robô fecha o laço localmente). No modo ponto, o `trajectory_setpoint_node_<i>` observa os comandos de velocidade e a predição do Kalman e publica `RobotTrajectorySetpoint`: um ponto futuro à frente do robô (velocidade × período de publicação × um fator de segurança, limitado por um teto), a velocidade desejada nesse ponto, o ângulo-alvo e a pose atual de referência. O firmware usa a pose de referência para corrigir o erro.

## Os drivers de comunicação

O último passo é o driver, escolhido por `mode`: o `grSim_controller_node` traduz `RobotCmd` para o protocolo do grSim (UDP); o `ra_controller_node` converte as velocidades globais em locais para o ER-Force Ra; e o `nrf24_bridge_node` serializa os comandos no protocolo binário do rádio (definido em `ssl_robot_protocol.bitproto`) e publica a telemetria dos robôs (bateria, erros) em `/robot_telemetry`.
