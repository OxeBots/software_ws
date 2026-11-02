# Instruções para agentes de IA — projeto OxeBots (`software_ws`)

**Versão para agentes com acesso ao repositório e aos documentos** (Claude Code, Cursor, Copilot Agent, Aider e similares).

> **Como usar.** Este arquivo é escrito para ser lido por um agente no início de **toda** sessão. Para que seja carregado automaticamente, copie-o (ou aponte para ele) na raiz do workspace com o nome que a sua ferramenta espera: `CLAUDE.md` (Claude Code), `AGENTS.md` (Codex/Cursor/outros) ou `.github/copilot-instructions.md`. Para quem usa um chat **sem** acesso a arquivos, existe a versão `INSTRUCOES-AGENTE-NAVEGADOR.md`, nesta mesma pasta.

---

## 1. O projeto em 60 segundos

O **OxeBots** é o time de futebol de robôs da UFBA na **RoboCup Small Size League – Entry Level (SSL-EL)**. Este repositório (`software_ws`) é um *workspace* **ROS 2** (Jazzy, no devcontainer) que reúne, como **submódulos Git**, todos os pacotes do software: percepção, predição, estratégia, controle e comunicação com os robôs.

- **3 robôs por time**, totalmente autônomos. O software recebe imagens de câmera (SSL-Vision) e **comandos do árbitro** (Game Controller) e decide, 60 vezes por segundo, o que cada robô faz.
- A decisão é feita por **Behavior Trees (BehaviorTree.CPP 4.x)**: **uma árvore por robô**, executada pelo processo `strategy_node`. Este é o **foco principal do trabalho**.
- O time está construindo, em ~4 semanas, uma versão capaz de **jogar uma partida inteira** respeitando o regulamento. A arquitetura proposta (Master Tree v2, `GameState`, SafetyGate…) está documentada, **mas em grande parte ainda não implementada**.
- O texto de referência completo é o **Manual da Estratégia OxeBots** (`docs/manual/`). **Leia o capítulo relevante antes de agir** (seção 7).

---

## 2. Como você deve agir

### 2.1 Postura

1. **Leia antes de escrever.** Abra o arquivo inteiro que vai alterar, busque (`grep`) todos os usos do símbolo, do ID XML, do tópico ou da chave de blackboard, e só então proponha a mudança.
2. **Em caso de dúvida, pergunte.** É sempre melhor uma pergunta curta do que uma alteração errada em um sistema que controla robôs e é editado por várias pessoas ao mesmo tempo. Em particular, **pergunte em que parte do projeto a pessoa está trabalhando** (seção 5) antes de qualquer alteração não trivial.
3. **Faça a menor mudança que resolve o problema.** Sem refatorações "de passagem", sem renomear, sem reformatar arquivos inteiros, sem "melhorar" código vizinho. Mudanças pequenas são revisáveis e não geram conflito com o trabalho dos colegas.
4. **Seja honesto sobre o que foi verificado.** Separe sempre: *li o código*, *analisei*, *executei*, *não verifiquei*. Nunca diga que algo compila, passa ou funciona se você não o executou. Hipóteses devem ser rotuladas como hipóteses.
5. **Nunca invente.** Não invente nomes de tópicos, mensagens, campos, portas de nó, parâmetros, IDs de árvore ou comandos do árbitro. Se não estiver no código ou nos documentos, diga que não encontrou.
6. **Distinga o que existe do que está proposto.** A Parte IV do manual descreve nós e componentes **que ainda não existem** (`CheckGameState`, `ComputeLegalSlot`, `referee_state_node`…). Não os use em XML ou código como se estivessem registrados.
7. **Responda em português do Brasil**, no tom técnico e direto dos documentos do projeto. Comentários de código seguem o idioma do arquivo (a maioria está em português).

### 2.2 Regras invioláveis

| # | Regra | Por quê |
|---|---|---|
| 1 | **Não compile nem teste o workspace por iniciativa própria** (`colcon build`, `colcon test`, `./build.sh`, `cmake`…). O time compila **sozinho, dentro do devcontainer**. Ao terminar uma alteração, pare em "aqui está o que mudou". Só compile se a pessoa **pedir explicitamente naquele turno**. | `build/` e `install/` foram gerados no caminho do container (`/software_ws`); usá-los a partir do host dá erro de diretório-fonte do CMake. O time já pediu que isso **nunca** seja feito sem pedido. |
| 2 | **Não rode `ros2 launch`, simulações ou nós** sem pedido. Sugira o comando para a pessoa executar. | Roda no devcontainer, com portas e domínios ROS específicos. |
| 3 | **Não faça `git commit`, `push`, `merge`, `rebase`, `reset`, `checkout` de outra branch nem `stash` sem pedido explícito.** Nunca use `--force`, `git add -A`/`git add .`, `--no-verify`. Ao commitar a pedido, adicione só os arquivos que você alterou. | O repositório tem submódulos e várias pessoas trabalhando em branches diferentes. |
| 4 | **Não altere ponteiros de submódulo** (`src/*` como submódulo) nem faça `git submodule update`. Cada pacote em `src/` é um **repositório separado**; uma mudança precisa ser commitada no submódulo, e só depois o ponteiro do `software_ws` é atualizado — decisão da pessoa. | Ponteiros apontam para *branches de feature*; mexer neles quebra o trabalho dos outros. |
| 5 | **Nunca enfraqueça uma proteção de segurança ou regulamentar** (clamp de área, limite de velocidade, limite de chute de 3 m/s, HALT/STOP, restrições de distância) sem **pedido explícito e discussão**. | O robô é físico; violar uma regra gera falta, cartão ou dano. |
| 6 | **Não edite arquivos gerados**: `build/`, `install/`, `log/`, `compile_commands.json`, `*.html`/`*.pdf` do manual (são regerados por scripts). | São artefatos. |
| 7 | **Não renomeie** IDs de árvore, tags de nó (`registerNodeType`), tópicos, mensagens, parâmetros ou chaves de blackboard sem listar **todos** os usos e obter confirmação. | Quebra silenciosa em XMLs, YAMLs e outras folhas. |
| 8 | **Não altere mensagens (`.msg`/`.srv`) ou o protocolo do rádio** sem alinhar com a equipe: obrigam a recompilar `oxebots_interfaces` e **todos** os pacotes dependentes, e invalidam *rosbags*. | Custo alto e efeito em todas as frentes. |
| 9 | **Não apague árvores legadas** (`master_strategy.xml`, `simple_attack.xml`, `test_*`, desafios técnicos…) nem "limpe" código morto sem confirmar. | Algumas servem a testes e desafios da equipe. |
| 10 | **Não exponha nem altere credenciais, IPs de rede, `net_interface_address` ou arquivos de configuração locais** (o `match_config.yaml` costuma ter um IP local não versionado). | Configuração da máquina de cada pessoa. |

### 2.3 Cuidados técnicos que já custaram caro

- **Orientação perto do alvo.** Nunca defina a orientação-alvo de um robô como "olhar para o ponto X" quando X está **muito perto** do destino (por exemplo, olhar para a bola no ponto de captura, a ~115 mm dela). O ângulo de marcação varia com ~1/distância e o ruído vira rotações enormes: o robô gira, anda de costas e não converge. Mantenha a orientação voltada a algo **longe e estável** (o gol adversário) durante a translação, e só corrija em direção ao alvo próximo com um passo de alinhamento dedicado, parado, com timeout.
- **Um único escritor de `/robot_commands`.** Apenas o `movement_calculation_node` deve publicar nele. Folhas pedem ações por `/robot_motion_override`; não publique comandos direto (o legado `PrecisionKick` faz isso e é um problema conhecido).
- **Porta de entrada sem atributo e sem valor padrão é erro.** Na BehaviorTree.CPP, `getInput` falha se a porta não está no XML e não tem padrão — a biblioteca **não** lê uma chave da blackboard de mesmo nome. Ao criar uma folha, dê padrão `"{chave}"` às portas que fazem sentido.
- **Nunca bloquear dentro de um tick** (sleep, espera de serviço, laço longo). Folhas assíncronas devolvem RUNNING.
- **`onHalted()` precisa ser rápido e idempotente.** E lembre que `GoToPoint::onHalted()` hoje é vazio: interromper um `GoToPoint` **não** cancela o último `RobotGoal`.
- **Lado do campo.** O gol próprio é `my_goal_x = +L/2` (cor efetiva amarela) ou `−L/2` (azul). **Não escreva coordenadas literais com sinal fixo** em XML novo.

---

## 3. Trabalho em grupo

O repositório é trabalhado por várias pessoas em paralelo, cada uma em uma *frente*. Você é mais um colaborador — **nunca o único**.

1. **Descubra quem mexe no quê.** Pergunte qual é a tarefa (`TASK-ID` do `docs/manual/anexos/backlog.csv`, se houver), qual é a branch e se mais alguém está editando os mesmos arquivos.
2. **Arquivos de alto risco de conflito** — mexa com cuidado extra e avise a pessoa de que eles são compartilhados:
   - `src/oxebots_strategy/src/strategy_node.cpp` (registro de nós, blackboard, callbacks);
   - `src/oxebots_strategy/behavior_trees/master_strategy_carry.xml` (a árvore mestre em uso);
   - `src/oxebots_interfaces/msg/*.msg` (mensagens);
   - `src/oxebots_strategy/src/movement_calculation.cpp` (controlador, único escritor de comandos);
   - `src/oxebots_bringup/launch/ssl-new.launch.py` e `config/*.yaml`;
   - `src/oxebots_strategy/CMakeLists.txt` (lista de fontes do `strategy_node`).
3. **Um arquivo novo por árvore nova.** Para não gerar conflito, não acrescente subárvores novas dentro de arquivos existentes; crie `behavior_trees/<nome>.xml`.
4. **Contratos de interface primeiro.** Antes de implementar algo que dois lados usam (mensagem, porta de folha, chave de blackboard), explicite o contrato e confirme com a pessoa. O manual (Cap. 20 e 21) já traz contratos propostos.
5. **Mudanças pequenas e atômicas** — uma ideia por alteração, fáceis de revisar e de reverter. Diga na resposta quais arquivos tocou e quais **não** tocou de propósito.
6. **Não "arrume" o trabalho alheio.** Se encontrar um defeito fora do escopo, **relate** em vez de corrigir (use a lista de pontos de atenção do Cap. 13 do manual para saber se já é conhecido).
7. **Deixe a documentação em dia no mesmo trabalho**, quando a mudança afetar o catálogo de folhas, as árvores ou as interfaces (`docs/manual/`, Apêndice B). Se você não puder atualizá-la, avise.

---

## 4. Seu primeiro passo: situar-se (e perguntar)

Em **toda sessão nova**, antes de propor ou editar qualquer coisa, descubra o contexto. Faça estas perguntas (todas de uma vez, curtas), adaptando ao que a pessoa já disse:

1. **Em que parte do projeto você está trabalhando agora?** (percepção / estratégia–árvores / movimento–controle / comunicação–rádio / papéis / goleiro / testes / documentação / infraestrutura)
2. **Se for estratégia: em qual árvore e em qual ramo?** (por exemplo, `master_strategy_carry.xml` → `AttackerRole`; `defender_tree.xml`; `kick_off.xml`; uma subárvore nova da Master Tree v2…)
3. **É uma tarefa do backlog?** Qual o `TASK-ID` (ex.: `E05`, `M03`) ou a descrição?
4. **Qual é o objetivo observável?** (o que o robô deve fazer ou deixar de fazer, em que situação de jogo/comando do árbitro)
5. **Onde roda?** grSim, ER-Force Ra ou robô real? Time **azul**, **amarelo** ou os dois?
6. **Qual branch e qual versão do código** (commit)? Alguém mais está mexendo nos mesmos arquivos?
7. **O que você já tentou / viu?** (log, tela do Groot2, comportamento no simulador)

Com a resposta, consulte a tabela abaixo para saber **o que ler primeiro, onde mexer e que cuidados tomar**.

| Se a pessoa está trabalhando em… | Leia primeiro (manual) | Onde mexer (arquivos) | Cuidados específicos |
|---|---|---|---|
| **Uma árvore XML existente** (ataque, defesa, kick-off, pênalti…) | Caps. 4, 5, 9–13 | `src/oxebots_strategy/behavior_trees/<arvore>.xml` | Guarda de ramo reativa; ordem = prioridade; portas sem padrão; coordenadas sem sinal fixo; **não** quebrar o `master_strategy_carry.xml` |
| **A Master Tree v2 / uma subárvore nova de fase** | Caps. 14–18, Apêndice D | novo `behavior_trees/<nome>.xml`; `anexos/xml-proposto/` | Muitos nós citados **não existem ainda**; use só nós registrados ou implemente-os antes |
| **Uma folha (nó C++) nova ou alterada** | Caps. 5, 21, 22; Apêndice B | `src/oxebots_strategy/include/oxebots_strategy/*.h`, `src/*.cpp`, **registro em `strategy_node.cpp`**, **`CMakeLists.txt`** | `onHalted` idempotente; falhar alto; sem bloqueio; thread-safety (callbacks × tick); não publicar em `/robot_commands` |
| **`GoToPoint`, D\*, controlador, chute** | Cap. 7 | `go_to_point_node.cpp`, `d_star_planner.cpp`, `movement_calculation.cpp` | Três camadas de clamp de área; override com TTL de 200 ms; lição da orientação perto do alvo; **nada de enfraquecer limites** |
| **Papéis** (atacante/defensor/goleiro/cobrador) | Caps. 11, 19, 20 | `src/oxebots_strategy/src/role_assigner_node.cpp`, `strategy_node.cpp` (`role_callback`) | Mudar a mensagem `RoleAssignment` é mudança de interface (alinhar) |
| **Goleiro** | Caps. 10, 18 (pênalti), 19 | `goalkeeper_node.cpp`, `behavior_trees/goalkeeper_tree.xml` | Regras de pênalti e de 10 s; id fixo `robot_id == 0` hoje |
| **Estado do árbitro / `GameState` / fases** | Caps. 2, 15, 16 | hoje: `gc_callback` em `strategy_node.cpp`; proposto: `referee_state_node` (novo) | `NORMAL_START` não identifica kick-off × pênalti; `TIMEOUT`/`BALL_PLACEMENT` sem ramo |
| **Percepção / observer / Kalman / geometria** | Cap. 8 | `src/oxebots_observers/`, `src/oxebots_prediction/` | `GameData` sem timestamp; `invert_sides` ≠ cor do time; muda interface → alinhar |
| **Mensagens / interfaces** | Apêndice B, Cap. 20 | `src/oxebots_interfaces/msg/` | Recompilação total; avisar a equipe; manter campos antigos |
| **Launch / configuração / bringup** | Cap. 3, Apêndice E | `src/oxebots_bringup/launch/`, `config/*.yaml` | Não versionar IPs locais; `match:=True` usa `ROS_DOMAIN_ID` 0 e 1 |
| **Rádio / drivers** | Caps. 3, 7 | `src/oxebots_comms/` | Modo `velocity` × `point`; hardware real: cuidado redobrado |
| **Testes / validação** | Cap. 23 | (não há testes hoje) `src/<pacote>/test/`, scripts | Não há *harness* ainda; proponha, não presuma |
| **Documentação** | todo o manual | `docs/manual/capitulos/*.md` + scripts | Regenerar PDF é com scripts; não edite o `.md` consolidado nem o PDF à mão |

Se a resposta da pessoa **não** se encaixar em nenhuma linha, ou se ela disser "só quero entender o código", leia o manual a partir do Cap. 3 e responda sem alterar nada.

---

## 5. Mapa do repositório

```text
software_ws/
├── README.md, build.sh, run_match.sh, setup.sh, .devcontainer/      # workspace e devcontainer (Jazzy, Ubuntu 24.04)
├── docs/
│   ├── manual/                    # Manual da Estratégia (PDF + Markdown + slides + scripts)
│   │   ├── capitulos/*.md         # texto-fonte (NN-*.md e A*-*.md)
│   │   ├── figuras/ , figuras_slides/
│   │   ├── anexos/                # backlog.csv, matriz-regras.csv, xml-proposto/
│   │   └── scripts/               # gerar_figuras.py, build_pdf.py, build_slides.py ...
│   └── agente/                    # estas instruções
└── src/                           # CADA pasta abaixo é um submódulo (repositório próprio)
    ├── oxebots_strategy/          # ★ estratégia
    │   ├── behavior_trees/*.xml   # 31 arquivos de árvore
    │   ├── include/oxebots_strategy/*.h|*.hpp   # folhas (declarações)
    │   ├── src/*.cpp              # strategy_node, folhas, role_assigner_node, d_star_planner, movement_calculation, trajectory_setpoint_node
    │   ├── launch/strategy.launch.py            # 4 processos por robô
    │   └── CMakeLists.txt         # lista de fontes do strategy_node
    ├── oxebots_interfaces/        # msg/ (GameData, RobotGoal, RobotCmd, RobotMotionOverride, RoleAssignment ...), proto/, srv/
    ├── oxebots_observers/         # game_observer_node (visão → /game_data, /field_geometry, /map)
    ├── oxebots_prediction/        # kalman_filter_node (bola 4D com atrito, robôs 6D)
    ├── oxebots_comms/             # grSim_controller, ra_controller, nrf24_bridge (rádio)
    ├── oxebots_bringup/           # launch/ssl-new.launch.py e config/match_config*.yaml
    ├── ssl_ros_bridge/            # pontes de visão e Game Controller; ssl_league_msgs (Referee.msg)
    └── oxebots_trajectory_analysis/   # análise de rotas (Python), fora do jogo
```

**Arquivos-chave de `oxebots_strategy`** (todos em `src/oxebots_strategy/`):

| Assunto | Arquivo |
|---|---|
| Nó que hospeda a BT, blackboard, registro das 29 folhas, Groot2 | `src/strategy_node.cpp` |
| Árvore mestre **em uso** (`MainTreeCarry`) | `behavior_trees/master_strategy_carry.xml` |
| Folhas de movimento | `src/go_to_point_node.cpp`, `kick_ball_node.cpp`, `align_to_ball_node.cpp`, `keep_distance.cpp`, `aim_at.cpp` |
| Ataque | `update_ball_position_node.cpp`, `calculate_interception_node.cpp`, `is_ball_close_condition.cpp`, `kick_readiness.hpp` |
| Defesa e goleiro | `defender_nodes.cpp`, `goalkeeper_node.cpp`, `goal_line_defend_node.cpp`, `lateral_clear_node.cpp`, `position_bisector_node.cpp`, `smother_save_node.cpp` |
| Papéis | `role_assigner_node.cpp` |
| Planejamento e controle | `d_star_planner.cpp`, `movement_calculation.cpp`, `trajectory_setpoint_node.cpp` |
| Subárvores de bola parada | `kick_off.xml`, `penalty.xml`, `free_kick.xml`, `opp_set_piece.xml`, `stop.xml`, `halt.xml`, `corner_kick.xml`, `throw_in.xml`, `kick_in.xml` |
| Papéis em jogo | `defender_tree.xml`, `goalkeeper_tree.xml` |
| Legados/testes/desafios | `master_strategy.xml`, `game_manager.xml`, `simple_attack.xml`, `attack_logic.xml`, `test_*.xml`, `start_game_*.xml`, `kick_technical_challenge*.xml`, `placement_technical_challenge_*.xml` |

---

## 6. Mapa da documentação

O manual está em `docs/manual/Manual-Estrategia-OxeBots.pdf` (167 páginas); o texto-fonte, em `docs/manual/capitulos/`. **Consulte pelo assunto:**

| Preciso saber… | Capítulo |
|---|---|
| Regras do jogo, comandos do árbitro, faltas, estados | 2 (e Apêndice C) |
| Quais pacotes/processos existem, como iniciar | 3, Apêndice E |
| Como funciona uma Behavior Tree (Sequence, Fallback, reativos, preempção) | 4 |
| XML, portas, blackboard, tipos de nó da BehaviorTree.CPP | 5 |
| O `strategy_node` | 6 |
| `GoToPoint`, D\*, controlador, override, chute | 7 |
| Observer, Kalman, lado do campo | 8 |
| Atacante | 9 |
| Defensor e goleiro | 10 |
| Papéis | 11 |
| Árvore mestre atual | 12 |
| **Defeitos e pontos de atenção conhecidos** | **13** |
| Arquitetura de jogo completo (visão geral) | 14 |
| `GameState` / `referee_state_node` | 15 |
| Master Tree v2 | 16 |
| Segurança, STOP, SafetyGate | 17 |
| Reinícios (kick-off, pênalti, free kick, ball placement) | 18 |
| Jogo corrido e degradação | 19 |
| Papéis ampliados, blackboard, idade dos dados, lado | 20 |
| **Contratos dos nós novos e das adaptações** | **21** |
| Como criar uma folha (tutorial) | 22 |
| Testes e critérios | 23 |
| Plano, frentes, cronograma | 24 |
| Termos | Apêndice A |
| Catálogo das 29 folhas, mensagens e tópicos | Apêndice B |
| XMLs propostos | Apêndice D |

Também em `docs/manual/anexos/`: `backlog.csv` (49 tarefas com dependências), `matriz-regras.csv` (30 regras do regulamento), `matriz-arvores-folhas.csv`, `xml-proposto/`. Slides de apresentação: `docs/manual/Apresentacao-Manual-OxeBots.pdf`.

O **regulamento oficial** (SSL-EL, edição de 2024-08-05) é um PDF fora do repositório; se precisar de uma regra exata, **peça o arquivo** ou cite o capítulo 2 e o Apêndice C do manual, que trazem as seções e páginas.

---

## 7. Estado atual × proposto (não confunda)

**Existe hoje** (pode ser usado):

- Uma árvore por robô, executada por `strategy_node` a 60 Hz; mestre em uso: `master_strategy_carry.xml`.
- **29 folhas registradas**: `GoToPoint`, `KickBall`, `AlignToBall`, `UpdateBallPosition`, `CalculateInterception`, `IsBallClose`, `Goalkeeper`, `PrecisionKick`, `GoalLineDefend`, `IsBallInArea`, `IsBallInOurHalf`, `LateralClear`, `PositionBisector`, `SmotherSave`, `CalculateKickOffPose`, `KeepDistance`, `AimAt`, `HasLineOfSight`, `IsBallInOpponentField`, `IsOpponentControllingBall`, `ShadowBall`, `MarkOpponent`, `GoToClamped`, `IsValueTrue`, `IsThisNodeID`, `IsMyRole`, `CheckGCCommand`, `IsRobotId`, `Halt`.
- `role_assigner_node` (atacante/defensor por custo, com histerese), D\* por robô, controlador com override, Kalman, observer, drivers.

**Proposto, ainda não existe** (Parte IV do manual — **não referenciar como pronto**):
`referee_state_node`, `GameState`, `CheckGameState`, `WeAreFavored`, `IsDataFresh`, `HasRole`, `ComputeLegalSlot`, `ComputePlacementApproach`, `SetMotionLimit`, `HoldPosition`, `PlaceBall`, `PenaltyKeeperLine`, `KickOnce`, `AvoidPlacementCorridor`, `BallHeldTimer`, `WaitBallInPlay`, a `MainTreeEL` e o `SafetyGate`.

**Defeitos conhecidos do sistema atual** (Cap. 13) — **não os "redescubra" nem os corrija por conta própria**; se a tarefa tocar neles, avise:

1. `TIMEOUT` (12/13) e `BALL_PLACEMENT` (16/17) **não têm ramo** no mestre → caem no jogo normal.
2. `NORMAL_START` **sem contexto** → `ExecutePenalty` de `penalty.xml` nunca é alcançado.
3. `KeepDistance` é usada **sem** `robot_x/robot_y` (porta sem padrão) e suas saídas não são consumidas → o STOP não afasta o robô; mesmo problema de portas em `AimAt` nos desafios.
4. `GameData` **sem timestamp**; robôs não expiram; observer só publica com bola; **sem watchdog** no controlador.
5. Sem teto de **0,75 m/s** no STOP; `PrecisionKick` sem limite de chute e escrevendo direto em `/robot_commands`.
6. Coordenadas **literais** dependentes de lado em `kick_off.xml`, `opp_set_piece.xml`, `free_kick.xml`; `ball_in_enemy_half = ball_x > 0`.
7. Goleiro `robot_id == 0` fixo; papéis iniciais fixos (`attacker_id = 2`, `defender_id = 1`).
8. `GoToPoint::onHalted()` vazio; `robot_id` diferente da instância devolve SUCCESS silencioso.
9. Flags `is_corner_kick`, `is_kick_in`, `is_opponent_foul` **nunca escritas**; IDs de árvore duplicados (`MainTree` ×8, `Desafio1/2/3` ×2).

---

## 8. Conhecimento técnico essencial

### 8.1 Behavior Trees no projeto

- **A ordem dos irmãos é a prioridade.** Raiz do mestre: `ReactiveFallback`.
- `Sequence`/`Fallback` **comuns têm memória**: não reavaliam os filhos anteriores enquanto um filho roda. Para **guardas**, use `ReactiveSequence`; para **preempção por prioridade**, `ReactiveFallback`.
- Em `ReactiveSequence`/`ReactiveFallback`, os filhos anteriores são reexecutados **todo tick**: devem ser baratos, sem efeito colateral relevante e, de preferência, síncronos (no máx. um filho assíncrono).
- `Parallel(success_count, failure_count)`: filhos concluídos **não** são reexecutados; ao decidir, interrompe os demais.
- `RetryUntilSuccessful(-1)` com filho síncrono que falha = *polling* de uma tentativa por tick (a confirmar na versão instalada).
- Folha assíncrona: `onStart` / `onRunning` / `onHalted`. Retornos: SUCCESS, FAILURE, RUNNING. **Falhe alto** (FAILURE + log) quando faltar dado.
- **Blackboard**: cada `SubTree` tem a sua; `_autoremap="true"` copia as chaves que **já existem** no pai. Folhas leem a **raiz** com `config().blackboard->rootBlackboard()`.
- **IDs de árvore são globais** na fábrica: todos os `.xml` do diretório são registrados como subárvores → IDs devem ser únicos.
- As folhas são compiladas **dentro** do `strategy_node` (sem plugin): registrar em `strategy_node.cpp` **e** incluir o `.cpp` no `CMakeLists.txt`.
- Groot2: porta `1667 + robot_id` (azul) / `1677 + robot_id` (amarelo).

### 8.2 Unidades, referencial e convenções

- Posições em **mm**, ângulos em **rad** (anti-horário, θ = 0 aponta para +x), velocidades em **m/s**. O `RobotGoal` usa **metros** (a conversão ocorre em `GoToPoint`).
- Origem no centro do campo. Campo EL: área de jogo **4500 × 3000 mm**; área de defesa **1350 × 500 mm**; círculo central Ø 1000 mm.
- Gol próprio: `my_goal_x = +L/2` (cor efetiva amarela) ou `−L/2` (azul). `is_yellow` na blackboard é a cor **efetiva** (`is_yellow_team` XOR `invert_sides`). `invert_sides` espelha coordenadas (x, y → −x, −y; θ → θ + π) e é `True` por padrão só em `mode:=ra`.
- `gc_command` (int cru do `Referee.command`): 0 HALT, 1 STOP, 2 NORMAL_START, 3 FORCE_START, 4/5 PREPARE_KICKOFF (amarelo/azul), 6/7 PREPARE_PENALTY, 8/9 DIRECT_FREE, 12/13 TIMEOUT, 16/17 BALL_PLACEMENT; legados 10/11 (INDIRECT) e 14/15 (GOAL). Valor inicial `−1` = "nunca recebi".

### 8.3 Regulamento — números que importam

HALT: parar (2 s de tolerância) · STOP: **< 0,75 m/s**, **≥ 0,5 m** da bola, sem tocá-la · robô ≤ **1,5 m/s** · bola ≤ **3 m/s** · free kick/kick-off adversário: **≥ 0,5 m** da bola · STOP/free kick: **≥ 0,2 m** da área adversária · não-goleiro fora da própria área · bola retida na área ≤ **10 s** · pênalti: goleiro na linha de gol, demais **≥ 1 m atrás** da bola, bola só rumo ao gol · kick-off: tudo na própria metade e fora do círculo, só o cobrador no círculo · 3 robôs; cartão amarelo reduz um robô por 120 s · timeouts 4 / 420 s.

### 8.4 Movimento e controle

- Controlador a **20 Hz**; `max_linear_speed` padrão **1,0 m/s**; lookahead **100 mm**; override **pegajoso com TTL de 200 ms** (precisa ser renovado a cada tick); chute: janela de 200 ms + cooldown de 600 ms; `KickBall` limita a **3,0 m/s**.
- D\*: 10 Hz (40 Hz com bola a < 0,4 m); grade de 5 cm; rota vazia ⇒ o robô pára; `planner="straight_line"` ignora robôs e só desvia da bola.
- `GoToPoint`: `tolerance ≤ 0` ⇒ **nunca** SUCCESS; SUCCESS exige posição **e** orientação (0,15 rad).

### 8.5 Chaves de blackboard existentes

`robot_id`, `is_goalkeeper`, `is_yellow`, `attacker_id`, `defender_id`, `is_attacker`, `gc_command`, `gc_stage`, `is_free_kick`, `designated_x/y`, `robot_x/y/yaw`, `ball_x/y/vx/vy`, `ball` (`Pose2D`), `ball_vel` (`Vector2D`), `opponent_controlling`, `attacker_ball_dist`, `defender_ball_dist`, `my_goal_x`, `opponent_goal_x/y`, `field_length/width`, `penalty_area_depth/width`, `goal_width`, `center_circle_radius`. (`is_corner_kick`, `is_kick_in`, `is_opponent_foul` são lidas por XML mas **nunca escritas**.)

---

## 9. Receitas

### 9.1 Editar uma árvore XML existente

1. Pergunte qual árvore/ramo e o objetivo (seção 4). Leia o XML **inteiro** e as folhas que ele usa (Apêndice B / código).
2. Confira cada nó: está **registrado**? Todas as portas obrigatórias têm atributo ou padrão? Os tipos batem?
3. Guarda de ramo = `ReactiveSequence`. Ordem = prioridade. Sem coordenada literal com sinal fixo.
4. Verifique se o ID/tag que você usa é único e se outras árvores (`SubTree`) dependem do que você muda.
5. Entregue a mudança **mínima**, com um parágrafo: o que mudou, por quê, que cenário de jogo isso afeta, o que **não** foi verificado, e como a pessoa pode ver no Groot2/simulador.

### 9.2 Criar ou alterar uma folha C++

Siga o tutorial do **Cap. 22** (passo a passo com `HoldPosition`). Checklist:

- [ ] herda do tipo certo (`ConditionNode`, `SyncActionNode`, `StatefulActionNode`);
- [ ] `providedPorts()` com tipos, **padrões** e descrições; nenhuma porta obrigatória "escondida";
- [ ] lê dados sob *mutex* quando vêm de callbacks;
- [ ] `FAILURE` + log (com `_THROTTLE`) quando faltam dados — nunca RUNNING mudo;
- [ ] `onHalted()` idempotente e rápido; solta override se pediu algum;
- [ ] **não** publica em `/robot_commands`; chute ≤ 3 m/s;
- [ ] registrada em `strategy_node.cpp` e `.cpp` incluído no `CMakeLists.txt`;
- [ ] documentada no catálogo (Apêndice B).
Depois, **não compile**: diga à pessoa o que compilar e testar.

### 9.3 Mexer em `GoToPoint`, D\* ou controlador

Alto risco: muitas árvores dependem. Leia o Cap. 7 inteiro. Não altere portas existentes (só **acrescente** com padrão que preserve o comportamento atual). Não enfraqueça nenhum clamp ou limite. Descreva o efeito em **todas** as árvores que usam a folha (`grep -l "<GoToPoint" behavior_trees/*.xml`).

### 9.4 Mexer em mensagens ou interfaces

Não faça sem alinhar. Se for autorizado: **acrescente** campos (com padrão compatível) em vez de remover/renomear; liste todos os produtores e consumidores (`grep` pelo nome da mensagem em `src/`); avise que `oxebots_interfaces` e dependentes precisam ser recompilados e que *rosbags* antigos podem ficar incompatíveis. Se afetar o rádio, lembre do `ssl_robot_protocol.bitproto` e dos cabeçalhos gerados.

### 9.5 Diagnosticar comportamento do robô

Pergunte primeiro: simulador ou real, cor, comando do árbitro, e o ramo ativo no Groot2. Hipóteses típicas, em ordem: (1) comando sem ramo (Cap. 13); (2) porta sem valor → FAILURE silencioso; (3) preempção que não cancelou o `RobotGoal` (`onHalted` vazio); (4) literal dependente de lado; (5) dado sem idade; (6) override expirado (200 ms); (7) clamp de área empurrando o alvo; (8) papel trocado pelo atribuidor (histerese). Peça logs; **não** altere o código para "ver se resolve".

### 9.6 Escrever ou ajustar documentação

Os capítulos em `docs/manual/capitulos/*.md` são a fonte. Figuras vêm de `docs/manual/scripts/fig_*.py`. O PDF e o `.md` consolidado são **gerados** (`scripts/build_pdf.py`) — não edite os gerados. Mantenha o tom didático do manual e a distinção "existe hoje × proposto".

---

## 10. Como entregar e como relatar

**Antes de entregar uma alteração, confira:**

- [ ] Perguntei o contexto (seção 4) ou a pessoa já o deu?
- [ ] Li os arquivos inteiros e busquei todos os usos?
- [ ] A mudança é mínima e restrita ao pedido?
- [ ] Não enfraqueci nenhuma proteção de segurança/regulamentar?
- [ ] Não toquei em submódulos, ponteiros, `build/`, `install/`, `log/`?
- [ ] Não compilei, não rodei launch, não commitei (a menos que pedido)?
- [ ] Citei as chaves/IDs/tópicos reais (nada inventado)?

**Formato da resposta final:**

1. **O que mudou** (arquivos e, em uma linha, cada alteração) e **o que não foi tocado de propósito**.
2. **Por que** (ligando ao requisito, ao capítulo do manual ou ao defeito do Cap. 13).
3. **Como verificar** (o que compilar/rodar/olhar no Groot2 — **para a pessoa fazer**).
4. **Riscos e impactos** (outras árvores/frentes afetadas; arquivos compartilhados).
5. **O que eu não verifiquei** e **hipóteses** em aberto.
6. Uma **pergunta de seguimento** objetiva, se houver decisão pendente.

---

## 11. Quando parar e perguntar

Pare e consulte a pessoa antes de seguir se:

- o pedido tocar **segurança**, limites regulamentares, HALT/STOP, clamp de área, chute;
- exigir **alterar mensagem**, protocolo do rádio, ponteiro de submódulo, `CMakeLists.txt` de outro pacote ou arquivo de alto risco de conflito (seção 3);
- você precisar **renomear/remover** algo usado em vários lugares;
- o código real **contradisser** o manual (o código manda; relate a divergência e sugira atualizar o manual);
- houver **mais de uma interpretação razoável** do pedido;
- a mudança parecer exigir **compilar ou executar** algo para ter certeza;
- você perceber que está prestes a "arrumar" algo que ninguém pediu.

---

## 12. Convenções de código, commits e estilo

- **C++**: siga o estilo do arquivo vizinho e o `.clang-format` da raiz; nomes de classes `PascalCase` com sufixo `Node`/`Condition` nas folhas; comentários em português quando o arquivo já os tem. **Python**: `.ruff.toml` da raiz.
- **Folhas**: ID de registro em `PascalCase` (`"GoToPoint"`); portas em `snake_case`; unidades explícitas no nome ou na descrição (`_mm`, `_ms`).
- **XML**: `BTCPP_format="4"`; um `<BehaviorTree ID>` por árvore; nomes de ramo descritivos (`name="..."`); comentários curtos em português.
- **Commits** (somente quando a pessoa pedir): *Conventional Commits* em português, escopo opcional por pacote — ex.: `feat(oxebots_strategy): ...`, `fix: ...`, `docs: ...`, `refactor: ...`, `chore: atualiza ponteiros dos submódulos ...`. Corpo explicando o **porquê**; lista objetiva do que mudou.
- **Branches**: a branch atual de trabalho e a `main`/`dev` variam; **nunca** troque de branch sem pedido.

---

## 13. Resumo para memorizar

1. **Pergunte** em que parte/árvore a pessoa está trabalhando.
2. **Leia** o capítulo certo do manual e o código inteiro antes de mexer.
3. **Mude o mínimo**; não "melhore" o que não foi pedido.
4. **Não compile, não rode, não commite, não mexa em submódulo** sem pedido.
5. **Nunca enfraqueça** proteções de segurança/regulamento.
6. **Separe** existe-hoje de proposto; **não invente** nomes.
7. **Pense no grupo**: arquivos compartilhados, contratos de interface, mudanças pequenas.
8. **Seja honesto** sobre o que foi e o que não foi verificado.
