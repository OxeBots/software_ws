# O jogo corrido

Em `RUN` (que começa com um `FORCE_START` ou quando a bola entra em jogo depois de um reinício), a partida é jogada pelos três papéis. Este capítulo descreve a subárvore `NormalPlayTree`, as adaptações necessárias em cada papel e como o time se degrada quando perde robôs.

## NormalPlayTree

A árvore ({{fig:arvore_normalplay}}) é um `ReactiveFallback` com um ramo por papel:

![NormalPlayTree: um ramo por papel, mais uma rede de segurança](figuras/arvore_normalplay.png)

```xml
<BehaviorTree ID="NormalPlayTree">
  <ReactiveFallback name="Roles">
    <ReactiveSequence name="GoalkeeperRole">
      <HasRole role="goalkeeper"/>
      <SubTree ID="GoalkeeperTree" _autoremap="true"/>
    </ReactiveSequence>
    <ReactiveSequence name="AttackerRole">
      <HasRole role="attacker"/>
      <SubTree ID="AttackerTree" _autoremap="true"/>
    </ReactiveSequence>
    <ReactiveSequence name="DefenderRole">
      <HasRole role="defender"/>
      <SubTree ID="DefenderTree" _autoremap="true"/>
    </ReactiveSequence>
    <Halt reason="idle"/>
  </ReactiveFallback>
</BehaviorTree>
```

Duas mudanças em relação ao mestre atual merecem atenção. Primeiro, a **identificação do papel** passa a ser feita por uma única condição, `HasRole`, que substitui as três verificações diferentes de hoje (`IsRobotId 0`, `IsMyRole attacker`, `IsMyRole defender`) e deixa de depender de um identificador fixo. Segundo, o último filho — `Halt idle` — significa que um robô **sem papel** (por exemplo, um robô extra, ou quando o atribuidor ainda não se manifestou) **fica parado**, em vez de ir fazer algo.

## O atacante

A lógica do atacante (Capítulo 9) é reaproveitada integralmente, extraída para a subárvore `AttackerTree`. As mudanças são pequenas:

- **Sem `PrecisionKick`.** Todo chute passa por `KickBall` (ou `KickOnce`), ambos limitados a 3 m/s.
- **`ball_in_enemy_half` consciente do lado.** `UpdateBallPosition` deixa de usar `ball_x > 0` e passa a usar o `side_sign`.
- **Falha em vez de espera muda.** Sem dados, `UpdateBallPosition` e `CalculateInterception` devolvem FAILURE com log (hoje devolvem RUNNING), para que o problema apareça.

## O defensor

A `DefenderTree` (Capítulo 10) também é mantida, com três ajustes:

- a verificação de papel passa a ser `HasRole defender`;
- `ShadowBall` e `MarkOpponent` ganham um `onHalted` que publica "fique onde está" (ou são encapsuladas em uma ação assíncrona), para que a preempção realmente pare o robô;
- a velocidade da bola passa a vir da **predição do Kalman** em vez da diferença finita, reduzindo o ruído do posicionamento.

## O goleiro

A folha `Goalkeeper` recebe as mudanças mais substanciais, porque o regulamento coloca regras específicas sobre ele:

1. **Identidade vinda do árbitro.** O goleiro é o robô cujo identificador o Game Controller informa (`TeamInfo.goalkeeper`, também em `GameState.our_goalkeeper_id`), e não mais o robô 0. Se esse identificador não corresponde a nenhum robô ativo, **não há goleiro**, e o defensor **não** pode ocupar a área (regra: só o goleiro pode estar na própria área).
2. **Um parâmetro de modo.** A folha ganha a porta `mode` (`normal`, `penalty_def`, `hold`). `penalty_def` mantém a linha de gol (Capítulo 18).
3. **Limite de 10 s com a bola.** Uma condição `BallHeldTimer` detecta a bola **parada dentro da área** por mais de 8 s (margem de 2 s sobre os 10 s do regulamento); ao disparar, o goleiro passa a priorizar o afastamento (o estado 1 do Capítulo 10, com maior urgência).
4. **Falhar em vez de esperar.** Se faltar dado por mais de 500 ms, devolve FAILURE (hoje, RUNNING mudo).

## Degradação com menos robôs

O número de robôs em campo **muda** durante a partida: cartões amarelos e vermelhos reduzem o número permitido (a equipe tem 10 s para retirar o excedente), robôs podem ser retirados por defeito, e a visão pode "perder" um robô. O sistema precisa continuar coerente com 3, 2 ou 1 robôs ({{fig:degradacao_papeis}}).

![Os papéis com 3, 2 e 1 robôs ativos](figuras/degradacao_papeis.png)

| Robôs ativos | Papéis | Observação |
|---|---|---|
| 3 | goleiro, atacante, defensor | operação normal |
| 2 | goleiro + atacante | o atacante **recua** (assume uma postura defensiva) quando a bola está no nosso campo |
| 1 | goleiro | permanece na linha de gol |
| 2 (sem goleiro) | atacante + defensor | o defensor não entra na área; o time joga "sem goleiro" |

A lista de robôs ativos (`active_ids`) é calculada pelo atribuidor de papéis a partir de três fontes: o que a visão vê (com a idade dos dados), o `max_allowed_bots` do árbitro e, no futuro, as flags de erro da telemetria dos robôs. Quando o `max_allowed_bots` fica abaixo do número de robôs ativos, o atribuidor indica **qual** robô deve ser retirado e o mantém parado; a retirada física é feita por um humano da equipe (um dos poucos momentos em que o regulamento permite).

!!! note "Quando um robô é substituído"
    A substituição de robôs, em si (o *robot handler* entra no campo, retira ou coloca robôs) está fora do software. O que o software faz é **reagir**: o atribuidor atualiza `active_ids` e a árvore vê o papel mudar no tick seguinte.
