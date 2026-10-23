# Segurança e parada

Os quatro primeiros ramos da Master Tree formam o **bloco de segurança**: dados confiáveis, HALT, TIMEOUT e STOP. Este capítulo descreve cada um, e também o **SafetyGate**, o mecanismo que garante a segurança *mesmo quando a árvore falha*.

## O princípio: segurança em duas camadas

Uma árvore reativa é uma boa defesa — mas depende de que o processo da árvore esteja vivo, ticando e correto. Se o `strategy_node` travar, entrar em *crash* ou ficar preso esperando algo, a árvore **não consegue** mandar o robô parar, e o controlador (como visto no Capítulo 13) continuaria seguindo a última rota. Por isso a segurança é construída em **duas camadas independentes**:

1. **Na árvore**: o ramo `SafetyGuard` e os ramos de HALT/STOP preemptam qualquer comportamento.
2. **No controlador**: o *SafetyGate* aplica limites e zera os comandos por conta própria, usando o `GameState` e um relógio local.

## O SafetyGuard e o modo degradado

O primeiro ramo da Master verifica se os dados ainda são confiáveis. A guarda é `Inverter(IsDataFresh)`: o ramo casa **quando os dados não estão frescos**. A condição `IsDataFresh` compara três idades, mantidas na blackboard:

| Dado | Limite padrão | Fonte da idade |
|---|---|---|
| Mensagem do Game Controller (`gc_age_ms`) | 500 ms | carimbo do `GameState` / flag `stale` |
| Pose do próprio robô (`pose_age_ms`) | 150 ms | carimbo de `GameData` |
| Bola (`ball_age_ms`) | 300 ms | carimbo de `GameData` |

(Os limites são propostas iniciais, a calibrar em simulação: a visão chega a cerca de 60 Hz, ou seja, um período de ~17 ms.) Se qualquer idade ultrapassar o limite, `IsDataFresh` devolve FAILURE, o `Inverter` o transforma em SUCCESS, e o ramo executa a `DegradedModeTree`, que contém apenas a ação `Halt` com o motivo `stale_data`.

```xml
<BehaviorTree ID="DegradedModeTree">
  <Halt reason="stale_data"/>
</BehaviorTree>
```

Quando os dados voltam, o ramo deixa de casar e os de baixo recomeçam do `onStart`: cada folha recalcula o alvo com os dados novos. Nenhum estado velho é "retomado".

## HALT e TIMEOUT

Os ramos de HALT e TIMEOUT são os mais simples possíveis: uma guarda de fase e a ação `Halt`.

- **`HaltSubTree`** (já existente): `Halt` com o motivo `gc_halt`. A cada tick, a ação publica `MODE_HALT` ao controlador, que zera as velocidades. O regulamento dá 2 s de tolerância para frear; a meta do projeto é parar em menos de 300 ms.
- **`TimeoutTree`** (nova): `Halt` com o motivo `timeout`. Durante o timeout, as equipes podem mexer no hardware; o software só precisa manter o robô quieto.

O fato de serem triviais é proposital: o caminho do HALT precisa ser o mais curto e o menos propenso a falhas de todo o sistema.

## STOP

O STOP é o estado mais frequente em uma partida e o que exige mais cuidado. Pelo regulamento, em STOP o robô deve: andar a **menos de 0,75 m/s**, ficar a **pelo menos 0,5 m da bola**, **não tocar a bola** e, ainda, ficar a **0,2 m da área de defesa adversária** (para evitar uma falta de proximidade). A `StopSubTree` proposta ({{fig:arvore_stop}}) implementa isso:

![A StopSubTree proposta](figuras/arvore_stop.png)

```xml
<BehaviorTree ID="StopSubTree">
  <ReactiveSequence name="StopLogic">
    <SetMotionLimit limit_mps="0.75"/>
    <ReactiveFallback name="StopAction">
      <ReactiveSequence name="RetreatIfClose">
        <IsBallClose robot_id="{robot_id}" distance_threshold="650.0"/>
        <ComputeLegalSlot slot="retreat" index="0"
                          slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}"
                   face_x="{ball_x}" face_y="{ball_y}" tolerance="80.0"/>
      </ReactiveSequence>
      <HoldPosition robot_id="{robot_id}"/>
    </ReactiveFallback>
  </ReactiveSequence>
</BehaviorTree>
```

Lendo a árvore:

1. **`SetMotionLimit 0.75`** informa ao SafetyGate o teto de velocidade desta fase (redundante com o `GameState`, mas explícito).
2. **`RetreatIfClose`**: se a bola está a menos de 650 mm (os 500 mm do regulamento mais uma margem de 150 mm), calcula um **ponto legal de recuo** (`ComputeLegalSlot` com o slot `retreat`: um ponto sobre a reta bola→robô, a 650 mm da bola, dentro do campo e fora das áreas) e vai até ele olhando para a bola.
3. **`HoldPosition`**: se já está longe da bola, **fica onde está** — publica um objetivo na própria pose.

O resultado é um robô que se afasta da bola só quando necessário e, o resto do tempo, está parado; e que **nunca** devolve FAILURE por falta de uma porta.

!!! note "E o goleiro?"
    O goleiro usa a mesma `StopSubTree`. O ponto de recuo, para ele, é limitado à própria área (como em qualquer `GoToPoint` do goleiro): se a bola está perto da meta, o goleiro recua para dentro da área mantendo, quando possível, 0,5 m da bola.

## O SafetyGate

O SafetyGate é um estágio no final do `movement_calculation_node`, **depois** de todo o cálculo de velocidade (seguimento de rota, repulsão, clamp de área) e **antes** de publicar em `/robot_commands` ({{fig:safety_gate}}).

![O SafetyGate: quatro verificações independentes sobre o comando final](figuras/safety_gate.png)

Ele aplica quatro regras, todas independentes da árvore:

1. **HALT zera a velocidade.** Se o `GameState` indica `HALT` (ou `TIMEOUT`), o comando é zero, mesmo que um override ou uma rota digam o contrário.
2. **Teto de velocidade por fase.** O módulo do vetor (vx, vy) é limitado a `speed_limit_mps` do `GameState`: 0,75 m/s nos estados de parada, 1,5 m/s no jogo. É este mecanismo que supre a lacuna do limite de STOP.
3. ***Watchdog***. Se o controlador não recebe um objetivo ou um override há mais de 500 ms, zera os comandos e informa `MODE_HALT` no status. Ao contrário do comportamento atual (continuar na última rota), uma árvore silenciosa **pára o robô**.
4. **Limite do chute.** `kick_speed` é limitado a 3,0 m/s para qualquer origem, inclusive folhas legadas que esqueçam de limitar.

As regras 1 e 3 usam apenas informações locais ao controlador (o último `GameState` recebido e um relógio), de modo que funcionam mesmo se o `strategy_node` não existir mais.

!!! warning "Coerência com o override de 200 ms"
    O override de parada (`MODE_HALT`) já expira em 200 ms. Com o watchdog de 500 ms, a ordem é: se a árvore continua renovando o override, o robô fica parado; se pára de renová-lo, o override expira, o controlador volta a seguir a rota **por até 300 ms** e então o watchdog zera tudo. Para eliminar essa janela, o plano de implementação propõe fazer o `MODE_HALT` **não** expirar por TTL, mas apenas ser liberado explicitamente (ou pelo watchdog).

## As folhas deste capítulo

| Folha | Tipo | Resumo |
|---|---|---|
| `IsDataFresh` | condição | falha se alguma idade (GC, pose, bola) ultrapassa o limite |
| `CheckGameState` | condição | verdadeira se a fase da blackboard é a pedida |
| `SetMotionLimit` | ação síncrona | informa o teto de velocidade ao SafetyGate |
| `HoldPosition` | ação assíncrona | publica a pose atual como objetivo; fica em RUNNING |
| `ComputeLegalSlot` | ação síncrona | calcula um ponto legal para um "slot" nomeado |

Seus contratos completos estão no Capítulo 21.
