<!-- parte: Parte V — Implementação | Como criar uma nova folha, como validar o comportamento do time sem robôs e como dividir o trabalho nas quatro semanas até uma versão jogável. -->
# Tutorial: criando uma folha de árvore

Este capítulo guia a criação de uma folha completa, do zero ao XML e ao teste, usando como exemplo a ação **`HoldPosition`** do Capítulo 17 — simples, mas representativa: lê dados do mundo, publica um objetivo e precisa de um `onHalted` correto. O padrão segue o das folhas existentes, como `GoalLineDefendNode`.

!!! tip "Antes de começar"
    Compilar é com você: `./build.sh` no devcontainer. Os trechos abaixo são **exemplos esquemáticos** escritos com a API real da BehaviorTree.CPP 4.x e o padrão do projeto, mas ainda não estão no repositório.

## Nó ROS 2 ou nó de árvore?

A confusão mais comum de quem chega é entre dois conceitos que têm "nó" no nome:

- **Nó ROS 2** (`rclcpp::Node`): um **processo** que publica e assina tópicos — `strategy_node`, `role_assigner_node`…
- **Nó de BT** (`BT::TreeNode`): um **objeto C++** dentro da árvore — `GoToPoint`, `Sequence`…

Um nó de BT *não* é um processo. No projeto, as folhas que precisam falar com o ROS 2 **recebem o `rclcpp::Node` do `strategy_node`** e criam seus publicadores e assinantes nele ({{fig:no_ros_vs_no_bt}}).

![Nós de BT vivem dentro de um processo ROS 2 e usam o nó ROS dele](figuras/no_ros_vs_no_bt.png)

## Passo 1 — Definir o que a folha faz

Para `HoldPosition`: *"Ler a pose atual do robô em `/game_data`, publicar um `RobotGoal` nessa pose e ficar em RUNNING; ao ser interrompida, não fazer nada."*

Perguntas a responder antes de escrever código:

| Pergunta | Resposta para `HoldPosition` |
|---|---|
| Que dado preciso? | a pose do meu robô (`/game_data`) |
| Que comando produzo? | um `RobotGoal` (`/robot_goal`) |
| É síncrona ou assíncrona? | assíncrona (fica em RUNNING) |
| O que faço se faltarem dados? | FAILURE, com log |
| O que faço ao ser interrompida? | nada (idempotente) |

## Passo 2 — O cabeçalho

`include/oxebots_strategy/hold_position_node.hpp`:

```cpp
#pragma once

#include <mutex>
#include "behaviortree_cpp/action_node.h"
#include "rclcpp/rclcpp.hpp"
#include "oxebots_interfaces/msg/game_data.hpp"
#include "oxebots_interfaces/msg/robot_goal.hpp"

namespace oxebots_strategy
{

class HoldPositionNode : public BT::StatefulActionNode
{
public:
  HoldPositionNode(const std::string& name, const BT::NodeConfig& config,
                   rclcpp::Node::SharedPtr node);

  static BT::PortsList providedPorts();

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  void gameDataCallback(const oxebots_interfaces::msg::GameData::SharedPtr msg);
  bool publishHere();

  rclcpp::Node::SharedPtr node_;
  rclcpp::Publisher<oxebots_interfaces::msg::RobotGoal>::SharedPtr goal_pub_;
  rclcpp::Subscription<oxebots_interfaces::msg::GameData>::SharedPtr game_data_sub_;

  std::mutex mutex_;                                  // callback e tick rodam em threads diferentes
  oxebots_interfaces::msg::GameData::SharedPtr last_data_;
  unsigned int robot_id_{0};
};

}  // namespace oxebots_strategy
```

## Passo 3 — A implementação

`src/hold_position_node.cpp`:

```cpp
#include "oxebots_strategy/hold_position_node.hpp"
#include <cmath>

namespace oxebots_strategy
{

HoldPositionNode::HoldPositionNode(const std::string& name, const BT::NodeConfig& config,
                                   rclcpp::Node::SharedPtr node)
  : BT::StatefulActionNode(name, config), node_(node)
{
  // Mesmo QoS das demais folhas de movimento: guarda o último objetivo.
  auto goal_qos = rclcpp::QoS(rclcpp::KeepLast(1)).transient_local().reliable();
  goal_pub_ = node_->create_publisher<oxebots_interfaces::msg::RobotGoal>("/robot_goal", goal_qos);
  game_data_sub_ = node_->create_subscription<oxebots_interfaces::msg::GameData>(
      "/game_data", 10,
      std::bind(&HoldPositionNode::gameDataCallback, this, std::placeholders::_1));
}

BT::PortsList HoldPositionNode::providedPorts()
{
  // O padrão "{robot_id}" lê a chave da blackboard quando o XML não passa a porta.
  return { BT::InputPort<unsigned int>("robot_id", "{robot_id}", "Id do robô") };
}

void HoldPositionNode::gameDataCallback(const oxebots_interfaces::msg::GameData::SharedPtr msg)
{
  std::lock_guard<std::mutex> lock(mutex_);
  last_data_ = msg;
}

bool HoldPositionNode::publishHere()
{
  oxebots_interfaces::msg::GameData::SharedPtr data;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    data = last_data_;
  }
  if (!data) return false;

  for (const auto& ally : data->robots.allies) {
    if (ally.id != robot_id_) continue;

    auto goal = std::make_unique<oxebots_interfaces::msg::RobotGoal>();
    goal->robot_id = robot_id_;
    goal->pose.header.stamp = node_->now();
    goal->pose.header.frame_id = "map";
    goal->planner_type = oxebots_interfaces::msg::RobotGoal::PLANNER_STRAIGHT_LINE;
    goal->disable_arrival_latch = true;                       // nunca "trava" por chegada
    goal->pose.pose.position.x = ally.x / 1000.0;             // mm -> m
    goal->pose.pose.position.y = ally.y / 1000.0;
    goal->pose.pose.orientation.z = std::sin(ally.orientation * 0.5);
    goal->pose.pose.orientation.w = std::cos(ally.orientation * 0.5);
    goal_pub_->publish(std::move(goal));
    return true;
  }
  return false;
}

BT::NodeStatus HoldPositionNode::onStart()
{
  if (!getInput<unsigned int>("robot_id", robot_id_)) {
    RCLCPP_ERROR(node_->get_logger(), "HoldPosition: porta robot_id ausente");
    return BT::NodeStatus::FAILURE;                           // falhar alto, nunca em silêncio
  }
  if (!publishHere()) {
    RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 2000,
                         "HoldPosition: sem pose do robô %u", robot_id_);
    return BT::NodeStatus::FAILURE;
  }
  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus HoldPositionNode::onRunning()
{
  return BT::NodeStatus::RUNNING;   // o objetivo publicado continua valendo
}

void HoldPositionNode::onHalted()
{
  // Nada a limpar: não publicamos nenhum override. Idempotente por construção.
}

}  // namespace oxebots_strategy
```

Três decisões de projeto que valem comentário:

- **Falhar alto.** Sem `robot_id` ou sem pose, a folha devolve FAILURE com log; não fica em RUNNING "esperando".
- **Mutex.** A callback roda na *thread* do executor e `onStart` na do tick; o *mutex* evita corrida na troca do ponteiro.
- **`onHalted` vazio e seguro.** Como não há override a soltar, interromper é seguro. Se a folha pedisse um override (como `KickOnce`), o `onHalted` precisaria liberá-lo.

## Passo 4 — Registrar na fábrica

Em `strategy_node.cpp`, junto aos demais registros:

```cpp
#include "oxebots_strategy/hold_position_node.hpp"
// ...
factory_.registerNodeType<oxebots_strategy::HoldPositionNode>("HoldPosition", shared_from_this());
```

O nome entre aspas (`"HoldPosition"`) é a **tag** que o XML usará.

## Passo 5 — Incluir no build

No `CMakeLists.txt` de `oxebots_strategy`, acrescentar o `.cpp` à lista do executável (a lista começa na linha `add_executable(strategy_node ...)`):

```cmake
add_executable(
  strategy_node
  src/strategy_node.cpp
  ...
  src/hold_position_node.cpp        # <- novo
)
```

As dependências (`behaviortree_cpp`, `oxebots_interfaces`, `rclcpp`) já estão presentes. Como as folhas são compiladas dentro do executável, um `.cpp` esquecido nessa lista só aparece como erro de *link* na compilação.

## Passo 6 — Usar no XML

```xml
<ReactiveFallback name="StopAction">
  <!-- ... recuar se estiver perto da bola ... -->
  <HoldPosition robot_id="{robot_id}"/>
</ReactiveFallback>
```

Como a porta tem padrão `{robot_id}`, o atributo poderia ser omitido: `<HoldPosition/>`.

## Passo 7 — Testar

Um teste unitário não precisa de robôs: basta uma fábrica e uma mensagem simulada.

```cpp
TEST(HoldPosition, PublishesCurrentPoseAndStaysRunning) {
  rclcpp::init(0, nullptr);
  auto ros = std::make_shared<rclcpp::Node>("test_node");
  BT::BehaviorTreeFactory factory;
  factory.registerNodeType<oxebots_strategy::HoldPositionNode>("HoldPosition", ros);

  auto bb = BT::Blackboard::create();
  bb->set("robot_id", 1u);
  auto tree = factory.createTreeFromText(
      R"(<root BTCPP_format="4"><BehaviorTree ID="T"><HoldPosition/></BehaviorTree></root>)", bb);

  // publica um GameData com o robô 1 em (500, -200) e processa as callbacks...
  EXPECT_EQ(tree.tickOnce(), BT::NodeStatus::RUNNING);
  // verifica que /robot_goal recebeu x = 0.5, y = -0.2
  tree.haltTree();                  // deve ser seguro chamar mais de uma vez
  tree.haltTree();
}
```

O padrão (criar fábrica, registrar, criar árvore a partir de texto, ticar, `haltTree`) vale para qualquer folha. Também é útil: `ros2 topic echo /robot_goal` em simulação e o Groot2 na porta do robô.

## Passo 8 — Simular e documentar

Com o sistema rodando em simulação (`ros2 launch oxebots_bringup ssl-new.launch.py bt_xml:=<arquivo>.xml`), verifique no Groot2 o ramo ativo, e confirme no RViz que o robô permanece parado. Por fim, registre a folha no catálogo (Apêndice B): ID, classe, portas com tipo e padrão, condições de SUCCESS/FAILURE/RUNNING e comportamento no `halt`.

## Quando usar publisher, serviço ou ação

Uma dúvida frequente é qual mecanismo ROS 2 usar para falar com outro nó:

| Necessidade | Mecanismo | Exemplo no projeto |
|---|---|---|
| Um valor que vale até mudar (último vence), sem resposta | **publisher** | `/robot_goal` |
| Pedido de modo físico, com TTL e retorno de status | **publisher** + assinatura de status | `RobotMotionOverride` / `RobotMotionStatus` |
| Estado compartilhado que todos precisam ver, mesmo quem entra depois | **assinatura `transient_local`** | `/field_geometry`, `/game_state` |
| Operação rara com resposta imediata | **serviço** | `SetDesiredKeeper`, `SubstituteBot` |
| Tarefa longa com feedback e **cancelamento** por outro processo | **action** | (não usado hoje) |

Uma *action* só vale a pena se outro processo executa a tarefa. Hoje, a árvore já cancela por `halt` + override, e o controlador fecha o laço; por isso as folhas do projeto são publicadores.
