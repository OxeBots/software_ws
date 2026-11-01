"""Slides das Partes I e II."""


def partes_1_e_2(d):
    d.capa("Manual da Estratégia OxeBots",
           "Behavior Trees, arquitetura de jogo e implementação para a RoboCup Small Size League – Entry Level",
           "capa_arvore", "Apresentação do manual · 167 páginas, 24 capítulos, 5 apêndices")

    d.cartoes("O manual em uma página", [
        ("Parte I — A partida e o ecossistema", "O jogo que o software precisa jogar, as regras que afetam o código e a pilha de programas.  *Caps. 1–3*"),
        ("Parte II — Behavior Trees", "A teoria do zero e como a BehaviorTree.CPP a implementa: XML, nós, portas, blackboard.  *Caps. 4–5*", "v"),
        ("Parte III — O sistema atual", "Strategy node, movimento, percepção, ataque, defesa, goleiro, papéis, árvore mestre — e os pontos de atenção.  *Caps. 6–13*", "l"),
        ("Parte IV — A Master Tree de jogo completo", "GameState, árvore mestre por fase, SafetyGate, reinícios, papéis e blackboard, nós novos.  *Caps. 14–21*", "r"),
        ("Parte V — Implementação", "Tutorial de folha, testes, plano de 4 semanas.  *Caps. 22–24*", "p"),
        ("Apêndices", "Glossário, catálogo de nós e mensagens, regras × arquitetura, XMLs propostos, parâmetros.  *A–E*", "g"),
    ], cols=3, nota=("az", "Esta apresentação segue **a ordem do manual**; o que é didático (exemplos passo a passo, código completo) está lá, nos capítulos indicados."))

    # ---------------- PARTE I
    d.divisor("Parte I", "A partida e o ecossistema",
              "Antes das árvores: o jogo que o software precisa jogar e a pilha de programas que transforma imagens de câmera em movimento de robô.",
              "Capítulo 1 · Introdução   |   Capítulo 2 · A partida SSL-EL   |   Capítulo 3 · Visão geral do software")

    d.cartoes("Cap. 1 — O desafio: jogar uma partida inteira sozinho", [
        ("Duas entradas", ["**Imagens das câmeras** (SSL-Vision): onde estão bola e robôs", "**Comandos do árbitro** (Game Controller): em que estado o jogo está"]),
        ("Uma pergunta, 60 vezes por segundo", "*\"O que devo fazer agora?\"* — depende de comando, papel, bola, outros robôs e do regulamento.", "l"),
        ("Uma assimetria", "Errar uma jogada é aceitável. **Violar uma regra de segurança, não.** HALT precisa parar o robô — sempre.", "r"),
    ], cols=3, nota="Boa parte da arquitetura existe para que a **interrupção seja garantida**, e não apenas provável.")

    d.fig("Cap. 1 — As camadas do software", "visao_geral_camadas", [
        "**Decisão** (papéis + Behavior Tree) escolhe *aonde ir* e *o que fazer*",
        "**Planejamento** (D\\*), **controle** e **atuação** cuidam do *como*",
        "O manual percorre as camadas de baixo para cima (Parte III) e de cima para baixo (Parte IV)",
    ], larg=64)

    d.fig("Cap. 2 — O campo, a bola e os robôs", "campo_dimensoes", [
        "Área de jogo **4,5 × 3 m**; margem de 0,5 m",
        "Áreas de defesa **1,35 × 0,5 m**; círculo central Ø 1 m",
        "**3 robôs** por time; um pode ser o goleiro",
        "Robôs **totalmente autônomos**; sem dribbler",
        "Bola de golfe laranja, Ø 43 mm",
    ], larg=66)

    d.fig("Cap. 2 — Software compartilhado e etapas da partida", "linha_do_tempo_partida", [
        "**SSL-Vision**: câmeras compartilhadas, com ruído, atraso e falhas",
        "**Game Controller**: traduz o árbitro para mensagens de rede — origem do *comando*",
        "**Autoref**: detecta infrações e as reporta ao GC",
        "O **relógio pára** em STOP, HALT, preparações e ball placement: o robô passa muito tempo *não jogando*",
        "4 timeouts por jogo (420 s)",
    ], larg=60, altura=300)

    d.tabela("Cap. 2 — Os comandos do árbitro", ["Comando", "O que exige do robô"], [
        ["`HALT`", "ninguém se move nem toca a bola; 2 s para frear; sempre seguido de STOP"],
        ["`STOP`", "**< 0,75 m/s**, **≥ 0,5 m da bola**, sem manipulá-la"],
        ["`BALL_PLACEMENT_*`", "como STOP; quem posiciona leva a bola ao alvo em 30 s; o outro time fica ≥ 0,5 m do corredor"],
        ["`PREPARE_KICKOFF_*` / `PREPARE_PENALTY_*`", "ir para as posições do reinício"],
        ["`NORMAL_START`", "autoriza o kick-off **ou** o pênalti preparados"],
        ["`DIRECT_FREE_*`", "free kick: o favorecido bate; adversários ≥ 0,5 m (inclui lateral, escanteio, tiro de meta)"],
        ["`FORCE_START`", "ambos os times podem manipular a bola"],
        ["`TIMEOUT_*`", "equipes livres; robôs parados"],
    ], nota=("vm", "`NORMAL_START` é o **mesmo** comando para kick-off e pênalti: é preciso **lembrar** o contexto."))

    d.fig("Cap. 2 — STOP e BALL_PLACEMENT", "geometria_stop_placement", [
        "**STOP**: o robô que está a menos de 0,5 m da bola deve recuar; velocidade < 0,75 m/s",
        "**BALL_PLACEMENT**: a zona proibida tem formato de **estádio** em volta do segmento bola → alvo",
        "Na SSL-EL um time pode **optar por não posicionar** a bola",
    ], larg=70, altura=310)

    d.fig("Cap. 2 — Kick-off e pênalti", "geometria_kickoff_penalty", [
        "**Kick-off**: todos na própria metade, fora do círculo; só o **cobrador** pode entrar nele",
        "**Pênalti**: goleiro defensor **na linha de gol**; demais robôs **≥ 1 m atrás da bola**; a bola só vai rumo ao gol adversário",
        "Pênalti: se a bola ainda está em jogo após **10 s**, o jogo pára",
    ], larg=70, altura=310)

    d.fig("Cap. 2 — Free kick", "geometria_freekick", [
        "Adversários **≥ 0,5 m** da bola; um cobrador do favorecido",
        "Atacantes **≥ 0,2 m** da área adversária",
        "A bola entra em jogo ao se mover **0,05 m** ou após **10 s**",
        "Lateral, escanteio e tiro de meta **são free kicks** — não há comandos próprios",
    ], larg=48, altura=520)

    d.fig("Cap. 2 — A máquina de estados do jogo", "maquina_estados_gc", [
        "Três famílias: **Halted**, **Stopped**, **Running**",
        "Qualquer estado → `Halt` por HALT",
        "Há **mais estados do que comandos**: `Kickoff` não é um comando",
    ], altura=380, larg=100, nota=("az", "Por isso a arquitetura proposta (Parte IV) deriva uma **fase de jogo** em vez de reagir ao número do comando."))

    d.tabela("Cap. 2 — Faltas que o software pode (e deve) evitar", ["Regra", "Limite"], [
        ["Velocidade do robô em jogo", "≤ **1,5 m/s**"],
        ["Velocidade do robô em STOP", "≤ **0,75 m/s** (2 s de tolerância)"],
        ["Velocidade da bola após o chute", "≤ **3 m/s**"],
        ["Distância à bola em free kick / kick-off do adversário", "≥ **0,5 m**"],
        ["Proximidade da área adversária (STOP e free kick)", "≥ **0,2 m**"],
        ["Robô (não goleiro) na própria área", "proibido; tocar a bola ali = pênalti"],
        ["Bola retida na área de defesa (goleiro)", "≤ **10 s**"],
        ["Interferência no ball placement", "≥ **0,5 m** do corredor bola → alvo"],
    ], nota="Toda 3ª falta gera **cartão amarelo**: o número de robôs ativos pode mudar durante a partida.")

    d.cartoes("Cap. 2 — O que o software precisa garantir", [
        ("Segurança", ["Parar com **HALT**, sempre", "**0,75 m/s** e 0,5 m da bola em STOP", "Modo seguro **sem dados**"], "r"),
        ("Reinícios", ["Posicionar-se nos **dois papéis** (bate / defende)", "Lembrar o contexto de **NORMAL_START**", "Respeitar **áreas** de defesa"], "l"),
        ("Jogo", ["Chute ≤ **3 m/s**, robô ≤ 1,5 m/s", "Goleiro: ≤ 10 s e linha no pênalti", "**Adaptar-se** a cartões e goleiro ausente"], "v"),
    ], cols=3, nota=("az", "O **Apêndice C** relaciona cada regra do regulamento ao componente que a trata."))

    d.cartoes("Cap. 3 — O workspace e seus pacotes", [
        ("ssl_ros_bridge", "Pontes UDP → ROS 2 (visão e Game Controller)"),
        ("oxebots_interfaces", "Mensagens, serviços e protocolo do rádio", "v"),
        ("oxebots_observers", "game_observer: `/game_data`, geometria, mapa", "l"),
        ("oxebots_prediction", "Kalman: bola (com atrito) e robôs", "p"),
        ("oxebots_strategy", "**strategy_node (BTs)**, papéis, D\\*, controlador, folhas e XMLs", "r"),
        ("oxebots_comms", "Drivers: grSim, Ra, rádio NRF24", "g"),
        ("oxebots_bringup", "Launch e configuração YAML"),
        ("oxebots_trajectory_analysis", "Análise de rotas em Python (fora do jogo)", "g"),
    ], cols=4)

    d.fig("Cap. 3 — Os processos em execução", "arquitetura_processos", [
        "**Únicos da equipe**: pontes SSL, observer, Kalman, atribuidor de papéis, driver",
        "**Um conjunto por robô** (0, 1, 2): `strategy_node`, D\\*, path follower, setpoint",
        "**Cada robô tem a sua árvore e a sua blackboard** — não existe \"árvore do time\"",
    ], larg=100, altura=330, nota=("az", "Tópicos como `/robot_goal` e `/robot_commands` são **compartilhados**: cada mensagem carrega o id do robô."))

    d.fig("Cap. 3 — O caminho dos dados", "fluxo_dados", [
        "Visão ~60 Hz → observer → Kalman",
        "BT a **60 Hz** → `/robot_goal`",
        "D\\* a **10 Hz** (40 Hz perto da bola)",
        "Controlador a **20 Hz** → `/robot_commands`",
        "**Canal de exceção**: `override` (parar, chutar, alinhar)",
    ], larg=48)

    d.codigo("Cap. 3 — Como iniciar o sistema", "ros2 launch oxebots_bringup ssl-new.launch.py\n\n"
             "# mode:=grsim | ra | game        (driver de comunicação)\n# command_mode:=velocity | point  (rádio)\n# match:=True                     (azul × amarelo, domínios 0 e 1)\n# bt_xml:=<arquivo>.xml           (outra árvore)\n# team_color:=blue | yellow\n\n./run_match.sh                    # partida simulada completa",
             ["Um único launch sobe tudo: pontes, observer, Kalman, 3 conjuntos por robô, papéis e driver", "`invert_sides` é `True` por padrão **só** em `mode:=ra`", "Parâmetros em `match_config*.yaml` (Apêndice E)"])

    d.fig("Cap. 3 — O referencial de coordenadas", "sistemas_de_coordenadas", [
        "Origem no centro; **θ = 0 aponta para +x**; anti-horário",
        "Posições em **mm**; metros só no `RobotGoal` (conversão em um ponto único)",
        "O **lado de defesa** depende da cor e do simulador: `my_goal_x = ±L/2`",
    ], larg=100)

    # ---------------- PARTE II
    d.divisor("Parte II", "Behavior Trees",
              "A teoria necessária para ler, escrever e depurar as árvores do projeto, e a forma como a biblioteca BehaviorTree.CPP a coloca em prática.",
              "Capítulo 4 · Behavior Trees do zero   |   Capítulo 5 · BehaviorTree.CPP na prática")

    d.cartoes("Cap. 4 — Por que uma árvore e não uma máquina de estados", [
        ("Máquina de estados", ["Transições crescem rápido: *todo estado* precisa de uma saída para \"parado\"", "Difícil reaproveitar um pedaço"], "r"),
        ("Behavior Tree", ["Hierarquia: comportamentos compostos de comportamentos", "**A ordem dos irmãos é a prioridade**", "Reavaliação contínua → interrupção natural"], "v"),
        ("Ganhos práticos", ["Modularidade", "Reatividade", "Legibilidade: o desenho é a documentação", "Desenvolvimento em paralelo"], "l"),
    ], cols=3)

    d.fig("Cap. 4 — Anatomia de uma árvore", "bt_anatomia", [
        "**Condição**: pergunta ao mundo; sem efeito",
        "**Ação**: faz algo (mover, chutar, parar)",
        "**Controle**: decide qual filho executar e em que ordem",
        "**Decorador**: modifica um filho",
        "**Subárvore**: reuso por nome",
    ], larg=64)

    d.cartoes("Cap. 4 — O tick e os três resultados", [
        ("SUCCESS", "A tarefa foi concluída (ou a condição é verdadeira).", "v"),
        ("FAILURE", "A tarefa não pôde ser concluída (ou a condição é falsa).", "r"),
        ("RUNNING", "Ainda em andamento: precisa de mais ticks. É o que permite comportamentos que duram.", "l"),
    ], cols=3, nota=("az", "O tick é um **pulso de decisão** (60 por segundo no projeto). Latência de reação ≤ 1 período de tick (~17 ms) + processamento."))

    d.duas("Cap. 4 — Sequence e Fallback", "bt_sequence", "bt_fallback", "Sequence: faz A, depois B, depois C", "Fallback: tenta A, senão B, senão C",
           itens=["Ambos **têm memória**: retomam no filho em andamento, **sem reavaliar** os anteriores"], altura=420)

    d.duas("Cap. 4 — O problema da reatividade e os nós reativos", "bt_reactive_sequence", "bt_reactive_fallback",
           "ReactiveSequence: a guarda é reavaliada", "ReactiveFallback: prioridades reavaliadas", altura=380,
           nota=("vm", "Com `Fallback`/`Sequence` comuns, um **HALT pode passar despercebido** durante uma ação longa. Os reativos recomeçam do 1º filho **a cada tick**."))

    d.duas("Cap. 4 — Parallel e decoradores", "bt_parallel", "bt_decoradores", "Parallel (success=1): o 1º a concluir encerra", "Inverter · Retry · Repeat · Timeout · Delay · ForceSuccess",
           altura=430)

    d.fig("Cap. 4 — Preempção: a razão de ser de tudo isso", "bt_preempcao_halt", [
        "Tick N: a condição `HALT?` falha; o atacante segue em RUNNING",
        "Tick N+1: o comando virou HALT → o ramo de maior prioridade tem sucesso",
        "Os filhos de menor prioridade recebem **`halt()`**",
        "Acontece em **no máximo um tick**, sem depender de a ação \"colaborar\"",
    ], larg=52, altura=500)

    d.cartoes("Cap. 4 — Regra prática e ações assíncronas", [
        ("Que nó usar?", ["Guarda reavaliada → **ReactiveSequence**", "Escolha com preempção → **ReactiveFallback**", "Roteiro em ordem → **Sequence**", "Simultâneo → **Parallel**"], "v"),
        ("Síncrona × assíncrona", ["Síncrona: termina no mesmo tick", "Assíncrona: pode devolver RUNNING e precisa tratar **`halt`**"]),
        ("Regra de ouro", "**Nunca bloquear dentro de um tick.** Um tick travado impede a reação a um HALT.", "r"),
    ], cols=3)

    d.codigo("Cap. 5 — Duas camadas: XML e C++", '<BehaviorTree ID="MainTreeCarry">\n  <ReactiveFallback name="MasterStrategy">\n    <Sequence name="HaltBranch">\n      <CheckGCCommand expected="0"/>\n      <SubTree ID="HaltSubTree" _autoremap="true"/>\n    </Sequence>\n    ...\n    <Halt reason="idle"/>\n  </ReactiveFallback>\n</BehaviorTree>',
             ["**XML** = estrutura da árvore; **C++** = o que cada folha faz", "A **fábrica** liga os dois: `registerNodeType<GoToPointNode>(\"GoToPoint\")`", "As folhas são compiladas *dentro* do `strategy_node` — **não há plugin**", "Três tipos de folha: `ConditionNode` · `SyncActionNode` · `StatefulActionNode`"])

    d.fig("Cap. 5 — O ciclo de vida de uma ação assíncrona", "ciclo_stateful_action", [
        "`onStart()` no 1º tick; `onRunning()` nos seguintes",
        "`onHalted()` quando o **pai interrompe** — hora de limpar (soltar override, parar de publicar)",
        "`onHalted` deve ser **rápido e idempotente**",
    ], larg=100)

    d.fig("Cap. 5 — Portas e blackboard", "fluxo_blackboard_subtree", [
        "**Porta** = atributo XML (`x=\"1000\"` ou `x=\"{ball_x}\"`)",
        "**Blackboard** = memória da árvore; cada `SubTree` tem a sua",
        "`_autoremap` copia as chaves que **já existem** no pai",
        "Folhas leem a blackboard **raiz** para atravessar subárvores",
    ], larg=58, nota=("vm", "**Porta de entrada sem atributo e sem padrão = erro.** A biblioteca *não* lê uma chave de mesmo nome. Declare o padrão como `\"{chave}\"`."))
