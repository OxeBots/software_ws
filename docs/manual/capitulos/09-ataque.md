# O atacante

O atacante é o robô que disputa e conduz a bola. Sua lógica é a mais elaborada do sistema e reúne, em um só ramo, quase todas as técnicas vistas até aqui: preparação de dados, predição, movimento com planejamento, movimento em linha reta, verificação de condições e chute. Este capítulo explica **como** o atacante decide, começando pelas folhas que preparam os dados e terminando pela árvore completa.

## UpdateBallPosition: o ponto de pré-chute

`UpdateBallPosition` é uma ação cujo trabalho é **preparar dados para o resto do ramo**; ela sempre devolve SUCCESS quando tem dados. A cada tick ela:

- lê a posição real da bola e escreve `ball_x`, `ball_y` e `ball_in_enemy_half` (`ball_x > 0`);
- calcula o **ponto de pré-chute** (`pre_kick_x`, `pre_kick_y`): um ponto sobre a reta que liga o gol alvo à bola, **400 mm atrás da bola** (do lado oposto ao gol);
- decide se o robô está **pronto para chutar** (`is_ready_to_kick`), usando uma histerese: para *entrar* no estado "pronto", o robô precisa estar a menos de 150 mm do ponto de pré-chute; para *permanecer* pronto, basta estar a menos de 600 mm. Em ambos os casos, é preciso estar do lado certo da bola (produto escalar positivo), isto é, atrás dela em relação ao gol.

A histerese evita que a decisão oscile quando o robô está na fronteira: sem ela, o estado "pronto" ligaria e desligaria a cada tick, e o robô hesitaria.

## CalculateInterception: onde a bola vai estar

Perseguir a posição *atual* da bola faz o robô sempre chegar atrasado quando ela se move. `CalculateInterception` calcula, em vez disso, **onde interceptá-la**, com um algoritmo de busca simples e robusto.

### A busca pelo ponto de interceptação

O nó assina as predições do Kalman (`ball_predicted`, `robot_predicted`) e, para instantes `t` de 0,05 s a 3 s (passos de 0,05 s), faz duas perguntas:

1. *Onde a bola estará em `t`?* Usa o movimento com aceleração (a bola desacelera pelo atrito do carpete) e, se ela já parou antes de `t`, considera o ponto final.
2. *Consigo chegar lá em `t`?* Calcula o tempo de deslocamento do robô até aquele ponto com um perfil trapezoidal de velocidade (aceleração máxima de 2000 mm/s², velocidade máxima de 1500 mm/s), levando em conta a velocidade atual do robô na direção do alvo (se ele está indo para o lado contrário, primeiro precisa frear).

O **primeiro `t` em que o robô consegue chegar a tempo** define o ponto de interceptação. Se nenhum serve, o alvo é o ponto onde a bola para.

Um cuidado importante: com a bola parada, o ruído do filtro (alguns cm/s) seria amplificado por essa busca de até 3 s, fazendo o ponto "pular" a cada tick. Por isso há uma **banda-morta**: se a velocidade da bola é menor que 150 mm/s, a velocidade e a aceleração são zeradas e o ponto de interceptação passa a ser a própria posição da bola.

### Os pontos de saída

A partir do ponto de interceptação, o nó calcula uma família de pontos, todos sobre a reta bola–gol, ilustrados na {{fig:pontos_ataque}}:

![Os pontos calculados em torno da bola (a) e o contorno quando o robô está do lado errado (b)](figuras/pontos_ataque.png)

| Saída | Onde fica | Para que serve |
|---|---|---|
| `intercept_x/y` | onde interceptar a bola | alvo da aproximação "pura" |
| `intercept_pk_x/y` | 400 mm atrás do ponto de interceptação | pré-chute: de onde o robô arranca já alinhado |
| `intercept_pk_safe_x/y` | igual ao pré-chute, **ou** um ponto de contorno lateral | alvo da fase 1 |
| `intercept_capture_x/y` | 115 mm atrás da bola | **captura**: ponto onde o robô encosta alinhado |
| `intercept_carry_x/y` | 120 mm **além** do centro da bola, do lado do gol | **carga**: alvo de condução (ver abaixo) |
| `intercept_carry_face_x/y` | 400 mm à frente da bola, rumo ao gol | para onde o robô **olha** ao conduzir |
| `is_ready_to_kick` | — | mesma histerese de prontidão |

O **ponto de contorno** (`pk_safe`) merece atenção. O planejador D\* evita colidir com a bola, mas não tem noção de *por qual lado* contorná-la para chegar *atrás* dela. Se o robô já está do lado do gol, ir direto ao pré-chute o faria passar pela frente da bola. Então, enquanto o robô está do lado errado, o alvo é um ponto deslocado **600 mm lateralmente** (perpendicular à reta bola–gol, do lado em que o robô já está), forçando o D\* a rodear a bola. Uma histerese de 80 mm evita que o contorno ligue e desligue na fronteira.

O ponto de **carga** ficar *além* da bola é deliberado: como a velocidade do controlador é proporcional à distância ao alvo, mirar além do ponto de contato mantém uma velocidade de empurrão mais alta com o mesmo controlador proporcional. Já o ponto de **mira** da carga é recalculado a cada tick sobre a posição bruta da bola (e não sobre a predição), para evitar que o alvo de orientação deslize para a frente da bola durante o empurrão.

## IsBallClose e KickBall

- **`IsBallClose`** é uma condição: verdadeira se a distância do robô à bola (da posição **real**, não da predita) é menor que `distance_threshold` e, se `angle_threshold_deg > 0`, se o desvio entre a frente do robô e a bola é menor que esse ângulo. A checagem de ângulo existe porque estar "perto" não basta: a bola pode estar ao alcance em distância e fora do cone de contato do chutador — o que produzia chutes inconsistentes.
- **`KickBall`** pede o chute ao controlador (`MODE_KICK`, no máximo 3 m/s) e devolve SUCCESS quando o controlador conta um chute concluído (Capítulo 7).

## A árvore do atacante

O ramo `AttackerRole` do mestre atual, `master_strategy_carry.xml`, é uma `ReactiveSequence` com a condição de papel e um laço ({{fig:arvore_atacante_atual}}):

![O laço do atacante: preparar dados, calcular a interceptação e executar ChaseAndKick](figuras/arvore_atacante_atual.png)

1. A guarda `IsMyRole = attacker` é reavaliada a cada tick: se o atribuidor de papéis troca o atacante, o ramo é interrompido.
2. O laço `AttackerLogicLoop` (uma `ReactiveSequence` dentro de um `RetryUntilSuccessful(-1)`) executa `UpdateBallPosition`, `CalculateInterception` e a árvore de ações a **cada tick**, de modo que os pontos de saída estão sempre atualizados.
3. `ChaseAndKick` é uma `Sequence` com três passos:
   - **Fase 1 — aproximação.** `GoToPoint` até o ponto de pré-chute seguro (tolerância de 120 mm), com o planejador D\* e `ball_contact_threshold_mm=150`: se a bola chegar perto demais no caminho, a folha **falha de propósito**, o que obriga a árvore a recalcular tudo a partir da posição real da bola.
   - **Fase 2 — `ApproachAndKick`**, descrita a seguir.
   - **Cooldown.** Um `Delay` de 600 ms (com `AlwaysSuccess`) impede que o atacante reinicie o ciclo imediatamente após um chute.

### ApproachAndKick: três comportamentos por prioridade

`ApproachAndKick` é um `ReactiveFallback` ({{fig:arvore_approach_and_kick}}): a cada tick, tenta primeiro o comportamento de maior prioridade.

![ApproachAndKick: chutar, realinhar ou conduzir](figuras/arvore_approach_and_kick.png)

1. **Shoot** (chutar): vale quando a bola **não** está na nossa metade, o robô está perto (140 mm) e alinhado (10°). Executa `KickBall`.
2. **Realign** (realinhar): quando a bola está na metade adversária mas o robô ainda não está em posição de chute, ele vai ao **ponto de captura** em linha reta, olhando para a mira. É uma `ReactiveSequence`: se a condição `Inverter(IsBallInOurHalf)` deixar de valer, o comportamento é interrompido.
3. **Carry** (conduzir): quando a bola está **na nossa metade**, em vez de chutar, o robô a **conduz** em direção à metade adversária, empurrando-a até o ponto de carga, em linha reta e com `ball_side_check=true` (se o robô acabar do lado errado da bola, a folha falha e tudo recomeça pela fase 1).

A figura abaixo resume as quatro fases em termos de geometria:

![As quatro fases do atacante em torno da bola](figuras/fases_atacante.png)

!!! note "Como a árvore 'recomeça do zero'"
    Muitas folhas de movimento do atacante usam *falhas intencionais* (`ball_contact_threshold_mm`, `ball_side_check`) como mecanismo de recuperação: quando a situação física muda de modo que o plano em curso deixa de fazer sentido, o `GoToPoint` falha, a falha sobe pela `Sequence` e pelo `ReactiveFallback`, o `RetryUntilSuccessful` reinicia o laço, e `CalculateInterception` recomputa os pontos com a posição real da bola. É uma forma de "replanejar" usando apenas a semântica da árvore.

### Sobre `IsBallInOurHalf`

A condição usa o `my_goal_x` da blackboard para saber de que lado fica "a nossa metade" e adota uma **histerese de 100 mm** em torno do meio-campo, com memória do último estado, para a decisão não oscilar com a bola sobre a linha central. (Atenção: como tem memória interna, o estado da condição não é limpo entre ativações.)

## PrecisionKick (legado)

Existe uma folha anterior, `PrecisionKick`, que gira, avança e chuta sozinha, publicando comandos de velocidade diretamente. Ela aparece apenas em árvores antigas e **não** em `master_strategy_carry.xml`. Duas razões a tornam inadequada para o jogo completo: ela escreve direto em `/robot_commands` (disputando o canal com o controlador) e **não limita** a velocidade do chute. O Capítulo 21 recomenda aposentá-la em favor de `KickOnce`.
