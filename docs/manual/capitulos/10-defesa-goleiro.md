# O defensor e o goleiro

Enquanto o atacante ataca a bola, os outros robôs protegem o gol. Este capítulo descreve os dois comportamentos defensivos do sistema atual: o **defensor** (um robô de linha) e o **goleiro**.

## O defensor

A árvore do defensor, `defender_tree.xml`, é pequena e declarativa ({{fig:arvore_defensor_atual}}). Ela só é executada pelo robô que o atribuidor de papéis nomeou defensor (`IsMyRole = defender`) e decide, por prioridade, entre dois cenários:

![A árvore do defensor](figuras/arvore_defensor_atual.png)

1. **Bola no campo adversário** (`IsBallInOpponentField`): o defensor faz `ShadowBall` — acompanha a bola prevista a uma distância fixa, **atrás** dela, no rumo do próprio gol, sem nunca cruzar o meio-campo (distância padrão de 1200 mm).
2. **Bola no nosso campo**: subdivide-se em
   - **o adversário tem a posse** (`IsOpponentControllingBall`): `MarkOpponent` — posiciona-se na linha entre a bola e o gol, a 400 mm da bola, bloqueando o chute;
   - **caso contrário**: volta a fazer `ShadowBall`, agora com distância de 1000 mm, para cobrir o goleiro em vez de brigar pela bola.

Note a escolha de projeto: o defensor **não disputa a bola**. Quem faz isso é o atacante. O defensor é uma "sombra" que ocupa a posição defensiva correta.

### ShadowBall

`ShadowBall` é uma ação síncrona que, a cada tick, calcula um alvo e o publica como `RobotGoal`. O cálculo ({{fig:defensor_shadow_mark}}, painel a):

1. **Bola prevista**: posição atual somada à velocidade × `predict_time` (0,3 s).
2. **Alvo em x**: a posição prevista deslocada de `follow_distance` **na direção do próprio gol**. Esse valor é então limitado entre a linha do meio-campo (−180 mm, do nosso lado) e a **borda da área de defesa mais 200 mm**, de modo que o defensor nunca entre na área.
3. **Alvo em y**: o y previsto da bola, limitado a ±`y_limit` (900 mm).
4. **Orientação**: o robô olha para a bola.

### MarkOpponent

`MarkOpponent` ({{fig:defensor_shadow_mark}}, painel b) traça a linha da bola ao centro do próprio gol e coloca o alvo sobre ela, a `block_distance` (400 mm) da bola, com o mesmo limite de área e |y| ≤ 1200 mm. O defensor fica entre o chutador e o gol.

![ShadowBall (a) e MarkOpponent (b)](figuras/defensor_shadow_mark.png)

### Limitações de projeto

- As duas ações são **síncronas**: devolvem SUCCESS no mesmo tick em que publicam o alvo. Isso as torna baratas, mas significa que **não têm `onHalted`**: ao serem interrompidas por um ramo de maior prioridade, o último alvo continua valendo no controlador.
- A velocidade da bola vem da **diferença finita** do `strategy_node`, mais ruidosa que a predição do Kalman.
- Há um terceiro nó defensivo, `GoToClamped`, que vai a um ponto limitado fora da área, registrado mas ainda não usado em nenhum XML.

## O goleiro

O goleiro é o único robô que pode (e deve) entrar na própria área, e o único que, por regra, pode reter a bola ali — por até 10 segundos. A árvore `goalkeeper_tree.xml` é mínima ({{fig:arvore_goleiro_atual}}): se `robot_id == 0`, executa a folha `Goalkeeper`; caso contrário, o robô fica parado.

![A árvore do goleiro](figuras/arvore_goleiro_atual.png)

Toda a lógica está na folha `Goalkeeper` (`goalkeeper_node.cpp`), uma ação assíncrona que **nunca termina** (devolve sempre RUNNING) e a cada tick escolhe entre dois estados ({{fig:goleiro_estados}}):

![Os dois estados do goleiro](figuras/goleiro_estados.png)

### Estado 2 — bola fora da área: defender na linha

Enquanto a bola está fora da área de defesa, o goleiro fica **na linha do gol, 120 mm à frente da linha de fundo**, e acompanha o `y` da bola, limitado a `±(largura do gol/2 − 50 mm)`. O robô olha para a bola. Usa o planejador de linha reta, sem desvio de obstáculos.

### Estado 1 — bola na área: sair e afastar

Quando a bola entra na área (com margem zero), o goleiro vai buscá-la e a **afasta para a lateral**:

1. Escolhe o lado do afastamento pelo sinal do `y` da bola e calcula a direção do chute: da bola até o ponto `(0, ±(largura/2 + 500 mm))`.
2. Se ainda não está **atrás da bola** em relação a essa direção (ou está a mais de 250 mm dela), navega, com o D\*, até um **ponto de pré-chute 200 mm atrás da bola**, dentro da área.
3. Quando já está atrás e a menos de 250 mm, avança em linha reta até **60 mm além da bola** e, se estiver a menos de 180 mm e alinhado (erro de ângulo < 0,45 rad), pede o **chute** por `MODE_KICK` (no máximo 3 m/s).

Em todos os casos, o alvo é limitado a ficar **dentro da área de defesa**.

!!! warning "O que o goleiro atual ainda não faz"
    A folha não conhece o estado de jogo: ela se comporta do mesmo jeito em qualquer fase. Em particular, **não há tratamento do pênalti** (o goleiro defensor precisa tocar a linha de gol até a bola entrar em jogo) nem **limite de 10 segundos** para a bola retida na área. Além disso, a identidade do goleiro é fixa (`robot_id == 0`) e a folha devolve RUNNING mesmo sem dados, em vez de falhar. O Capítulo 19 propõe essas correções.

## Blocos defensivos disponíveis, mas não usados

O repositório traz outras folhas defensivas já implementadas e registradas, mas ainda sem uso em nenhuma árvore: `GoalLineDefend` (acompanha o y da bola na linha de gol), `PositionBisector` (posiciona-se na bissetriz entre a bola e as traves, ponderando 80% bissetriz e 20% bola), `SmotherSave` (vai direto à bola para "abafar") e `LateralClear` (afasta a bola para a lateral). São bons pontos de partida para um goleiro mais elaborado.
