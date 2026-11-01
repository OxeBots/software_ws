<!-- apendice -->
# Os arquivos XML propostos

Os arquivos abaixo são a **especificação** das árvores da Parte IV. Eles só se tornam executáveis quando os nós novos (marcados com ✦ nas figuras) estiverem implementados e registrados; os nós existentes que usam estão listados no cabeçalho de cada arquivo. As cópias para uso estão em `docs/manual/anexos/xml-proposto/`.

## A árvore mestre (`MainTreeEL`)

Arquivo `master_strategy_el.xml` — referente ao Capítulo 16.

```xml
<?xml version="1.0"?>
<!--
  PROPOSTA — especificação NÃO EXECUTÁVEL até que os nós NOVOS existam e estejam registrados:
  CheckGameState, WeAreFavored, IsDataFresh, HasRole, ComputeLegalSlot, HoldPosition, SetMotionLimit,
  KickOnce, WaitBallInPlay, PlaceBall, ComputePlacementApproach, AvoidPlacementCorridor,
  PenaltyKeeperLine, BallHeldTimer. Nós EXISTENTES usados: ReactiveFallback, ReactiveSequence,
  Sequence, Fallback, Inverter, SubTree, Halt, GoToPoint, IsBallClose, UpdateBallPosition, Goalkeeper.
  Regra: TODA guarda de ramo é ReactiveSequence (reavaliada a cada tick).
  Ver o Capítulo 16 do manual.
-->
<root BTCPP_format="4" main_tree_to_execute="MainTreeEL">
  <BehaviorTree ID="MainTreeEL">
    <ReactiveFallback name="MasterEL">

      <!-- 0. Segurança: dado velho/ausente -> parado -->
      <ReactiveSequence name="SafetyGuard">
        <Inverter>
          <IsDataFresh max_gc_ms="500" max_pose_ms="150" max_ball_ms="300"/>
        </Inverter>
        <SubTree ID="DegradedModeTree" _autoremap="true"/>
      </ReactiveSequence>

      <!-- 1. HALT -->
      <ReactiveSequence name="HaltBranch">
        <CheckGameState phase="HALT"/>
        <SubTree ID="HaltSubTree" _autoremap="true"/>
      </ReactiveSequence>

      <!-- 2. TIMEOUT -->
      <ReactiveSequence name="TimeoutBranch">
        <CheckGameState phase="TIMEOUT"/>
        <SubTree ID="TimeoutTree" _autoremap="true"/>
      </ReactiveSequence>

      <!-- 3. STOP -->
      <ReactiveSequence name="StopBranch">
        <CheckGameState phase="STOP"/>
        <SubTree ID="StopSubTree" _autoremap="true"/>
      </ReactiveSequence>

      <!-- 4. BALL PLACEMENT -->
      <ReactiveSequence name="BallPlacementBranch">
        <CheckGameState phase="BALL_PLACEMENT"/>
        <ReactiveFallback name="PlacementOurOrTheir">
          <ReactiveSequence name="PlacementOur">
            <WeAreFavored/>
            <SubTree ID="BallPlacementOurTree" _autoremap="true"/>
          </ReactiveSequence>
          <SubTree ID="BallPlacementTheirTree" _autoremap="true"/>
        </ReactiveFallback>
      </ReactiveSequence>

      <!-- 5. PREPARE KICKOFF -->
      <ReactiveSequence name="PrepareKickoffBranch">
        <CheckGameState phase="PREPARE_KICKOFF"/>
        <ReactiveFallback>
          <ReactiveSequence>
            <WeAreFavored/>
            <SubTree ID="PrepareKickoffOurTree" _autoremap="true"/>
          </ReactiveSequence>
          <SubTree ID="PrepareKickoffTheirTree" _autoremap="true"/>
        </ReactiveFallback>
      </ReactiveSequence>

      <!-- 6. KICKOFF (NORMAL_START com restart_ctx=KICKOFF) -->
      <ReactiveSequence name="KickoffBranch">
        <CheckGameState phase="KICKOFF"/>
        <ReactiveFallback>
          <ReactiveSequence>
            <WeAreFavored/>
            <SubTree ID="KickoffExecuteOurTree" _autoremap="true"/>
          </ReactiveSequence>
          <SubTree ID="PrepareKickoffTheirTree" _autoremap="true"/>
        </ReactiveFallback>
      </ReactiveSequence>

      <!-- 7. PREPARE PENALTY -->
      <ReactiveSequence name="PreparePenaltyBranch">
        <CheckGameState phase="PREPARE_PENALTY"/>
        <ReactiveFallback>
          <ReactiveSequence>
            <WeAreFavored/>
            <SubTree ID="PreparePenaltyOurTree" _autoremap="true"/>
          </ReactiveSequence>
          <SubTree ID="PreparePenaltyTheirTree" _autoremap="true"/>
        </ReactiveFallback>
      </ReactiveSequence>

      <!-- 8. PENALTY (NORMAL_START com restart_ctx=PENALTY) -->
      <ReactiveSequence name="PenaltyBranch">
        <CheckGameState phase="PENALTY"/>
        <ReactiveFallback>
          <ReactiveSequence>
            <WeAreFavored/>
            <SubTree ID="PenaltyExecuteOurTree" _autoremap="true"/>
          </ReactiveSequence>
          <SubTree ID="PenaltyDefendTheirTree" _autoremap="true"/>
        </ReactiveFallback>
      </ReactiveSequence>

      <!-- 9. FREE KICK (inclui lateral, escanteio, tiro de meta) -->
      <ReactiveSequence name="FreeKickBranch">
        <CheckGameState phase="FREE_KICK"/>
        <ReactiveFallback>
          <ReactiveSequence>
            <WeAreFavored/>
            <SubTree ID="FreeKickOurTree" _autoremap="true"/>
          </ReactiveSequence>
          <SubTree ID="FreeKickTheirTree" _autoremap="true"/>
        </ReactiveFallback>
      </ReactiveSequence>

      <!-- 10. JOGO CORRIDO (FORCE_START / Run) -->
      <ReactiveSequence name="RunBranch">
        <CheckGameState phase="RUN"/>
        <SubTree ID="NormalPlayTree" _autoremap="true"/>
      </ReactiveSequence>

      <!-- 11. Estado desconhecido: parado (seguro por padrão) -->
      <Halt reason="unknown_phase"/>

    </ReactiveFallback>
  </BehaviorTree>
</root>
```

## Subárvores comuns: modo degradado, HALT, TIMEOUT, cobrador e recuo

Arquivo `common.xml` — referente ao Capítulos 17 e 18.

```xml
<?xml version="1.0"?>
<!-- PROPOSTA (não executável até os nós novos existirem). Subárvores comuns: S01, S02, S03, S20, S21 -->
<root BTCPP_format="4">

  <BehaviorTree ID="DegradedModeTree">
    <Halt reason="stale_data"/>
  </BehaviorTree>

  <!-- ID mantido do arquivo existente halt.xml -->
  <BehaviorTree ID="HaltSubTree">
    <Halt reason="gc_halt"/>
  </BehaviorTree>

  <BehaviorTree ID="TimeoutTree">
    <Halt reason="timeout"/>
  </BehaviorTree>

  <!-- Ports: target_x, target_y (alvo do chute), kick_speed (<=3.0) -->
  <BehaviorTree ID="RestartKickerTree">
    <Sequence name="AlignThenKick">
      <UpdateBallPosition robot_id="{robot_id}" goal_x="{target_x}" goal_y="{target_y}"
                          ball_x="{ball_x}" ball_y="{ball_y}"
                          pre_kick_x="{pkx}" pre_kick_y="{pky}"
                          is_ready_to_kick="{rk_ready}" ball_in_enemy_half="{rk_adv}"/>
      <GoToPoint robot_id="{robot_id}" x="{pkx}" y="{pky}"
                 face_x="{target_x}" face_y="{target_y}" tolerance="50.0"
                 ball_contact_threshold_mm="150.0"/>
      <!-- TODO(NV): KickOnce (clamp 3.0 m/s, timeout 10 s, SUCCESS quando a bola move >= 50 mm) -->
      <KickOnce robot_id="{robot_id}" target_x="{target_x}" target_y="{target_y}"
                kick_speed="2.5" timeout_s="10.0"/>
    </Sequence>
  </BehaviorTree>

  <!-- Port: slot (kickoff_def | wall | retreat | ...) -->
  <BehaviorTree ID="RetreatToLegalPositionTree">
    <ReactiveSequence name="Retreat">
      <ComputeLegalSlot slot="{slot}" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
      <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}"
                 face_x="{ball_x}" face_y="{ball_y}" tolerance="80.0"/>
    </ReactiveSequence>
  </BehaviorTree>

</root>
```

## A subárvore de STOP

Arquivo `stop.xml` — referente ao Capítulo 17.

```xml
<?xml version="1.0"?>
<!-- PROPOSTA. Substitui behavior_trees/stop.xml (ID mantido: StopSubTree). Corrige o problema do STOP descrito no Capítulo 13. -->
<root BTCPP_format="4">
  <BehaviorTree ID="StopSubTree">
    <ReactiveSequence name="StopLogic">
      <!-- Regra §5.1.1: < 0,75 m/s (SafetyGate aplica o teto no controlador) -->
      <SetMotionLimit limit_mps="0.75"/>
      <ReactiveFallback name="StopAction">
        <!-- Perto da bola (< 0,5 m + margem): recua para ponto legal -->
        <ReactiveSequence name="RetreatIfClose">
          <IsBallClose robot_id="{robot_id}" distance_threshold="650.0"/>
          <ComputeLegalSlot slot="retreat" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
          <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}"
                     face_x="{ball_x}" face_y="{ball_y}" tolerance="80.0"/>
        </ReactiveSequence>
        <!-- Caso contrário fica parado (publica goal na pose atual) -->
        <HoldPosition robot_id="{robot_id}"/>
      </ReactiveFallback>
    </ReactiveSequence>
  </BehaviorTree>
</root>
```

## Kick-off, pênalti e free kick

Arquivo `restarts.xml` — referente ao Capítulo 18.

```xml
<?xml version="1.0"?>
<!-- PROPOSTA (não executável): kickoff, pênalti, free kick. Sem coordenadas literais:
     posições vêm de ComputeLegalSlot (independente de lado: own_goal_x/side_sign na blackboard). -->
<root BTCPP_format="4">

  <BehaviorTree ID="PrepareKickoffOurTree">
    <ReactiveFallback name="Roles">
      <ReactiveSequence><HasRole role="goalkeeper"/><SubTree ID="GoalkeeperTree" _autoremap="true"/></ReactiveSequence>
      <ReactiveSequence>
        <HasRole role="kicker"/>
        <ComputeLegalSlot slot="kickoff_kicker" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}" face_x="{ball_x}" face_y="{ball_y}" tolerance="50.0"/>
      </ReactiveSequence>
      <ReactiveSequence>
        <ComputeLegalSlot slot="kickoff_def" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}" face_x="{ball_x}" face_y="{ball_y}" tolerance="50.0"/>
      </ReactiveSequence>
    </ReactiveFallback>
  </BehaviorTree>

  <!-- Também usada como espera durante o KICKOFF adversário -->
  <BehaviorTree ID="PrepareKickoffTheirTree">
    <ReactiveFallback name="Roles">
      <ReactiveSequence><HasRole role="goalkeeper"/><SubTree ID="GoalkeeperTree" _autoremap="true"/></ReactiveSequence>
      <ReactiveSequence>
        <ComputeLegalSlot slot="kickoff_def" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}" face_x="{ball_x}" face_y="{ball_y}" tolerance="50.0"/>
      </ReactiveSequence>
    </ReactiveFallback>
  </BehaviorTree>

  <BehaviorTree ID="KickoffExecuteOurTree">
    <ReactiveFallback name="Roles">
      <ReactiveSequence><HasRole role="goalkeeper"/><SubTree ID="GoalkeeperTree" _autoremap="true"/></ReactiveSequence>
      <ReactiveSequence>
        <HasRole role="kicker"/>
        <SubTree ID="RestartKickerTree" _autoremap="true" target_x="{opp_goal_x}" target_y="{opp_goal_y}"/>
      </ReactiveSequence>
      <HoldPosition robot_id="{robot_id}"/>
    </ReactiveFallback>
  </BehaviorTree>

  <BehaviorTree ID="PreparePenaltyOurTree">
    <ReactiveFallback name="Roles">
      <ReactiveSequence><HasRole role="goalkeeper"/><SubTree ID="GoalkeeperTree" _autoremap="true"/></ReactiveSequence>
      <ReactiveSequence>
        <HasRole role="kicker"/>
        <ComputeLegalSlot slot="penalty_kicker" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}" face_x="{opp_goal_x}" face_y="{opp_goal_y}" tolerance="50.0"/>
      </ReactiveSequence>
      <ReactiveSequence>
        <ComputeLegalSlot slot="penalty_behind" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}" tolerance="50.0"/>
      </ReactiveSequence>
    </ReactiveFallback>
  </BehaviorTree>

  <BehaviorTree ID="PreparePenaltyTheirTree">
    <ReactiveFallback name="Roles">
      <ReactiveSequence><HasRole role="goalkeeper"/><PenaltyKeeperLine side="defend"/></ReactiveSequence>
      <ReactiveSequence>
        <ComputeLegalSlot slot="penalty_behind" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}" tolerance="50.0"/>
      </ReactiveSequence>
    </ReactiveFallback>
  </BehaviorTree>

  <BehaviorTree ID="PenaltyExecuteOurTree">
    <ReactiveFallback name="Roles">
      <ReactiveSequence><HasRole role="goalkeeper"/><SubTree ID="GoalkeeperTree" _autoremap="true"/></ReactiveSequence>
      <ReactiveSequence>
        <HasRole role="kicker"/>
        <SubTree ID="RestartKickerTree" _autoremap="true" target_x="{opp_goal_x}" target_y="{opp_goal_y}"/>
      </ReactiveSequence>
      <HoldPosition robot_id="{robot_id}"/>
    </ReactiveFallback>
  </BehaviorTree>

  <BehaviorTree ID="PenaltyDefendTheirTree">
    <ReactiveFallback name="Roles">
      <ReactiveSequence>
        <HasRole role="goalkeeper"/>
        <!-- Linha de gol até a bola entrar em jogo; depois volta ao goleiro normal -->
        <ReactiveFallback>
          <ReactiveSequence><Inverter><WaitBallInPlay moved_mm="50.0" timeout_s="10.0"/></Inverter><PenaltyKeeperLine side="defend"/></ReactiveSequence>
          <SubTree ID="GoalkeeperTree" _autoremap="true"/>
        </ReactiveFallback>
      </ReactiveSequence>
      <HoldPosition robot_id="{robot_id}"/>
    </ReactiveFallback>
  </BehaviorTree>

  <!-- Funde free_kick/corner_kick/throw_in/kick_in. designated_x/y vem do GameState. -->
  <BehaviorTree ID="FreeKickOurTree">
    <ReactiveFallback name="Roles">
      <ReactiveSequence><HasRole role="goalkeeper"/><SubTree ID="GoalkeeperTree" _autoremap="true"/></ReactiveSequence>
      <ReactiveSequence>
        <HasRole role="kicker"/>
        <SubTree ID="RestartKickerTree" _autoremap="true" target_x="{opp_goal_x}" target_y="{opp_goal_y}"/>
      </ReactiveSequence>
      <ReactiveSequence>
        <ComputeLegalSlot slot="freekick_support" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}" face_x="{ball_x}" face_y="{ball_y}" tolerance="80.0"/>
      </ReactiveSequence>
    </ReactiveFallback>
  </BehaviorTree>

  <BehaviorTree ID="FreeKickTheirTree">
    <ReactiveFallback name="Roles">
      <ReactiveSequence><HasRole role="goalkeeper"/><SubTree ID="GoalkeeperTree" _autoremap="true"/></ReactiveSequence>
      <ReactiveSequence>
        <ComputeLegalSlot slot="wall" index="0" slot_x="{slot_x}" slot_y="{slot_y}" slot_w="{slot_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{slot_x}" y="{slot_y}" face_x="{ball_x}" face_y="{ball_y}" tolerance="80.0"/>
      </ReactiveSequence>
    </ReactiveFallback>
  </BehaviorTree>

</root>
```

## Ball placement do adversário

Arquivo `ball_placement_their.xml` — referente ao Capítulo 18.

```xml
<?xml version="1.0"?>
<!-- PROPOSTA. S06. Regra §8.3.3 p.26: >= 0,5 m da linha bola->alvo. -->
<root BTCPP_format="4">
  <BehaviorTree ID="BallPlacementTheirTree">
    <ReactiveSequence name="AvoidCorridor">
      <SetMotionLimit limit_mps="0.75"/>
      <ReactiveFallback>
        <!-- Sai do corredor (estádio) quando necessário -->
        <AvoidPlacementCorridor margin_mm="550.0"/>
        <HoldPosition robot_id="{robot_id}"/>
      </ReactiveFallback>
    </ReactiveSequence>
  </BehaviorTree>
</root>
```

## Ball placement nosso

Arquivo `ball_placement_our.xml` — referente ao Capítulo 18.

```xml
<?xml version="1.0"?>
<!-- PROPOSTA. S05 (pós-MVP / opcional: EL pode desabilitar o ball placement, p.16). -->
<root BTCPP_format="4">
  <BehaviorTree ID="BallPlacementOurTree">
    <ReactiveFallback name="PlacementRoles">
      <ReactiveSequence name="PlacerRole">
        <HasRole role="kicker"/>
        <ComputePlacementApproach designated_x="{designated_x}" designated_y="{designated_y}"
                                  pickup_x="{pickup_x}" pickup_y="{pickup_y}"
                                  drop_x="{drop_x}" drop_y="{drop_y}" approach_w="{approach_w}"/>
        <GoToPoint robot_id="{robot_id}" x="{pickup_x}" y="{pickup_y}"
                   face_x="{drop_x}" face_y="{drop_y}" tolerance="50.0"/>
        <PlaceBall drop_x="{drop_x}" drop_y="{drop_y}" timeout_s="30.0" tolerance_mm="150.0"/>
      </ReactiveSequence>
      <!-- Demais robôs: respeitam STOP -->
      <SubTree ID="StopSubTree" _autoremap="true"/>
    </ReactiveFallback>
  </BehaviorTree>
</root>
```

## Jogo corrido

Arquivo `normal_play.xml` — referente ao Capítulo 19.

```xml
<?xml version="1.0"?>
<!-- PROPOSTA. S16 NormalPlayTree. AttackerTree = extração de master_strategy_carry.xml linhas 76-135
     (sem PrecisionKick; KickBall com kick_speed <= 3.0). GoalkeeperTree/DefenderTree existentes
     (com AD de 08). Substitui IsMyRole/IsRobotId por HasRole. -->
<root BTCPP_format="4">
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
  <!-- TODO: BehaviorTree ID="AttackerTree" = corpo de AttackerRole do carry (RetryUntilSuccessful(-1) +
       ReactiveSequence: UpdateBallPosition, CalculateInterception, ReactiveFallback ChaseAndKick) -->
</root>
```
