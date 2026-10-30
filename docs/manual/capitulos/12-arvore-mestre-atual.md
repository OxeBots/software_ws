# A árvore mestre atual

Neste capítulo juntamos as peças. A árvore que o time executa hoje é `master_strategy_carry.xml` (ID `MainTreeCarry`), configurada como padrão nos arquivos YAML. Ela organiza todo o comportamento em um único `ReactiveFallback` de ramos por prioridade ({{fig:arvore_mestre_atual}}).

![A árvore mestre atual, ramo a ramo](figuras/arvore_mestre_atual.png)

## Como ler a árvore

A raiz, `MasterStrategy`, é um `ReactiveFallback`: a cada tick, os ramos são tentados **de cima para baixo**, e o primeiro que tiver sucesso (ou estiver em andamento) é o escolhido; os de baixo são interrompidos. A ordem dos ramos é, portanto, a **prioridade**:

| # | Ramo | Condição | Ação |
|---|---|---|---|
| 1 | `HaltBranch` | comando = 0 (HALT) | `HaltSubTree` |
| 2 | `StopBranch` | comando = 1 (STOP) | `StopSubTree` |
| 3 | `OurKickOffBranch` | comando 4 (se amarelos) ou 5 (se azuis) | `KickOffTree` |
| 4 | `OurPenaltyBranch` | comando 6 (se amarelos) ou 7 (se azuis) | `PenaltyTree` |
| 5 | `CornerBranch` | flag `is_corner_kick` | `CornerTree` |
| 6 | `ThrowInBranch` | flag `is_kick_in` | `ThrowInTree` |
| 7 | `FreeKickBranch` | flag `is_free_kick` | `FreeKickTree` |
| 8 | `OpponentSetPieceBranch` | comando do adversário (kick-off 4/5, pênalti 6/7, falta 8/9) ou flag `is_opponent_foul` | `OppSetPieceTree` |
| 9 | `GoalkeeperRole` | `robot_id == 0` | `GoalkeeperTree` |
| 10 | `AttackerRole` | papel = atacante | laço do atacante (Capítulo 9) |
| 11 | (defensor) | papel = defensor | `DefenderTree` |
| 12 | `Halt (idle)` | — | parar o robô |

Os ramos 1 a 8 tratam **bolas paradas e comandos do árbitro**; os ramos 9 a 11 tratam o **jogo corrido**, distribuindo o trabalho pelos papéis; o ramo 12 é a rede de segurança: se nenhum outro serve, o robô fica parado.

Uma observação sobre a **seleção de cor**: os ramos de kick-off e pênalti usam `is_yellow` (a cor efetiva) para escolher entre os comandos "amarelo" e "azul". Por exemplo, `OurKickOffBranch` aceita `cmd == 4` se somos amarelos e `cmd == 5` se somos azuis. O ramo do adversário usa os comandos *complementares*.

## As subárvores de bola parada

### HaltSubTree e StopSubTree

`HaltSubTree` é uma única ação `Halt`. `StopSubTree` é uma `ReactiveSequence` que atualiza a posição da bola e chama a folha `KeepDistance` com 550 mm (0,5 m do regulamento mais 5 cm de margem), como mostra a figura a seguir. Esse ramo é crítico e merece a leitura do Capítulo 13.

![A árvore de STOP atual](figuras/arvore_stop_atual.png)

### KickOffTree

O kick-off do nosso time distribui três papéis com um `Fallback` ({{fig:arvore_kickoff_atual}}):

![A árvore de kick-off atual: posições fixas por papel](figuras/arvore_kickoff_atual.png)

- o **goleiro** (`robot_id == 0`) executa `GoalkeeperTree`;
- o **atacante** vai a `(350, 0)` — dentro do círculo central, como é permitido ao cobrador — e **espera** até o comando virar `NORMAL_START` (o `Repeat` com um `Inverter(CheckGCCommand 2)` é o mecanismo de espera);
- o **defensor** vai a `(600, 600)` pela mesma lógica;
- qualquer outro robô fica parado (`Halt waiting_kick_off`).

As coordenadas são **literais no XML**, um ponto a que voltaremos: elas só são válidas para um dos lados do campo.

### PenaltyTree

A árvore de pênalti do nosso time tem um `Fallback` com três ramos: o atacante (cobrador), o goleiro (que executa `Goalkeeper`) e os demais (`Halt`). O cobrador tem uma `ReactiveFallback` interna com duas ações: **"executar o pênalti"** (quando o comando é `NORMAL_START`: vai à bola e chuta) e **"preparar"** (vai ao ponto de pré-chute e aguarda). Há uma sutileza importante sobre a primeira: ela só roda se o comando for 2 *enquanto o ramo do pênalti está ativo* — e o ramo do mestre só é ativado com o comando de preparação (6 ou 7). Veja a discussão no Capítulo 13.

### FreeKickTree

Na falta a nosso favor, o goleiro continua na meta, o **cobrador** (atacante) vai ao ponto de pré-chute e, em seguida, em paralelo, **avança à bola** e **chuta** (um `Parallel(success=1, failure=1)` combina `GoToPoint` à bola e "espere `IsBallClose` e então `KickBall`"). O **suporte** (defensor) mantém-se a 650 mm da bola se ela chegar a menos de 600 mm, ou vai a uma posição fixa.

### OppSetPieceTree

Quando a bola parada é do adversário, o objetivo é **recuar sem cometer falta**: o goleiro defende normalmente; o defensor e o atacante vão a posições táticas fixas, mas — se a bola chegar a menos de 600 mm — recuam para 650 mm dela com `KeepDistance`.

### CornerTree, ThrowInTree e KickInTree

Árvores específicas para escanteio e lateral. Dependem de flags (`is_corner_kick`, `is_kick_in`) que **ninguém escreve** hoje — e, como vimos no Capítulo 2, escanteios e laterais chegam como `DIRECT_FREE`. Na prática, são código sem uso.

## O jogo corrido

Se nenhum ramo de bola parada se aplica, o mestre cai nos três ramos de papel:

1. **Goleiro**: `ReactiveSequence(IsRobotId 0, GoalkeeperTree)`.
2. **Atacante**: o laço descrito no Capítulo 9.
3. **Defensor**: a `DefenderTree` (Capítulo 10).
4. **Parado** (`Halt idle`): robôs sem papel, ou se tudo falhar.

Observe que, neste desenho, "jogo corrido" não é uma condição verificada: é o que **sobra** quando nenhum outro ramo casa. Esse "default" é elegante, mas tem uma consequência importante, que o próximo capítulo explora: qualquer comando que o mestre *não conhece* cai, silenciosamente, no jogo corrido.

## Outras árvores no diretório

O diretório `behavior_trees/` contém muito mais do que a árvore mestre:

- **Versões anteriores do mestre**: `master_strategy.xml` (só para o time amarelo) e `game_manager.xml` (um seletor com `Fallback`, sem preempção).
- **Árvores de jogo simplificadas**: `simple_attack.xml`, `attack_logic.xml`, `test_attack.xml`, `normal_play.xml`.
- **Posicionamento inicial**: `start_game_left.xml`, `start_game_right.xml`.
- **Árvores de teste**: `test_prediction.xml`, `test_roles.xml`, `test_tree.xml`.
- **Desafios técnicos** (`kick_technical_challenge1-4.xml`, `placement_technical_challenge_*.xml`): roteiros específicos, um por robô, escritos para as provas técnicas do campeonato. Usam `IsThisNodeID`, `AimAt`, `Sleep` e `ignore_area`.

Como o `strategy_node` registra **todos** os `.xml` do diretório, esses arquivos coexistem na mesma fábrica — o que exige IDs únicos, e vários legados têm o mesmo `MainTree`.
