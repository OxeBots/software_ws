# Papéis, blackboard e contratos de dados

Este capítulo fecha o desenho da Parte IV tratando da "cola" entre os componentes: a mensagem de papéis ampliada, o novo esquema da blackboard, a validação da idade dos dados, o tratamento do lado do campo e um exemplo completo de ponta a ponta.

## Papéis ampliados

A mensagem `RoleAssignment`, hoje com `attacker_id` e `defender_id`, passa a trazer o necessário para uma partida inteira:

| Campo | Significado |
|---|---|
| `goalkeeper_id` | identificador do goleiro (do `TeamInfo.goalkeeper` do GC, ou parâmetro; ausente se o robô não está ativo) |
| `attacker_id` | atacante em jogo corrido |
| `defender_id` | defensor em jogo corrido |
| `kicker_id` | quem **bate** o reinício em curso (kick-off, pênalti, free kick, ball placement) |
| `epoch` | inteiro crescente: aumenta a cada mudança de papéis |
| `active_ids[]` | robôs considerados ativos |

### Cobrador travado

Para reinícios, o `role_assigner_node` escolhe o `kicker_id` pelo **menor custo até o ponto do reinício** (a bola, ou o ponto designado) e o **trava** enquanto a fase for de reinício (`PREPARE_*`, `KICKOFF`, `PENALTY`, `FREE_KICK`, `BALL_PLACEMENT`). A troca só é permitida quando a fase volta a `RUN` ou quando o robô travado deixa de estar ativo. Isso corrige a instabilidade atual, em que o atribuidor poderia trocar o atacante no meio da preparação do kick-off.

### Época

O campo `epoch` permite que as árvores detectem **papéis velhos**: se a época que a árvore conhece é menor que a da mensagem, houve troca. Na prática, a troca de papéis já é refletida pela guarda `HasRole` (que é reavaliada a cada tick); a `epoch` serve para diagnóstico, registro e para folhas que precisem reiniciar estado interno quando o papel muda.

### Histerese e exclusividade

As histereses atuais (custo 2,5; tempo 2 s) são **mantidas**, com uma exceção: são **desligadas** durante os reinícios (o cobrador é travado, como visto). A exclusividade — cada identificador tem exatamente um papel por época — é garantida pelo próprio atribuidor, que publica um conjunto coerente por mensagem.

## A blackboard proposta

### O que mudar

A blackboard atual é escrita por callbacks em outra *thread*, o que dá valores relacionados lidos em instantes diferentes (Capítulo 5). A proposta é fazer a atualização **em um único ponto**, na *thread* de tick, no início de cada tick: uma função `refresh()` copia de buffers (um por fonte de dados, preenchidos pelas callbacks sob *mutex*) para a blackboard, **de uma só vez**. Assim, durante um tick, todas as chaves são consistentes entre si.

![Das fontes à blackboard e dela aos nós consumidores](figuras/blackboard_fluxo.png)

### As chaves

| Chave | Tipo | Quem escreve | Quem lê | Validade |
|---|---|---|---|---|
| `phase`, `restart_ctx`, `we_favored` | enum, enum, bool | `refresh()` (de `/game_state`) | `CheckGameState`, `WeAreFavored` | `gc_age_ms` |
| `designated`, `has_designated` | `Pose2D`, bool | idem | árvores de reinício | idem |
| `speed_limit`, `can_place_ball` | double, bool | idem | `SetMotionLimit`, ball placement | idem |
| `own_goal_x`, `opp_goal_x`, `opp_goal_y`, `side_sign` | double, double, double, int | idem + geometria | quase todas | por geometria |
| `field_*`, `penalty_area_*`, `goal_width`, `center_circle_radius` | double (mm) | geometria | folhas de posição | por geometria |
| `role`, `kicker_id`, `role_epoch`, `active_ids` | enum, uint, uint, vetor | `refresh()` (de `/role_assignment`) | `HasRole` | por época |
| `robot_pose` | `Pose2D` | `refresh()` (de `/game_data`) | movimento | `pose_age_ms` |
| `ball`, `ball_vel` | `Pose2D`, `Vector2D` | `refresh()` (de `/game_data` e do Kalman) | defesa, ataque | `ball_age_ms` |
| `gc_age_ms`, `pose_age_ms`, `ball_age_ms` | double | `refresh()` | `IsDataFresh` | — |

As chaves **temporárias** de subárvore (`pkx`, `pky`, `int_*`, `slot_x`…) continuam com o escopo da subárvore e **não** são remapeadas com `_autoremap`, para não poluir a raiz.

### Convenções

- Nomes em `snake_case`, com sufixo de unidade quando houver ambiguidade (`_ms`, `_mm`).
- Posições em **mm** e ângulos em **rad** na árvore; metros só no `RobotGoal`.
- Preferir **objetos compostos** (`ball` como `Pose2D`, `robot_pose`) a pares de chaves soltas (`ball_x`, `ball_y`), para evitar leituras parciais.

## A idade dos dados

A idade é a base da supervisão de segurança. Ela depende de **carimbos de tempo** que hoje não existem:

- `GameData` ganha um `std_msgs/Header` e, para cada robô, o instante da última detecção;
- o `game_observer_node` passa a **expirar** robôs não vistos por alguns quadros (hoje, ficam para sempre) e a publicar **mesmo sem bola** (hoje, não publica);
- o `refresh()` calcula as idades: `pose_age_ms = agora − stamp da pose`, `ball_age_ms`, e `gc_age_ms` (a partir de `GameState.stale` e do seu carimbo).

A condição `IsDataFresh` apenas compara essas idades com os limites; a vigilância "pesada" (watchdog) fica no SafetyGate.

## O lado do campo

O `referee_state_node` calcula `our_goal_positive_x` a partir de `blue_team_on_positive_half` e da nossa cor. O `refresh()` traduz isso em duas chaves:

- **`own_goal_x`** = `+L/2` se o nosso gol está em x positivo, `−L/2` caso contrário;
- **`side_sign`** = `+1` se defendemos o gol de x **negativo** (nossa metade é x < 0), `−1` caso contrário.

Com isso, qualquer posição "para o nosso lado do campo" é escrita como `side_sign × (valor positivo)`, e `ComputeLegalSlot` faz esse espelhamento internamente. Nenhum XML precisa conhecer o lado. Na troca de tempo, `blue_team_on_positive_half` inverte, `side_sign` muda de sinal, e todas as posições calculadas a partir daí são automaticamente as do lado novo.

!!! warning "`invert_sides` fica só para o simulador"
    O parâmetro `invert_sides` do observer espelha as **coordenadas** para o simulador Ra. Ele não deve influenciar a **cor** do time nem o **lado lógico** de defesa. Na proposta, `is_yellow` volta a significar apenas a cor real, e o lado lógico vem do árbitro.

## Concorrência: como evitar leituras inconsistentes

Resumindo as regras de acesso aos dados:

1. Cada fonte (GC, visão, geometria, papéis) tem um **dono**, que a converte para o tipo interno.
2. As callbacks apenas **copiam** a última mensagem para um buffer protegido por *mutex*.
3. A cada tick, `refresh()` lê todos os buffers e atualiza a blackboard.
4. As folhas leem a blackboard; as folhas só escrevem chaves temporárias da própria subárvore.
5. Uma chave obrigatória ausente leva a FAILURE com log, nunca a um valor padrão silencioso.

## Um exemplo de ponta a ponta

O exemplo abaixo percorre uma informação desde a rede até a ação, e a sua interrupção. Os nós `CheckGameState` e `ComputeLegalSlot` ainda não existem (são os nós novos); `GoToPoint` é código existente.

1. **A informação chega.** O Game Controller publica `Referee { command = STOP, command_counter = 57 }`.
2. **O estado é interpretado.** O `referee_state_node` aceita a mensagem (o contador avançou), mapeia `STOP → phase = STOP`, calcula `speed_limit = 0,75` e publica o `GameState`.
3. **O dado chega à árvore.** No início do tick seguinte, `refresh()` copia `phase = "STOP"` e `speed_limit = 0.75` para a blackboard.
4. **Uma condição escolhe o ramo.** `CheckGameState phase="STOP"` lê a chave e devolve SUCCESS; o ramo `StopBranch` torna-se ativo.
5. **Uma ação recebe parâmetros.** A `StopSubTree` calcula `slot_x`, `slot_y` com `ComputeLegalSlot` e passa ao `GoToPoint`: `x="{slot_x}" y="{slot_y}"`.
6. **A subárvore usa remapeamento.** `<SubTree ID="StopSubTree" _autoremap="true"/>` torna `ball_x`, `ball_y`, `robot_id` visíveis dentro dela.
7. **Um evento novo interrompe a ação.** Chega `FORCE_START`: a fase vira `RUN`. No tick seguinte, o `ReactiveFallback` raiz tenta primeiro os ramos de cima; `CheckGameState STOP` falha, o ramo de STOP é interrompido, e `GoToPoint::onHalted()` publica "fique onde está".
8. **O estado é registrado.** O nó de log escreve uma linha: `phase STOP → RUN (cmd_counter=58)`.
