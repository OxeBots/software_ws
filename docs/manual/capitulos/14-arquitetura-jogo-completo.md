<!-- parte: Parte IV — A Master Tree de jogo completo | A arquitetura proposta para que o time jogue uma partida inteira: um estado de jogo único e confiável, uma árvore mestre com prioridades claras, uma subárvore para cada situação regulamentar e papéis dinâmicos. -->
# A arquitetura de jogo completo

A Parte III descreveu o que existe. A Parte IV descreve o que construir para que o time jogue uma **partida inteira**, do primeiro apito ao último. Este capítulo apresenta a visão geral e as decisões arquiteturais; os capítulos seguintes detalham cada peça. Tudo o que aparece a partir daqui é **proposta de projeto**: os nós e componentes novos ainda precisam ser implementados, e as figuras os marcam com **✦**.

## O que uma partida inteira exige

Do Capítulo 2 e dos pontos de atenção do Capítulo 13, saem cinco propriedades que a arquitetura precisa garantir:

1. **Cobertura completa dos comandos.** Cada comando do árbitro, em cada estágio, tem um comportamento definido. Nenhum cai em um "default" por acaso.
2. **Segurança acima de tudo.** HALT para os robôs, sempre; dados ausentes ou velhos levam a um estado seguro; limites de velocidade e de chute valem independentemente de qualquer árvore.
3. **Independência de lado e de cor.** O mesmo código e as mesmas árvores servem ao time amarelo e ao azul, e continuam corretos quando os times trocam de lado.
4. **Coordenação entre os robôs.** Papéis exclusivos, trocas estáveis, degradação graciosa quando o número de robôs muda.
5. **Testabilidade.** Cada ramo e cada transição pode ser verificado automaticamente, sem robôs.

## Uma árvore para o time, uma por robô, ou ambas?

A primeira decisão é de **onde** mora a inteligência. Há três modelos possíveis.

**Centralizado.** Uma única Behavior Tree comanda os três robôs, como se fosse um técnico. Tem a vantagem de a coordenação ser natural (uma árvore sabe o que todos fazem). Mas exige reescrever as folhas, que hoje assumem "o meu robô"; um tick lento atrasa todos os robôs ao mesmo tempo; e a falha de um processo derruba o time inteiro.

**Distribuído por robô** (o modelo atual). Cada robô tem a sua árvore. É simples, rápido, e a falha de um processo afeta um robô só. Em compensação, a coordenação depende de mensagens externas (como o atribuidor de papéis) e cada árvore precisa reconstruir sozinha o estado do jogo.

**Híbrido** (a proposta). Mantém **uma árvore por robô**, para aproveitar o que existe, mas move para **serviços de equipe**, fora da árvore, tudo o que é *coletivo* ou *crítico*: o estado legal do jogo (`referee_state_node`) e a atribuição de papéis (`role_assigner_node`). A execução continua distribuída; a decisão sobre "o que está acontecendo" e "quem faz o quê" é única.

![A arquitetura híbrida: serviços de equipe alimentam a árvore de cada robô; o controlador ganha um SafetyGate](figuras/arquitetura_hibrida.png)

A {{fig:arquitetura_hibrida}} mostra a arquitetura. Os componentes marcados com ✦ são os novos ou ampliados:

- **`referee_state_node`**: converte o comando bruto do árbitro em um `GameState` tipado, com a fase de jogo, o favorecido, o limite de velocidade e a idade do dado.
- **`role_assigner_node`** ampliado: além de atacante e defensor, publica goleiro, cobrador de reinício e a lista de robôs ativos.
- **Observer com carimbo de tempo**: `GameData` passa a carregar o instante da leitura.
- **Master Tree v2**: a árvore mestre reescrita, com um ramo por fase.
- **SafetyGate**: um filtro de segurança dentro do controlador de movimento.

## As camadas de decisão

Dentro do modelo híbrido, as decisões se organizam em camadas de **prioridade decrescente** ({{fig:camadas_decisao}}):

![As cinco camadas de decisão, da mais prioritária à mais concreta](figuras/camadas_decisao.png)

| Camada | Pergunta | Onde vive |
|---|---|---|
| **0 — Segurança** | Posso confiar nos dados? O árbitro mandou parar? | BT (`SafetyGuard`) **e** SafetyGate no controlador |
| **1 — Fase do jogo** | O que está acontecendo: STOP, kick-off, pênalti, jogo corrido…? | BT (ramos do mestre), alimentada pelo `GameState` |
| **2 — Papéis** | Qual é a minha função agora? | `role_assigner` (ROS) + `HasRole` (BT) |
| **3 — Comportamentos** | Como cumpro essa função nesta fase? | Subárvores (atacar, defender, cobrar…) |
| **4 — Habilidades** | Como me movo e chuto? | Folhas C++, D\*, controlador |

Um critério ajuda a decidir **o que é BT e o que não é**: Behavior Trees são excelentes para **escolher entre comportamentos por prioridade e reagir a mudanças**, mas ruins para **manter estado entre ticks** (memória de contexto, histerese temporal) e para **cálculos coletivos**. Por isso a interpretação do árbitro (que precisa lembrar o contexto do reinício), a atribuição de papéis (com histerese) e a vigilância de dados (que precisa de um relógio) ficam fora da árvore, em componentes ROS 2, e a árvore apenas **consulta** o resultado.

## Quem tem a palavra final

Para evitar conflitos, cada tipo de decisão tem **um único dono**:

| Decisão | Dono | Os outros... |
|---|---|---|
| Em que fase do jogo estamos | `referee_state_node` | só lêem `/game_state` |
| Quem é goleiro, atacante, defensor, cobrador | `role_assigner_node` | só lêem `/role_assignment` |
| Qual ação este robô executa | a BT do robô | — |
| O que vai para o robô (velocidade, chute) | o controlador (com SafetyGate) | folhas pedem; não escrevem |
| Se um dado ainda é confiável | a condição `IsDataFresh` e o SafetyGate | — |

Duas consequências diretas: o `strategy_node` **deixa de interpretar** o `Referee` (a `gc_callback` atual é removida) e **nenhuma folha escreve** em `/robot_commands`.

## Princípios de projeto

Algumas regras orientam todos os capítulos seguintes:

!!! tip "Princípios"
    1. **Toda guarda de ramo é uma `ReactiveSequence`.** Uma condição precisa ser reavaliada a cada tick; um `Sequence` comum não a reavalia enquanto um filho está em andamento.
    2. **Nenhuma coordenada literal que dependa de lado** nos XML. Posições são calculadas (`ComputeLegalSlot`) a partir da geometria e do lado.
    3. **Toda ação assíncrona tem `onHalted` idempotente** e rápido, e deixa o robô em estado seguro.
    4. **Nunca bloquear dentro de um tick.**
    5. **Falhar alto, não em silêncio:** sem dado, a folha devolve FAILURE com log, não RUNNING mudo.
    6. **A segurança é redundante:** vale na árvore *e* no controlador.
    7. **Seguro por padrão:** se nenhum ramo casa, o robô pára (não joga).

## Reaproveitamento

Uma preocupação legítima é quanto do que existe será jogado fora. A resposta: **muito pouco**. As folhas de movimento (`GoToPoint`, `KickBall`, `IsBallClose`, `CalculateInterception`), o D\*, o controlador, o Kalman, o atribuidor de papéis, a árvore do defensor e a lógica do atacante são reaproveitados — com ajustes pontuais (Capítulo 21). O que muda é a **estrutura em torno deles**: o mestre, o estado de jogo, o tratamento de lado e a segurança. A tabela do Apêndice C mostra, para cada regra do regulamento, que componente a trata.
