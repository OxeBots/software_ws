"""Slides das Partes III, IV, V e dos apêndices."""


def partes_3_a_5(d):
    # ---------------- PARTE III
    d.divisor("Parte III", "O sistema atual",
              "Como cada peça funciona hoje, do nó de estratégia ao movimento, da percepção ao ataque, da defesa aos papéis — e uma lista honesta dos pontos que precisam de atenção.",
              "Cap. 6 strategy_node · 7 Movimento · 8 Percepção · 9 Ataque · 10 Defesa e goleiro · 11 Papéis · 12 Árvore mestre · 13 Pontos de atenção")

    d.fig("Cap. 6 — O strategy_node", "strategy_node_estrutura", [
        "Hospeda a **BT de um robô**; tick a **60 Hz**",
        "4 callbacks alimentam a **blackboard**: jogo, árbitro, geometria, papéis",
        "Registra **29 folhas** + todos os XMLs do diretório como subárvores",
        "A ação **`Halt`** pede `MODE_HALT` ao controlador (sempre SUCCESS)",
        "**Groot2** na porta 1667+id (azul) / 1677+id (amarelo)",
    ], larg=60, nota="O tick só começa com `GameData` **e** geometria; sem comando do árbitro, `gc_command = -1` e a árvore cai no jogo normal.")

    d.fig("Cap. 7 — Do GoToPoint ao comando de roda", "pipeline_movimento", [
        "`GoToPoint` é a folha mais usada: **93 usos** em 25 XMLs",
        "`tolerance ≤ 0` → **nunca** devolve SUCCESS",
        "SUCCESS = posição **e** orientação (0,15 rad) dentro da tolerância",
        "`onHalted` está **vazio**: o último objetivo continua valendo",
    ], larg=58)

    d.fig("Cap. 7 — Restrição de áreas", "clamp_area", [
        "O alvo é **corrigido** para fora da área adversária (todos) e da própria (exceto o goleiro), com margem de 100 mm",
        "Há **3 camadas**: `GoToPoint`, parede no mapa do D\\*, clamp de velocidade no controlador",
        "`ignore_area` só desliga a camada 1",
    ], larg=58)

    d.fig("Cap. 7 — O planejador D\\* Lite", "dstar_grade", [
        "Grade de **5 cm** publicada pelo observer; robôs inflados em 150 mm",
        "Aliados (0,20 m) e **bola (0,15 m)** como obstáculos dinâmicos",
        "**Replanejamento incremental**; 10 Hz, 40 Hz perto da bola",
        "Sem caminho → **rota vazia** → o robô pára",
        "`straight_line`: reta com desvio local da bola; **não** desvia de robôs",
    ], larg=58)

    d.duas("Cap. 7 — O controlador de movimento", "pure_pursuit", "override_modos",
           "Pure pursuit: lookahead de 100 mm", "Prioridade: HALT > KICK > ALIGN > rota", altura=330,
           itens=["Ganho linear 2,0, **`max_linear_speed` = 1,0 m/s**; alinhamento tem prioridade a < 100 mm do alvo",
                  "Override é **pegajoso** e expira em **200 ms** sem renovação"])

    d.fig("Cap. 7 — O chute e o modo \"ponto\" do rádio", "maquina_chute", [
        "**FIRING 200 ms**: `kick_speed` + avanço de 0,5 m/s na direção do heading",
        "**Cooldown 600 ms**: robô parado; evita \"metralhadora\"",
        "`KickBall` limita o pedido a **3,0 m/s** e devolve SUCCESS quando `kick_fire_count` sobe",
        "Rádio: modo **velocidade** ou **ponto** (`trajectory_setpoint_node`)",
    ], larg=62, altura=260)

    d.fig("Cap. 8 — Percepção, predição e geometria", "inversao_lado", [
        "`game_observer`: mm/rad, melhor bola (confiança ≥ 0,3), aliados × adversários, geometria com *fallbacks* EL",
        "**Inversão de lado** (`invert_sides`): (−x, −y, θ+π) — só para o simulador Ra",
        "**Kalman**: bola 4D com atrito do carpete; robôs 6D",
    ], larg=62, altura=260, nota=("vm", "Limitações: `GameData` **sem carimbo de tempo** · robôs que somem **não expiram** · sem bola, **nada é publicado** · leitura **não atômica**."))

    d.fig("Cap. 9 — O atacante: pontos calculados em torno da bola", "pontos_ataque", [
        "`UpdateBallPosition`: pré-chute a **400 mm** atrás da bola; prontidão com histerese 150/600 mm",
        "`CalculateInterception`: busca de **0,05 a 3 s** onde o robô alcança a bola prevista",
        "Pontos: pré-chute · captura (115 mm) · carga (+120 mm) · mira · **contorno** (600 mm lateral)",
    ], larg=70, altura=260)

    d.duas("Cap. 9 — A árvore do atacante", "arvore_atacante_atual", "arvore_approach_and_kick",
           "AttackerLogicLoop", "ApproachAndKick: Shoot › Realign › Carry", altura=390,
           itens=["Falhas **intencionais** (`ball_contact_threshold_mm`, `ball_side_check`) fazem a árvore **recomeçar do zero** com a posição real da bola"])

    d.fig("Cap. 9 — As quatro fases do atacante", "fases_atacante", [
        "**1** aproximação (D\\*) → **2** realinhar → **3** chutar (≤ 3 m/s)",
        "**4** conduzir quando a bola está na **nossa metade**",
        "`PrecisionKick` é legado: escreve direto em `/robot_commands` e **não limita** o chute",
    ], larg=60)

    d.duas("Cap. 10 — O defensor", "arvore_defensor_atual", "defensor_shadow_mark", "Bola no campo adversário → ShadowBall; posse deles → MarkOpponent",
           "ShadowBall (a) e MarkOpponent (b)", altura=380,
           itens=["Nunca entra na área (limite: área + 200 mm); **não disputa a bola**; as ações são síncronas e **sem `onHalted`**"])

    d.duas("Cap. 10 — O goleiro", "goleiro_estados", "arvore_goleiro_atual", "Linha de gol × sair e afastar", "Árvore", altura=330,
           itens=["Estado 2: **linha do gol**, 120 mm à frente, segue o y da bola",
                  "Estado 1: bola na área → pré-chute 200 mm atrás, avança e **chuta ≤ 3 m/s** para a lateral",
                  "Ainda **não** trata pênalti nem o limite de 10 s; id fixo `robot_id == 0`"])

    d.fig("Cap. 11 — Papéis dinâmicos", "custo_papel", [
        "`role_assigner` (global): **custo = 2,0·r + 1,0·(1 − cos θ)**",
        "**Histerese de custo 2,5** e **de tempo 2 s** evitam a troca-troca",
        "A árvore consome por `IsMyRole`; **o goleiro é fixo** (id 0)",
    ], larg=70, altura=260)
    d.fig("Cap. 11 — Histerese em ação", "histerese_papeis", [
        "O robô 2 só vira atacante quando supera o **desconto** do atual **e** o cooldown de 2 s permite",
        "Não conhece o estado de jogo nem robôs ativos",
    ], larg=62, altura=360)

    d.fig("Cap. 12 — A árvore mestre atual (master_strategy_carry.xml)", "slide_mestre_atual", None, altura=400,
          nota=("az", "`ReactiveFallback` na raiz: **a ordem dos ramos é a prioridade**. Jogo corrido é o que **sobra** quando nenhum ramo de bola parada casa."))

    d.duas("Cap. 12 — Subárvores de bola parada (atuais)", "arvore_kickoff_atual", "arvore_stop_atual", "KickOffTree: posições literais", "StopSubTree", altura=300,
           itens=["`PenaltyTree`, `FreeKickTree`, `OppSetPieceTree`; `CornerTree`/`ThrowInTree` dependem de flags **nunca escritas**"])

    d.tabela("Cap. 13 — Pontos de atenção do sistema atual", ["Ponto", "Consequência", "Resolvido em"], [
        ["TIMEOUT e BALL_PLACEMENT sem ramo", "robôs **jogam** com o jogo parado", "Caps. 15, 16, 18"],
        ["NORMAL_START sem contexto", "pênalti/kick-off executados pelo jogo corrido", "Cap. 15"],
        ["STOP com `KeepDistance` inoperante", "atacante age durante o STOP", "Caps. 17, 21"],
        ["Dados sem idade e sem watchdog", "robô se move com a visão caída ou a BT travada", "Cap. 17"],
        ["Sem teto 0,75 m/s; `PrecisionKick` sem clamp", "faltas de velocidade", "Cap. 17"],
        ["Coordenadas literais e lado fixo", "amarelo e azul se comportam diferente", "Caps. 15, 20"],
        ["Goleiro e papéis fixos", "sem goleiro alternativo nem degradação", "Caps. 19, 20"],
        ["`onHalted` vazio", "preempção não pára o movimento", "Caps. 17, 21"],
        ["Flags nunca escritas, IDs duplicados", "árvores mortas, registro ambíguo", "Caps. 18, 24"],
    ], nota=("az", "Não é crítica: é o **mapa preciso** do que resolver para jogar uma partida inteira."))

    d.fig("Cap. 13 — NORMAL_START sem contexto", "normal_start_sem_contexto", [
        "Ao chegar `NORMAL_START` (cmd 2) **nenhum** ramo de bola parada casa — o robô cai no jogo corrido",
        "No pênalti, todos os robôs entram em ação (violando o posicionamento)",
        "`ExecutePenalty` da `PenaltyTree` **nunca é alcançado**",
    ], larg=100, altura=250)

    d.fig("Cap. 13 — O lado do campo", "lado_literais", [
        "Os literais pressupõem lados **diferentes** entre si: kick-off → x>0; set-piece e free kick → x<0",
        "Para **qualquer** time, algum cai na metade errada — o defensor do kick-off ali é falta",
        "O árbitro informa `blue_team_on_positive_half`, que o software ignora",
    ], larg=64, altura=300)

    # ---------------- PARTE IV
    d.divisor("Parte IV", "A Master Tree de jogo completo",
              "A arquitetura proposta: um estado de jogo único e confiável, uma árvore mestre com prioridades claras, uma subárvore para cada situação regulamentar, papéis dinâmicos e contratos de dados.",
              "Cap. 14 Arquitetura · 15 GameState · 16 Master Tree v2 · 17 Segurança e STOP · 18 Reinícios · 19 Jogo corrido · 20 Papéis e blackboard · 21 Nós novos")

    d.cartoes("Cap. 14 — O que uma partida inteira exige", [
        ("Cobertura completa", "Cada comando, em cada estágio, tem comportamento definido — nenhum cai num *default* por acaso.", "v"),
        ("Segurança acima de tudo", "HALT para; dado ausente → estado seguro; limites valem **independentemente** da árvore.", "r"),
        ("Lado e cor", "Mesmo código para amarelo e azul; troca de lado no 2º tempo sem retrabalho.", "l"),
        ("Coordenação", "Papéis exclusivos, trocas estáveis, degradação com menos robôs."),
        ("Testabilidade", "Cada ramo e transição verificável sem robôs.", "p"),
    ], cols=3)

    d.fig("Cap. 14 — Arquitetura híbrida", "arquitetura_hibrida", [
        "**Mantém uma BT por robô** (o que já existe) e move para **serviços de equipe** o que é coletivo ou crítico",
        "**`referee_state_node`** ✦ → `GameState` · **`role_assigner`** ampliado ✦ · **observer com carimbo de tempo** ✦ · **Master Tree v2** ✦ · **SafetyGate** ✦",
    ], larg=100, altura=215, nota="Alternativas descartadas: **centralizada** (reescreve as folhas; um tick lento atrasa todos) e **só por robô** (cada árvore reconstrói o estado do jogo sozinha).")

    d.fig("Cap. 14 — As camadas de decisão", "camadas_decisao", [
        "BT escolhe por **prioridade** e reage; **não** guarda estado entre ticks",
        "Estado do árbitro, papéis e vigilância de dados ficam em **nós ROS 2**; a árvore **consulta**",
        "**Um dono por decisão**: fase → `referee_state_node`; papéis → `role_assigner`; ação → BT do robô; comandos → controlador",
    ], larg=60)

    d.fig("Cap. 15 — GameState e referee_state_node", "game_state_pipeline", [
        "Interpreta **uma vez, corretamente** e entrega pronto a todos os robôs",
        "`phase` · `restart_ctx` · `we_favored` · `speed_limit` · `ball_min_distance` · `our_goal_positive_x` · `stale` …",
        "**Descarta** repetições por `command_counter`",
        "**Lembra** o contexto do reinício (resolve o NORMAL_START)",
    ], larg=52)

    d.fig("Cap. 15 — Do comando à fase", "mapa_comando_fase", [
        "Legados normalizados: `INDIRECT` → FREE_KICK; `GOAL` → STOP",
        "**Pergunta aberta (H-01)**: que `command` o GC publica durante o *Run*? → capturar um log real (`log2bag`)",
    ], larg=55, altura=480)

    d.fig("Cap. 16 — Master Tree v2: um ramo por fase", "slide_mestre_v2", None, altura=400,
          nota=("az", "Cada ramo = `ReactiveSequence(guarda, subárvore)`. Quando **nada** casa, o robô **pára** — o oposto do mestre atual."))

    d.codigo("Cap. 16 — O padrão \"nosso ou deles\" e as guardas reativas",
             '<ReactiveSequence name="FreeKickBranch">\n  <CheckGameState phase="FREE_KICK"/>\n  <ReactiveFallback>\n    <ReactiveSequence>\n      <WeAreFavored/>\n      <SubTree ID="FreeKickOurTree"/>\n    </ReactiveSequence>\n    <SubTree ID="FreeKickTheirTree"/>\n  </ReactiveFallback>\n</ReactiveSequence>',
             ["A **cor do time não aparece** nos ramos: já virou `we_favored`",
              "Se a subárvore \"nossa\" **falha**, cai na \"deles\" (retirada segura)",
              "Guarda em `Sequence` comum **não é reavaliada** enquanto um filho roda; por isso **toda guarda é `ReactiveSequence`**"])

    d.fig("Cap. 16 — A árvore ao longo de uma sequência de fases", "preempcao_timeline", [
        "RUN → STOP → PREPARE_KICKOFF → KICKOFF → RUN",
        "O ramo anterior recebe `halt()` assim que o novo assume; **o GameState carrega todo o contexto**",
        "Três trajetórias verificadas: partida completa, troca de papéis e dado velho com ação em andamento",
    ], larg=100, altura=260)

    d.duas("Cap. 17 — Segurança: SafetyGuard e StopTree", "arvore_stop", "safety_gate", "StopSubTree proposta", "SafetyGate no controlador", altura=330,
           itens=["`SafetyGuard`: `IsDataFresh` falha (GC 500 ms · pose 150 ms · bola 300 ms) → `Halt`",
                  "STOP: `SetMotionLimit 0.75` → recua se a bola < 650 mm, senão `HoldPosition`"])

    d.cartoes("Cap. 17 — SafetyGate: segurança em duas camadas", [
        ("1  HALT zera a velocidade", "mesmo que haja override ou rota", "r"),
        ("2  Teto por fase", "0,75 m/s nos estados de parada; 1,5 m/s no jogo"),
        ("3  Watchdog de 500 ms", "sem objetivo/override → comandos zero; uma árvore silenciosa **pára** o robô", "l"),
        ("4  Chute ≤ 3,0 m/s", "para **qualquer** origem, inclusive folhas legadas", "v"),
    ], cols=4, nota=("az", "As regras 1 e 3 usam só informação **local** ao controlador: valem mesmo se o `strategy_node` morrer."))

    d.fig("Cap. 18 — Posições legais sem coordenadas literais", "slots_legais", [
        "`ComputeLegalSlot` calcula a posição de cada **slot** a partir de `own_goal_x` e `side_sign`",
        "Slots: `kickoff_kicker` · `kickoff_def` · `penalty_kicker` · `penalty_behind` · `freekick_support` · `wall` · `retreat`",
        "O mesmo slot vale para **os dois lados** do campo",
    ], larg=100, altura=250)

    d.duas("Cap. 18 — Kick-off e o cobrador", "arvore_prepare_kickoff", "arvore_restart_kicker", "PrepareKickoffOurTree", "RestartKickerTree + KickOnce", altura=300,
           itens=["`KickOnce`: chuta ≤ 3 m/s e confirma que a bola **se moveu 50 mm**; prazo de **10 s**",
                  "A mesma sequência de cobrança serve a kick-off, pênalti e free kick"])

    d.fig("Cap. 18 — Pênalti", "arvore_penalty_defesa", [
        "**Nosso**: cobrador atrás da bola sem tocar; demais **≥ 1 m atrás**; execução com chute direto ao gol",
        "**Deles**: `PenaltyKeeperLine` — goleiro **na linha de gol** até `WaitBallInPlay`; depois, goleiro normal",
        "O goleiro **não** sai da linha mesmo se a bola \"entrar na área\"",
    ], larg=34, altura=470)

    d.duas("Cap. 18 — Free kick e ball placement", "arvore_freekick", "arvore_ballplacement_deles", "FreeKickOurTree (substitui corner/throw-in/kick-in)", "BallPlacementTheirTree", altura=300,
           itens=["Do adversário: `wall` a ≥ 0,5 m da bola; ball placement dele → `AvoidPlacementCorridor` (margem 550 mm)",
                  "Ball placement **nosso** (`PlaceBall`, 30 s): recomendado como **pós-MVP**; a SSL-EL permite o *opt-out*"])

    d.duas("Cap. 19 — Jogo corrido e degradação", "arvore_normalplay", "degradacao_papeis", "NormalPlayTree", "Papéis com 3, 2 e 1 robô", altura=320,
           itens=["`HasRole` substitui `IsMyRole` + `IsRobotId`; robô sem papel **fica parado**",
                  "Goleiro: id do **árbitro**, modo `penalty_def`, `BallHeldTimer` (8 s), FAILURE sem dados",
                  "Defensor: Kalman no lugar da diferença finita; ataque sem `PrecisionKick`"])

    d.fig("Cap. 20 — Papéis ampliados e blackboard proposta", "blackboard_fluxo", [
        "`RoleAssignment`: **goalkeeper_id · attacker_id · defender_id · kicker_id · epoch · active_ids**",
        "**Cobrador travado** durante o reinício; histereses desligadas nele",
        "`refresh()` no início de **cada tick** → chaves consistentes entre si",
        "Idade dos dados: `gc_age_ms`, `pose_age_ms`, `ball_age_ms`",
        "**side_sign** e **own_goal_x** vêm do árbitro; `invert_sides` fica só para o simulador",
    ], larg=56)

    d.cartoes("Cap. 21 — Os 14 nós novos", [
        ("Condições (6)", ["`CheckGameState` · `WeAreFavored`", "`IsDataFresh` · `HasRole`", "`BallHeldTimer` · `WaitBallInPlay`"], "v"),
        ("Ações síncronas (3)", ["`ComputeLegalSlot`", "`ComputePlacementApproach`", "`SetMotionLimit`"]),
        ("Ações assíncronas (5)", ["`HoldPosition` · `KickOnce`", "`PlaceBall` · `PenaltyKeeperLine`", "`AvoidPlacementCorridor`"], "l"),
    ], cols=3, nota=("az", "**Adaptações**: `GoToPoint` (onHalted) · `KeepDistance` · `PrecisionKick` · `Goalkeeper` · `UpdateBallPosition` · controlador (SafetyGate) · `strategy_node` · `role_assigner` · observer/`GameData`."))

    # ---------------- PARTE V
    d.divisor("Parte V", "Implementação",
              "Como criar uma nova folha, como validar o comportamento do time sem robôs e como dividir o trabalho nas quatro semanas até uma versão jogável.",
              "Capítulo 22 · Tutorial de folha   |   Capítulo 23 · Testes   |   Capítulo 24 · Plano")

    d.fig("Cap. 22 — Tutorial: criando uma folha", "no_ros_vs_no_bt", [
        "**Nó ROS 2** = processo · **nó de BT** = objeto dentro da árvore, que usa o nó ROS do `strategy_node`",
        "Passos: definir → cabeçalho → implementação → **registrar** → **CMake** → XML → teste → simular e documentar",
        "Exemplo: **`HoldPosition`** (publica a pose atual; `onHalted` idempotente)",
        "Publisher × serviço × action: só use *action* se **outro processo** executa a tarefa",
    ], larg=48, altura=380)

    d.fig("Cap. 23 — A pirâmide de testes", "piramide_testes", [
        "Base: **validador estático** de XML (portas sem valor, IDs duplicados, subárvores) — o mais barato e valioso",
        "**Harness de semântica** da biblioteca na versão do container (4.10)",
        "Integração com `launch_testing`; **replay** de rosbags; falhas injetadas",
        "Topo: partidas completas simuladas",
    ], larg=52, altura=360)

    d.cartoes("Cap. 23 — Cenários e critérios de aceitação", [
        ("26 cenários (SC-01…26)", ["Sem GC → parado", "HALT/STOP/TIMEOUT", "Kick-off, pênalti, free kick: **dois lados**", "Ball placement, troca de lado, cartão", "`SIGSTOP` na BT → parado em 500 ms"]),
        ("Critérios (a calibrar)", ["HALT: v = 0 em **≤ 300 ms**", "STOP: |v| ≤ 0,75 m/s em ≥ 99%", "Chute ≤ 3,0 m/s em **100%**", "Dado velho → parado em ≤ 500 ms", "2 partidas de 5 min sem faltas por software"], "l"),
        ("Definição de pronto", ["Contrato documentado", "XML passa no validador", "Teste de comportamento e de `halt`", "Evidência de execução", "Catálogos atualizados"], "v"),
    ], cols=3)

    d.tabela("Cap. 24 — Frentes de trabalho e prioridades", ["Frente", "Escopo", "Tarefas"], [
        ["**GC**", "GameState, referee_state_node, lançamento", "G01–G06"],
        ["**MASTER**", "MainTreeEL, condições, observabilidade, limpeza", "A01–A06"],
        ["**DADOS**", "carimbo de tempo, refresh(), lado, fim das literais", "D01–D04"],
        ["**MOV**", "SafetyGate, GoToPoint, KeepDistance, PrecisionKick, D\\*", "M01–M06"],
        ["**ESTRAT**", "Stop, reinícios, placement, ataque, defesa", "E01–E10"],
        ["**GK · PAPEIS · TESTE · DOC**", "goleiro, atribuidor, validação, documentação", "K · P · T · X"],
    ], nota=("az", "**49 tarefas**: 25 P0 (segurança/legalidade), 20 P1 (MVP jogável), 4 P2 (evolução). Kick-off, free kick e pênalti são **obrigatórios**; ball placement próprio é opcional."))

    d.fig("Cap. 24 — Dependências e caminho crítico", "grafo_dependencias", [
        "Destravam o resto: **G01** (GameState), **D03** (blackboard e lado), **M01** (SafetyGate)",
        "Caminho crítico: G01 → G02 → A01 → E01 → A02 → E05 → E06/E07 → A06 → T07 → T09",
        "Um **único PR de interfaces** na semana 1 (msgs); `strategy_node.cpp` com um dono",
    ], larg=100, altura=230)

    d.fig("Cap. 24 — Cronograma de quatro semanas", "gantt_4_semanas", [
        "**S1** contratos e base segura · **S2** núcleo de jogo · **S3** integração e regras · **S4** ponta a ponta",
        "Pressupõe **≥ 5 pessoas**; ordem de corte: ball placement próprio → team client → ajuste de papéis → testes P1",
    ], larg=100, altura=330)

    d.cartoes("Riscos e como começar", [
        ("Riscos principais", ["Comando em *Run* desconhecido → capturar log real", "Mudança de mensagens → **um PR de interfaces**", "Semântica 4.6 × 4.10 → harness de testes", "Submódulos em branches de feature → fixar tags", "Escopo maior que a equipe → ordem de corte"], "r"),
        ("Como começar", ["Pegue uma tarefa da sua frente em `backlog.csv`", "Leia o contrato nos Caps. 15–21", "Feche contratos de interface na semana 1", "Implemente com **dublês**; escreva o teste junto", "Valide o XML; atualize o manual no mesmo PR"], "v"),
    ], cols=2)

    d.cartoes("Apêndices e material de apoio", [
        ("A · Glossário", "Termos do projeto e do regulamento"),
        ("B · Nós, mensagens e tópicos", "Catálogo das 29 folhas, mensagens e tópicos", "v"),
        ("C · Regras × arquitetura", "30 regras: cobertura hoje e componente responsável", "l"),
        ("D · XMLs propostos", "Mestre, STOP, reinícios, jogo corrido, ball placement", "p"),
        ("E · Parâmetros e execução", "Launch, YAML, portas de rede, parâmetros propostos", "g"),
        ("Anexos", "`backlog.csv` · `matriz-regras.csv` · `xml-proposto/`"),
    ], cols=3, nota=("az", "Manual completo: `docs/manual/Manual-Estrategia-OxeBots.pdf`  ·  Fontes e scripts: `docs/manual/`"))

    d.cartoes("Em resumo", [
        ("Hoje", "Um sistema que percebe, planeja, ataca e defende — mas com lacunas de **cobertura de comandos, segurança e lado**.", "g"),
        ("Proposta", "**GameState** único · **Master Tree** por fase · **SafetyGate** · papéis dinâmicos · posições calculadas.", "l"),
        ("Caminho", "4 semanas, 49 tarefas, contratos primeiro, **testes junto com o código**.", "v"),
    ], cols=3, nota=("az", "**Próximo passo:** fechar os contratos de interface (GameState, RoleAssignment, ComputeLegalSlot, KickOnce) e capturar um log real do Game Controller."))
