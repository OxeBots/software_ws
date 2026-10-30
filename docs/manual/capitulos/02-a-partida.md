# A partida SSL-EL

Este capítulo apresenta o jogo do ponto de vista do software. Ele resume o que o regulamento da SSL-EL (edição de agosto de 2024) exige dos robôs e, principalmente, **traduz cada regra em uma obrigação concreta** que a estratégia precisa cumprir. Quando o texto diz "o regulamento determina", trata-se de uma exigência da liga; quando diz "o software deve", trata-se da consequência prática para o nosso código.

## O campo, a bola e os robôs

A SSL-EL é a categoria de entrada da Small Size League. O campo é menor que o das divisões regulares: a **área de jogo mede 4,5 m × 3 m**, cercada por uma margem de 0,5 m e por uma parede de 10 cm de altura, totalizando 5,5 m × 4 m ({{fig:campo_dimensoes}}). Todas as linhas têm 1 cm de largura. A superfície é de feltro ou carpete verde.

![O campo da SSL-EL com suas dimensões (em mm)](figuras/campo_dimensoes.png)

Os elementos do campo que mais importam para a estratégia são:

- **Linhas de lateral** (*touch lines*): as duas linhas longas.
- **Linhas de fundo** (*goal lines*): as duas linhas curtas, onde ficam os gols.
- **Linha de meio-campo**, que divide o campo em duas metades, e o **círculo central**, com 1 m de diâmetro.
- **Áreas de defesa**: retângulos de 1,35 m × 0,5 m junto a cada gol. Elas têm regras especiais de entrada, como veremos.
- **Gols**: 0,8 m de abertura e 0,18 m de profundidade.

Cada equipe tem **no máximo 3 robôs**, e um deles pode ser o goleiro. O identificador do goleiro é escolhido antes da partida e só pode ser alterado quando a bola está fora de jogo ou na metade adversária. Os robôs cabem em um cilindro de 18 cm de diâmetro por 15 cm de altura e não podem ativar nenhum dispositivo de condução de bola (*dribbler*); o chute, porém, é permitido. A bola é uma bola de golfe laranja, com 43 mm de diâmetro.

## Software compartilhado: visão, árbitro e árbitros automáticos

Toda a liga usa a mesma infraestrutura de software, mantida pela comunidade:

- **SSL-Vision**: câmeras compartilhadas sobre o campo calculam a posição e a orientação da bola e dos robôs e as enviam por rede (multicast). As equipes não podem montar câmeras ou sensores externos próprios. Os dados reais têm ruído, atraso e falhas ocasionais de detecção — o software precisa tolerar isso.
- **Game Controller (GC)**: um programa operado por um humano (o *game controller operator*) que traduz as decisões do árbitro humano e dos **árbitros automáticos** em mensagens de rede. Ele mantém o estado do jogo, registra os eventos e serve de intermediário entre todos os participantes. É dele que vem o **comando do árbitro** que a nossa estratégia lê.
- **Árbitro automático** (*autoref*): programa que detecta infrações (bola fora do campo, faltas) e as reporta ao GC.
- **Controle remoto**: dispositivo opcional com o qual o operador do time pede timeout, troca de robô ou parada de emergência, e levanta a bandeira de contestação.

## As etapas da partida

Uma partida regular tem dois tempos de **300 segundos de jogo** separados por um intervalo de 300 segundos. Em partidas eliminatórias empatadas há prorrogação (dois tempos de 150 s, com 120 s de intervalo) e, persistindo o empate, uma disputa de pênaltis ({{fig:linha_do_tempo_partida}}).

![As etapas de uma partida SSL-EL](figuras/linha_do_tempo_partida.png)

Um detalhe com consequências práticas: **o relógio da partida pára** sempre que nenhuma equipe pode manipular a bola — durante STOP, HALT, a preparação de kick-off ou pênalti e o *ball placement*. Por isso uma partida de 10 minutos de jogo dura bem mais do que 10 minutos de relógio, e cada transição entre estados acontece muitas vezes por jogo. A estratégia passa uma fração enorme do tempo **não jogando**, mas posicionando-se corretamente para o próximo reinício.

Cada equipe tem direito a 4 timeouts, num total de 420 segundos (na prorrogação, 2 timeouts e 240 s). Timeouts só ocorrem com o jogo parado e, durante eles, as duas equipes podem mexer livremente no hardware e no software.

## Os comandos do árbitro

O Game Controller comunica o estado do jogo por meio de **comandos**. Cada comando define se os robôs podem se mover, a que velocidade, se podem tocar na bola e para onde devem ir. Entender esse vocabulário é pré-requisito para tudo o que vem depois.

### HALT

*"Ninguém se move."* Ao receber HALT, nenhum robô pode se mover nem manipular a bola. Existe uma **tolerância de 2 segundos** para os robôs frearem. O HALT é o comando de emergência: é usado quando algo dá errado (um robô fora de controle), quando humanos entram no campo e quando uma equipe pede substituição de robô. Ele é **sempre seguido de um STOP**, e o GC aguarda até 10 s após o HALT antes de retomar o jogo, dando tempo para as equipes se prepararem.

### STOP

*"Continuem se movendo, devagar, longe da bola."* No STOP, todos os robôs precisam reduzir a velocidade para **menos de 0,75 m/s**, manter pelo menos **0,5 m de distância da bola** e não manipulá-la. O STOP é usado depois que a bola sai do campo, quando ocorre uma falta e para preparar qualquer reinício. O limite de velocidade e a distância mínima existem para que o árbitro (humano) possa colocar a bola com segurança. É suficiente que fique claro ao árbitro que o robô está fazendo o possível para respeitar a distância — se a bola se move rápido, não é razoável exigir perfeição.

### BALL_PLACEMENT

Depois de uma parada, a bola precisa ser colocada na posição correta, que depende do evento ocorrido. A forma preferida é o **posicionamento automático**: os robôs de uma das equipes empurram a bola até a posição designada, sem intervenção humana ({{fig:geometria_stop_placement}}, painel b). O comando BALL_PLACEMENT informa qual equipe deve colocar a bola e a posição-alvo. As regras determinam:

- O posicionamento tem **30 segundos** para ser concluído. É considerado bem-sucedido quando a bola está parada a no máximo 0,15 m do alvo e nenhum robô está perto demais dela.
- Os robôs da equipe que **não** está colocando a bola devem ficar a **no mínimo 0,5 m da linha entre a bola e o alvo** (a zona proibida tem formato de estádio). Interferir é falta.
- Na SSL-EL, uma equipe pode decidir **não** colocar a bola pelo resto do jogo (basta avisar o árbitro); nesse caso a equipe adversária ou o próprio árbitro faz o posicionamento.

![STOP (a) e BALL_PLACEMENT (b)](figuras/geometria_stop_placement.png)

### Comandos de preparação e reinício

Para retomar o jogo, o GC emite primeiro um comando de **preparação** (os robôs vão para as posições do reinício) e depois um comando que **autoriza a jogada**. Os pares são:

| Situação | Preparação | Autorização |
|---|---|---|
| Kick-off (início de tempo, depois de um gol) | `PREPARE_KICKOFF_YELLOW/BLUE` | `NORMAL_START` |
| Pênalti | `PREPARE_PENALTY_YELLOW/BLUE` | `NORMAL_START` |
| Falta, lateral, escanteio, tiro de meta | (STOP) | `DIRECT_FREE_YELLOW/BLUE` |
| Jogo recomeça sem favorecimento | (STOP) | `FORCE_START` |

Note um ponto sutil que reaparece várias vezes neste manual: o comando **`NORMAL_START` é o mesmo** para o kick-off e para o pênalti. O que diferencia os dois é o comando de preparação que veio *antes*. Isso significa que quem lê apenas "o comando atual" não consegue saber, em `NORMAL_START`, qual reinício está acontecendo — é preciso **lembrar** o contexto.

### Kick-off

A bola é colocada no centro do campo pelo árbitro humano. No comando de preparação, **todos os robôs devem estar na própria metade do campo e fora do círculo central**; apenas **um robô da equipe que bate** (o *kicker*) pode ficar dentro do círculo. Nenhum robô toca a bola até o `NORMAL_START`; depois dele o kicker pode manipulá-la, e um gol direto do kick-off é válido ({{fig:geometria_kickoff_penalty}}, painel a). Os dois tempos e as eventuais prorrogações começam com kick-off, assim como o jogo depois de cada gol (batido pela equipe que sofreu o gol).

### Free kick

A posição da bola depende do evento que originou a falta, mas deve estar a pelo menos 0,2 m de qualquer linha e 1 m de qualquer área de defesa; se o evento exigir uma posição inválida, usa-se a posição válida mais próxima. Quando o `DIRECT_FREE` é emitido, os robôs da equipe favorecida podem se aproximar da bola, e **um deles** (o kicker) pode manipulá-la; os adversários continuam a **no mínimo 0,5 m da bola**. Um gol direto é válido. Throw-in (lateral), tiro de meta e escanteio são todos **mapeados para free kicks** — não existem comandos próprios para eles.

![Free kick: o cobrador, a distância mínima dos adversários e a faixa de 0,2 m ao redor da área de defesa adversária](figuras/geometria_freekick.png)

### Force start

Retoma o jogo imediatamente, com ambas as equipes livres para se aproximar e manipular a bola. É usado em situações sem favorecido claro — por exemplo, quando o jogo é parado sem motivo específico ou quando as duas equipes cometem falta.

### Pênalti

O pênalti é o reinício mais regrado. O árbitro coloca a bola na marca de pênalti. No comando de preparação, o **goleiro defensor deve ir para a linha de gol e tocá-la**; um robô atacante pode se aproximar da bola, mas **sem tocá-la**; e todos os outros robôs, de ambas as equipes, devem ficar **1 m atrás da bola**, de modo a não interferir ({{fig:geometria_kickoff_penalty}}, painel b). No `NORMAL_START`, o atacante pode tocar a bola, que **só pode se mover em direção ao gol adversário**. O goleiro defensor fica livre para se mover quando a bola entra em jogo, e se a bola ainda estiver em jogo após 10 segundos o jogo é parado.

![Kick-off (a) e pênalti (b)](figuras/geometria_kickoff_penalty.png)

Um gol de pênalti **não** é concedido se a bola cruzar as linhas fora do gol, se o goleiro desviar a bola mudando sua direção em 90° ou mais, se o time atacante cometer qualquer falta ou se a bola ainda estiver em jogo após 10 s. Se a equipe defensora cometer qualquer falta durante o pênalti, recebe cartão vermelho e o pênalti é repetido.

## A bola em jogo e fora de jogo

Enquanto o jogo está parado, a bola está **fora de jogo**. Ela entra **em jogo** quando: houve um FORCE_START; a bola se moveu pelo menos 0,05 m depois de um kick-off, free kick ou pênalti; ou passaram 10 segundos depois de um kick-off ou free kick. Esse critério importa para a estratégia porque define o momento em que as restrições do reinício terminam (por exemplo, a distância mínima de 0,5 m dos adversários).

Quando a bola sai do campo cruzando completamente uma linha, o jogo é parado e reiniciado com um free kick para o adversário de quem tocou nela por último, com a bola na posição prevista pelo evento (lateral: 0,2 m da linha de lateral; tiro de meta: 0,2 m da lateral e 0,5 m da linha de fundo; escanteio: 0,2 m de ambas). Um *chute sem alvo* (a bola cruza o meio-campo e depois a linha de fundo adversária, sem tocar outro robô) também é devolvido como free kick.

## Faltas e sanções que o software pode evitar

O regulamento define dezenas de infrações. A maioria exige julgamento humano (empurrar, segurar a bola, desrespeitar árbitros). Mas várias são **objetivamente mensuráveis**, e é exatamente delas que o software deve se proteger:

| Regra | Limite | Observação |
|---|---|---|
| Velocidade do robô | ≤ 1,5 m/s no jogo | falta que não pára o jogo |
| Velocidade do robô no STOP | ≤ 0,75 m/s | 2 s de tolerância; conta uma vez por robô por parada |
| Velocidade da bola após o chute | ≤ 3 m/s (em 3D) | falta que não pára o jogo |
| Distância à bola durante free kick/kick-off do adversário | ≥ 0,5 m | o relógio do adversário é reiniciado se violado |
| Proximidade da área de defesa adversária (STOP e free kick) | ≥ 0,2 m | 2 s de tolerância |
| Tocar a bola dentro da área adversária | proibido (parcial ou total) | falta que não pára o jogo |
| Robô que não é o goleiro dentro da própria área | proibido (melhor esforço) | se tocar a bola totalmente dentro: pênalti |
| Bola retida na área de defesa | ≤ 10 s | goleiro |
| Interferência no ball placement | ≥ 0,5 m do corredor bola→alvo | +10 s no cronômetro de placement |
| Colisão | diferença de velocidade projetada ≤ 0,75 m/s | caso contrário o mais rápido comete falta |

Cada **falta** soma ao contador da equipe, e **toda terceira falta gera um cartão amarelo**. Um cartão amarelo reduz em um o número de robôs permitidos em campo por 120 segundos de jogo; a equipe tem 10 segundos para tirar um robô, e dois cartões amarelos não expirados fazem o terceiro virar vermelho (que não expira). Isso tem uma consequência direta: **o número de robôs ativos pode mudar durante a partida**, e a estratégia precisa se adaptar (veremos a degradação de papéis no Capítulo 19).

## A máquina de estados do jogo

O Apêndice B do regulamento descreve o jogo como uma máquina de estados, reproduzida na {{fig:maquina_estados_gc}}. Há três grandes famílias de estados:

- **Halted** (parado totalmente): `Halt` e `Timeout`.
- **Stopped** (parado com movimento permitido): `Stop`, `BallPlacement`, `PrepareKickoff` e `PreparePenalty`.
- **Running** (jogo): `Run`, `FreeKick`, `Kickoff` e `Penalty`.

![A máquina de estados do jogo segundo o regulamento](figuras/maquina_estados_gc.png)

Qualquer estado pode ir para `Halt` por um comando HALT. Em geral, um reinício passa por `Stop`, vai para um estado de preparação ou de posicionamento e só então entra em um estado de jogo; a bola se mover (ou 10 s) leva de `Kickoff`/`FreeKick` para `Run`.

!!! warning "Comando versus estado"
    A máquina de estados tem mais estados do que o Game Controller tem comandos. O estado `Kickoff`, por exemplo, não é um comando: ele corresponde ao comando `NORMAL_START` que chega depois de um `PREPARE_KICKOFF`. É por isso que a nossa arquitetura de jogo completo (Parte IV) introduz um **estado de jogo derivado**, a *fase*, em vez de reagir diretamente ao número do comando.

## O que o software precisa garantir

Resumindo o capítulo em obrigações do software, uma estratégia de partida inteira precisa:

1. **Parar imediatamente** com HALT, e nunca se mover com o jogo em `Halt` ou `Timeout`.
2. **Limitar a velocidade a 0,75 m/s** e manter **0,5 m de distância da bola** durante STOP e BALL_PLACEMENT (e não interferir no corredor do posicionamento).
3. **Posicionar-se corretamente** para cada reinício, nos dois papéis possíveis (quem bate e quem defende): kick-off, pênalti e free kick.
4. **Lembrar o contexto** de `NORMAL_START` (kick-off ou pênalti).
5. **Respeitar as áreas de defesa**: nenhum robô, exceto o goleiro, na própria; nenhum robô tocando a bola na adversária.
6. **Limitar o chute a 3 m/s** e o robô a 1,5 m/s.
7. **Cuidar do goleiro**: não reter a bola por mais de 10 s na área e, no pênalti defensivo, manter-se na linha de gol.
8. **Adaptar-se** quando o número de robôs ativos mudar (cartões) ou o goleiro estiver ausente.
9. **Comportar-se com segurança** quando faltarem dados (visão ou árbitro).

Cada um desses itens reaparece, com a solução correspondente, na Parte IV. O Apêndice C relaciona cada regra do regulamento ao componente que a trata.
