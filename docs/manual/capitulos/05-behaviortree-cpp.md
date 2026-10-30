# BehaviorTree.CPP na prática

O projeto usa a biblioteca **BehaviorTree.CPP** (versão 4.x, mantida por Davide Faconti) para executar as árvores. Este capítulo mostra como os conceitos do capítulo anterior aparecem em código: o formato XML das árvores, os tipos de nós em C++, as portas e a blackboard, as subárvores e as ferramentas de depuração. Documentação oficial: <https://www.behaviortree.dev>.

## Duas camadas: XML e C++

Na BehaviorTree.CPP, uma árvore tem duas partes bem separadas:

1. A **estrutura** da árvore, escrita em **XML**: quais nós existem, em que ordem e com que parâmetros.
2. A **implementação** de cada nó folha, escrita em **C++**: o que "ir até um ponto" ou "a bola está perto?" realmente faz.

A ligação entre as duas é a **fábrica** (`BT::BehaviorTreeFactory`): em C++, cada classe de nó é *registrada* na fábrica com um nome (`"GoToPoint"`); no XML, esse nome é usado como se fosse uma tag. Ao carregar o XML, a fábrica instancia a classe correspondente a cada tag.

Um arquivo XML mínimo do projeto tem esta forma:

```xml
<root BTCPP_format="4" main_tree_to_execute="MainTreeCarry">
  <BehaviorTree ID="MainTreeCarry">
    <ReactiveFallback name="MasterStrategy">
      <Sequence name="HaltBranch">
        <CheckGCCommand expected="0"/>
        <SubTree ID="HaltSubTree" _autoremap="true"/>
      </Sequence>
      <!-- ... demais ramos ... -->
      <Halt reason="idle"/>
    </ReactiveFallback>
  </BehaviorTree>
</root>
```

Cada `<BehaviorTree ID="...">` define uma árvore com um nome. O atributo `main_tree_to_execute` indica qual delas é a raiz da execução. Os elementos internos são os nós: `ReactiveFallback`, `Sequence`, `SubTree` e `Halt` aparecem aqui; os dois últimos mais `CheckGCCommand` são folhas ou referências cujos nomes foram registrados em C++.

## Os tipos de nó em C++

Para criar uma nova folha, herda-se de uma de três classes da biblioteca, conforme a natureza do nó:

- **`BT::ConditionNode`**: condição síncrona. Implementa `tick()`, que devolve SUCCESS ou FAILURE (nunca RUNNING). Exemplo no projeto: `IsBallCloseCondition`.
- **`BT::SyncActionNode`**: ação síncrona. Também implementa `tick()` e termina no mesmo tick. Exemplos: `KeepDistance`, `AimAt`, `ShadowBall`.
- **`BT::StatefulActionNode`**: ação assíncrona. Implementa três métodos — `onStart()`, `onRunning()` e `onHalted()` — e pode devolver RUNNING. É o tipo mais usado para movimento e chute: `GoToPointNode`, `KickBallNode`, `GoalkeeperNode`.

O ciclo de vida de uma `StatefulActionNode` está na {{fig:ciclo_stateful_action}}:

![O ciclo de vida de uma ação assíncrona (StatefulActionNode)](figuras/ciclo_stateful_action.png)

- No **primeiro tick** depois de ficar inativa, a biblioteca chama `onStart()`. Ali a folha lê suas portas, prepara o estado e começa a tarefa. Se já puder concluir, devolve SUCCESS/FAILURE; caso contrário, RUNNING.
- Nos **ticks seguintes**, enquanto estiver em RUNNING, chama `onRunning()`.
- Se o **pai interrompe** a folha (por exemplo, porque um ramo de maior prioridade assumiu), a biblioteca chama `onHalted()`. É a oportunidade de **limpar**: liberar um override, parar de publicar, zerar um temporizador.
- Quando termina (SUCCESS ou FAILURE), a folha volta a IDLE e o ciclo recomeça no próximo `onStart()`.

!!! warning "onHalted() precisa ser rápido e idempotente"
    `onHalted()` pode ser chamado várias vezes e a qualquer momento. Ele não deve bloquear nem depender de que a tarefa tenha de fato começado. Várias folhas do projeto o usam para devolver o controle ao controlador de movimento (`KickBallNode::onHalted` libera o override de chute).

## Portas: a interface de cada nó

Cada folha declara suas **portas**, que são os parâmetros que o XML pode passar e as saídas que ela pode produzir. A declaração é feita em um método estático `providedPorts()`:

```cpp
BT::PortsList GoToPointNode::providedPorts() {
  return { BT::InputPort<unsigned int>("robot_id"),
           BT::InputPort<double>("x"),
           BT::InputPort<double>("y"),
           BT::InputPort<double>("tolerance", -1.0, "Tolerância para sucesso"),
           BT::InputPort<std::string>("planner", "dstar", "dstar | straight_line") };
}
```

Há portas de **entrada** (`InputPort`), de **saída** (`OutputPort`) e de entrada-e-saída. Uma entrada pode ter **valor padrão** (o segundo argumento acima). No XML, os valores são passados como atributos:

```xml
<GoToPoint robot_id="{robot_id}" x="1000" y="0" tolerance="80" planner="straight_line"/>
```

Um valor pode ser um **literal** (`x="1000"`) ou uma **referência à blackboard** entre chaves (`robot_id="{robot_id}"`). No segundo caso, o valor é lido da blackboard no momento em que a folha o pede com `getInput`. As portas de saída funcionam ao contrário: `ball_x="{ball_x}"` em uma saída significa "escreva o valor na chave `ball_x`".

!!! warning "Porta sem atributo e sem padrão = erro"
    Se uma porta de entrada não tem valor padrão e o XML **não** a menciona, `getInput` **falha**. A biblioteca *não* tenta ler, por conta própria, uma chave da blackboard com o mesmo nome da porta. Esse é um erro fácil de cometer e silencioso: a folha costuma devolver FAILURE e o ramo inteiro falha. Duas folhas do projeto (`KeepDistance`, `AimAt`) exigem as portas `robot_x`/`robot_y` e, em vários XML, elas não são passadas — voltaremos a isso no Capítulo 13. Quando faz sentido, declare o padrão como uma referência: `InputPort<double>("robot_x", "{robot_x}", ...)`.

## A blackboard

A **blackboard** é um dicionário compartilhado entre os nós de uma árvore: chaves de texto associadas a valores de qualquer tipo. É a memória da árvore. Ela serve para passar informação entre nós (um nó escreve `pkx`, outro lê) e para injetar dados do mundo (o `strategy_node` escreve `ball_x`, `gc_command` etc. a partir das mensagens ROS 2).

Duas propriedades merecem atenção:

- **Escopo de subárvores.** Cada `SubTree` tem a sua **própria blackboard**, separada da do pai. Para compartilhar valores, as chaves precisam ser *remapeadas*. Há duas formas: explícita (`<SubTree ID="X" bola_x="{ball_x}"/>`) ou automática (`_autoremap="true"`), que copia, com o mesmo nome, as chaves que **já existem** na blackboard do pai. Chaves novas criadas dentro da subárvore ficam só nela.
- **Raiz.** As folhas podem acessar a blackboard **raiz** com `config().blackboard->rootBlackboard()`, atravessando todas as subárvores. É o que o projeto faz para ler `my_goal_x`, `robot_id` e a geometria do campo de dentro de qualquer subárvore.

![A blackboard da árvore principal e a da subárvore, ligadas por remapeamento](figuras/fluxo_blackboard_subtree.png)

!!! note "Quem escreve na blackboard?"
    No projeto, a blackboard é escrita por duas fontes: (1) as **callbacks ROS 2** do `strategy_node` (dados do jogo, árbitro, geometria, papéis), que rodam em outra *thread*; e (2) as **folhas** (por exemplo, `UpdateBallPosition` escreve `pkx`, `pky`). Como leitura e escrita acontecem em *threads* diferentes, valores relacionados (`ball_x` e `ball_y`) podem ser lidos em instantes diferentes. O Capítulo 20 propõe uma forma de evitar isso.

## Subárvores e reuso

Uma subárvore é uma `<BehaviorTree>` com outro `ID`, referenciada por `<SubTree ID="...">`. Para que uma subárvore de **outro arquivo** seja encontrada, ela precisa estar registrada na fábrica. O `strategy_node` faz isso de forma abrangente: antes de criar a árvore principal, ele registra **todos os arquivos `.xml`** do diretório `behavior_trees/` (exceto o da árvore principal). Isso é prático, mas implica que os `ID` precisam ser **únicos entre todos os arquivos** — algo que hoje não é verdade para alguns legados (Capítulo 13).

## Nós de controle e decoradores nativos

A biblioteca já traz os nós vistos no Capítulo 4: `Sequence`, `ReactiveSequence`, `Fallback`, `ReactiveFallback`, `Parallel`, `Inverter`, `RetryUntilSuccessful`, `Repeat`, `Timeout`, `Delay`, `ForceSuccess`, `ForceFailure`, `AlwaysSuccess`, `AlwaysFailure`, `Sleep`. Existem ainda variantes (`SequenceWithMemory`, `IfThenElse`, `WhileDoElse`, `Switch`, `TryCatch`, `ParallelAll`) e scripts embutidos (`Script`, pré-condições), pouco usados aqui.

Uma observação sobre `RetryUntilSuccessful` com `num_attempts="-1"` — um padrão muito usado no projeto para "espere até a bola estar perto". Na implementação da série 4.x, quando o filho falha e a árvore foi configurada com o mecanismo de *wake-up*, o decorador devolve RUNNING depois de **uma** tentativa por tick (em vez de repetir o filho em laço apertado no mesmo tick). O efeito é um *polling* de uma tentativa por tick, o que é exatamente o desejado. O plano de testes (Capítulo 23) inclui um teste que confirma esse comportamento na versão instalada.

## Registrando folhas na fábrica

No `strategy_node`, o registro é feito em `init()`. Folhas que precisam falar com o ROS 2 recebem o nó ROS do processo como argumento extra:

```cpp
factory_.registerNodeType<oxebots_strategy::GoToPointNode>("GoToPoint", shared_from_this());
factory_.registerNodeType<oxebots_strategy::KeepDistance>("KeepDistance");
```

Para condições e ações triviais, a biblioteca aceita *lambdas*:

```cpp
factory_.registerSimpleCondition("CheckGCCommand", [&](BT::TreeNode& node) {
    int expected, current;
    if (!node.getInput("expected", expected)) return BT::NodeStatus::FAILURE;
    if (!blackboard_->get("gc_command", current)) return BT::NodeStatus::FAILURE;
    return (current == expected) ? BT::NodeStatus::SUCCESS : BT::NodeStatus::FAILURE;
}, { BT::InputPort<int>("expected") });
```

!!! note "Não existe plugin"
    As folhas são compiladas **dentro** do executável `strategy_node`; não há carregamento dinâmico de plugins. Ao criar uma folha nova, o arquivo `.cpp` precisa ser incluído na lista de fontes do `add_executable(strategy_node ...)` do `CMakeLists.txt`.

## Observando e depurando

Duas ferramentas ajudam a entender o que a árvore está fazendo:

- **Groot2**: o `strategy_node` inicia um `Groot2Publisher` em uma porta por robô (1667 + id para o time azul, 1677 + id para o amarelo). O Groot2 se conecta a essa porta e mostra a árvore ao vivo, com o ramo ativo destacado.
- **Logs**: as folhas usam `RCLCPP_*` (e o `Halt` registra, a cada 2 s, por que o robô está parado). A BehaviorTree.CPP também oferece *loggers* (`StdCoutLogger`, `FileLogger`) que podem ser ligados para registrar cada transição de estado de cada nó.

Para depurar um erro de criação de árvore, as mensagens costumam ser autoexplicativas: *"Node not registered"* indica que a tag do XML não tem um `registerNodeType`; *"getInput() failed ... does not contain the key"* indica uma porta de entrada sem atributo e sem padrão.
