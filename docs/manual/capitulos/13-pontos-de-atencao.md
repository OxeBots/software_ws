# Pontos de atenção do sistema atual

O sistema atual já faz muita coisa bem: percebe o jogo, planeja rotas, ataca, defende e executa várias bolas paradas em simulação. Mas ele foi construído de forma incremental, desafio a desafio, e algumas decisões que funcionam em um cenário controlado deixam de funcionar quando se pensa em uma **partida inteira**, com todos os comandos do árbitro, os dois lados do campo e falhas de comunicação. Este capítulo reúne esses pontos. O objetivo não é criticar, e sim mapear com precisão o que precisa ser resolvido — cada ponto aponta o capítulo da Parte IV que o resolve.

## Comandos que o mestre não conhece

Como vimos no Capítulo 12, o jogo corrido é o **destino padrão** do mestre: se nenhum ramo de bola parada casa, o robô joga. Isso é cômodo, mas significa que um comando sem ramo é tratado como se o jogo estivesse rolando.

Hoje, dois comandos regulamentares **não têm ramo nenhum**:

- **`TIMEOUT_YELLOW/BLUE` (12/13).** Durante um timeout, os robôs deveriam ficar parados. Em vez disso, o mestre os põe para jogar: o atacante persegue a bola.
- **`BALL_PLACEMENT_YELLOW/BLUE` (16/17).** Durante o posicionamento da bola, o jogo continua *parado* e tocar na bola é falta. Mas o mestre também trata esse comando como jogo corrido: o atacante vai à bola e tenta chutá-la, e o robô pode ficar dentro do corredor proibido.

Há ainda os comandos legados (`INDIRECT_FREE` 10/11 e `GOAL` 14/15), que não aparecem nas versões modernas do Game Controller, mas cairiam no mesmo destino.

**Solução:** cada comando passa a ter uma fase de jogo explícita e um ramo próprio (Capítulos 15, 16 e 18).

## O NORMAL_START sem contexto

`NORMAL_START` é o comando que **autoriza** tanto o kick-off quanto o pênalti. O mestre atual só ativa o ramo do kick-off com `cmd == 4/5` e o do pênalti com `cmd == 6/7` — isto é, **com o comando de preparação**. Quando chega o `NORMAL_START`, o comando muda para 2, **nenhum** desses ramos casa mais, e o robô cai no jogo corrido ({{fig:normal_start_sem_contexto}}).

![Linha do tempo de um pênalti nosso: ao chegar o NORMAL_START, nenhum ramo de bola parada casa](figuras/normal_start_sem_contexto.png)

Consequências práticas:

- A parte `ExecutePenalty` da `PenaltyTree`, que só roda com `cmd == 2`, **nunca é alcançada** pelo mestre: o ramo pai não está ativo nesse comando.
- No kick-off, a transição "funciona" por acaso: as árvores de espera (`Repeat` com `Inverter(CheckGCCommand 2)`) terminam quando o comando vira 2 e o jogo corrido assume, com o atacante indo à bola.
- No pênalti, porém, o jogo corrido faz com que **todos** os robôs, inclusive os que deveriam permanecer 1 m atrás da bola, entrem em ação, o que viola as regras de posicionamento.

**Solução:** guardar o **contexto do reinício** (kick-off ou pênalti, e a quem favorece) quando chega o comando de preparação, e derivar fases `KICKOFF` e `PENALTY` para o `NORMAL_START` (Capítulo 15).

## O ramo de STOP

O `StopSubTree` ({{fig:arvore_stop_atual}}, do capítulo anterior) contém uma `ReactiveSequence` com `UpdateBallPosition` e `KeepDistance` (550 mm). A intenção é nítida: manter o robô a 0,5 m da bola. Mas a implementação tem dois problemas que, juntos, impedem o efeito:

1. **Portas obrigatórias não informadas.** `KeepDistance` declara as entradas `robot_x` e `robot_y` **sem valor padrão**, e o XML não as passa. Como vimos no Capítulo 5, a biblioteca não busca por conta própria uma chave com o mesmo nome na blackboard; `getInput` falha e a folha devolve **FAILURE** (conferido nas fontes da série 4.6 da biblioteca).
2. **As saídas não são usadas.** Mesmo que `KeepDistance` funcionasse, ela só **calcula** um ponto de recuo (`target_x`, `target_y`) e não move o robô; nenhum XML conecta essas saídas a um `GoToPoint`.

O efeito em cascata é sério: a `ReactiveSequence` do STOP falha, o `StopBranch` falha, e o mestre segue para os ramos de baixo — o jogo corrido — **durante o STOP**. O mesmo padrão aparece em `free_kick.xml` e `opp_set_piece.xml` (quatro usos de `KeepDistance` ao todo), e a folha `AimAt` dos desafios técnicos sofre do mesmo problema de portas.

!!! warning "Vale confirmar com um teste"
    A análise acima decorre do código e da semântica da biblioteca. Como o time registrou os desafios técnicos como concluídos, convém executar `Desafio1` com o Groot2 e confirmar o comportamento na versão instalada (4.10). O plano de testes (Capítulo 23) inclui um *validador estático* de XML que detecta automaticamente portas obrigatórias não informadas.

**Solução:** uma `StopTree` que de fato move o robô (`ComputeLegalSlot` + `GoToPoint`, ou `HoldPosition`) e uma `KeepDistance` corrigida (Capítulos 17 e 21).

## Dados sem idade e sem vigilância

Como vimos nos Capítulos 6, 7 e 8, a imagem do mundo que chega à árvore **não carrega idade**: `GameData` não tem carimbo de tempo, os robôs não expiram no observer, e o observer só publica quando vê a bola. Se a visão cair:

- a blackboard continua com os últimos valores e a árvore segue decidindo com base neles;
- o controlador continua seguindo a **última rota** (rotas só são substituídas quando o D\* publica uma nova);
- o override de parada expira em 200 ms (se nenhuma árvore o renovar), devolvendo o robô ao seguimento de rota.

Em outras palavras, o sistema **não tem um modo seguro de falha**: se a árvore parar de ticar (travada, em *crash*, ou esperando um recurso) o robô continua se movendo. É o ponto mais sério do ponto de vista de segurança.

**Solução:** carimbar os dados, validar a idade com uma condição (`IsDataFresh`) no ramo de maior prioridade da árvore e acrescentar um *watchdog* no controlador, que zera os comandos se nada chegar por 500 ms (Capítulo 17).

## Limites de velocidade e de chute

Dois limites do regulamento são só parcialmente cobertos:

- **Velocidade em STOP (0,75 m/s).** O controlador usa um único teto, `max_linear_speed` (1,0 m/s no código), em qualquer fase. Em STOP, o limite regulamentar não é aplicado.
- **Velocidade da bola (3 m/s).** `KickBall` limita o pedido a 3 m/s, mas a folha `PrecisionKick` — presente em várias árvores legadas — **não limita** (os XML a usam com 4,5 m/s) e ainda escreve diretamente em `/robot_commands`, rompendo a regra de que o controlador é o único escritor.

**Solução:** um *SafetyGate* no controlador, que aplica o teto de velocidade da fase atual e limita o chute a 3 m/s **independentemente** da árvore (Capítulo 17).

## O lado do campo

A blackboard define `my_goal_x` como `+L/2` para a cor efetiva amarela e `−L/2` para a azul. As condições espaciais (`IsBallInOurHalf`, `IsBallInOpponentField`) usam esse valor e, portanto, funcionam para os dois times. Porém, vários **XML contêm coordenadas literais**, e elas pressupõem lados **diferentes** entre si:

| Árvore | Literal | Pressupõe que a nossa metade é... |
|---|---|---|
| `kick_off.xml` | `(350, 0)`, `(600, 600)` | x **positivo** (time amarelo) |
| `opp_set_piece.xml` | `x = −1500`, `x = −500` | x **negativo** (time azul) |
| `free_kick.xml` | `(−500, 0)` | x **negativo** (time azul) |
| `UpdateBallPosition` | `ball_in_enemy_half = ball_x > 0` | x **negativo** (time azul) |

O resultado é que, **para qualquer um dos dois times, algum desses literais cai do lado errado** ({{fig:lado_literais}}): o time azul (que defende `x = −2250`) tem o cobrador e o defensor do kick-off posicionados na metade adversária — o defensor ali é falta —, enquanto o time amarelo (que defende `x = +2250`) vai recuar para posições de bola parada do adversário que ficam perto do **gol adversário**.

![Os mesmos literais vistos pelos dois times: em verde, na metade própria; em vermelho, na metade errada](figuras/lado_literais.png)

Há ainda um segundo aspecto: o lado é **fixo por cor**. O Game Controller informa, na mensagem, `blue_team_on_positive_half`, que indica de que lado cada time realmente joga (e que muda entre os tempos). O software atual ignora esse campo.

**Solução:** uma chave `side_sign` e um `own_goal_x` derivados do campo do árbitro, e posições **calculadas** (`ComputeLegalSlot`) em vez de literais (Capítulos 15 e 20).

## Papéis e goleiro fixos

Como vimos no Capítulo 11: o goleiro é `robot_id == 0` por todo o código (árvores, `GoToPoint`, o controlador e o D\* tratam o robô 0 de modo especial), os papéis iniciais são constantes, e o atribuidor não conhece a fase de jogo nem os robôs ativos. Além disso, `attacker_ball_dist` é calculada no `strategy_node` com um identificador de atacante fixo (2), independente do papel real.

**Solução:** goleiro vindo do Game Controller, papéis conscientes da fase e uma época para detectar papéis antigos (Capítulos 19 e 20).

## Interromper uma ação não pára o robô

Quando um ramo de maior prioridade assume, a ação anterior recebe `halt()`. Mas a folha `GoToPoint` tem `onHalted()` **vazio**, e as folhas defensivas (`ShadowBall`, `MarkOpponent`) são síncronas e nem têm esse método. O último `RobotGoal` continua publicado e o controlador o segue. Funciona quando o novo ramo publica seu próprio alvo logo em seguida; mas se o novo ramo não publica nada (por exemplo, uma ação de espera), o robô **continua indo para o alvo antigo**.

Uma segunda consequência do mesmo desenho: quando o `robot_id` do `GoToPoint` não é o do processo, a folha devolve **SUCCESS** sem fazer nada. É o que permite árvores "multi-robô", como as dos desafios, mas esconde erros de configuração.

**Solução:** `onHalted` publicando o alvo "ficar onde está" e uma folha `HoldPosition` para esperas (Capítulos 17 e 21).

## Código morto e árvores sobrepostas

- As flags **`is_corner_kick`, `is_kick_in` e `is_opponent_foul`** são lidas pelo mestre mas **nunca escritas** por nenhum código — um comentário no XML diz que são "resolvidas no C++", o que não é verdade. `IsValueTrue` devolve FAILURE quando a chave não existe, e os ramos ficam permanentemente inativos.
- `is_free_kick` só considera `DIRECT_FREE` (8/9) e compara com a cor **real** (`is_yellow_`), sem considerar `invert_sides`.
- **IDs duplicados**: `MainTree` aparece em oito arquivos e `Desafio1/2/3` em dois. Como o registro percorre o diretório numa ordem não especificada, qual definição vale depende do sistema de arquivos; falhas de registro viram apenas aviso no log.
- `HasLineOfSight` é um *stub* que sempre devolve SUCCESS; `a_star_planner` existe mas não é compilado (a opção `astar` cai silenciosamente no D\*); `follow_ball_node.cpp` está inteiramente comentado.

**Solução:** limpar e separar as árvores de produção das legadas (Capítulo 24) e consolidar free kicks, laterais e escanteios em uma só subárvore (Capítulo 18).

## Resumo

| Ponto | Consequência | Resolvido em |
|---|---|---|
| TIMEOUT e BALL_PLACEMENT sem ramo | robôs jogam com o jogo parado | Cap. 15, 16, 18 |
| NORMAL_START sem contexto | pênalti/kick-off executados pelo jogo corrido | Cap. 15 |
| STOP com KeepDistance inoperante | atacante age em STOP | Cap. 17, 21 |
| Dados sem idade e sem watchdog | robô se move com a visão caída ou a BT travada | Cap. 17 |
| Sem teto de 0,75 m/s; chute sem clamp em PrecisionKick | faltas de velocidade | Cap. 17 |
| Coordenadas literais e lado fixo | amarelo e azul se comportam diferente; 2º tempo errado | Cap. 15, 20 |
| Goleiro e papéis fixos | sem goleiro alternativo, sem degradação | Cap. 19, 20 |
| `onHalted` vazio | preempção não pára o movimento | Cap. 17, 21 |
| Flags nunca escritas, IDs duplicados | árvores mortas, registro ambíguo | Cap. 18, 24 |
