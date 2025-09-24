#include "oxebots_strategy/go_to_point_node.h"

namespace oxebots_strategy
{

GoToPointNode::GoToPointNode(const std::string& name, const BT::NodeConfig& config, rclcpp::Node::SharedPtr node)
  : BT::StatefulActionNode(name, config), node_(node)
{
  publisher_ = node_->create_publisher<oxebots_interfaces::msg::RobotCmd>("/robot_commands", 10);
   RCLCPP_INFO(node_->get_logger(), "!!! Construtor do GoToPointNode executado. Publisher criado. !!!");
}

BT::PortsList GoToPointNode::providedPorts()
{
  // As portas não são usadas neste exemplo simples, mas podemos mantê-las
  return { BT::InputPort<unsigned int>("robot_id"),
           BT::InputPort<double>("x"),
           BT::InputPort<double>("y"),
           BT::InputPort<double>("w") };
}

BT::NodeStatus GoToPointNode::onStart()
{
  RCLCPP_INFO(node_->get_logger(), "Iniciando 'AndarParaFrente'");
    // MODIFICADO: Lógica com verificação de tempo
  unsigned int robot_id = 0;
  getInput<unsigned int>("robot_id", robot_id);

  oxebots_interfaces::msg::RobotCmd msg;
  oxebots_interfaces::msg::RobotCmdData robot_data;
  robot_data.id = robot_id;
  
  float forward_speed = 100.0;
  robot_data.x_velocity = forward_speed;  // Velocidade para frente
  robot_data.y_velocity = 0.0;            // Sem movimento lateral
  robot_data.angular_velocity = 0.0;      // Sem rotação

  msg.robots.push_back(robot_data);
  publisher_->publish(msg);
  RCLCPP_INFO(node_->get_logger(), "Enviando 'AndarParaFrente'");
  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus GoToPointNode::onRunning()
{

  
  return BT::NodeStatus::RUNNING; // Continue rodando...
}

void GoToPointNode::onHalted()
{
  // onHalted é chamado se a ação for interrompida. É importante parar o robô aqui também.
  RCLCPP_WARN(node_->get_logger(), "Ação 'AndarParaFrente' interrompida. Parando o robô.");
  
  oxebots_interfaces::msg::RobotCmd msg;
  oxebots_interfaces::msg::RobotCmdData robot_data;
  robot_data.id = 0;
  robot_data.x_velocity = 0.0;
  robot_data.y_velocity = 0.0;
  robot_data.angular_velocity = 0.0;
  msg.robots.push_back(robot_data);
  publisher_->publish(msg);
}

}  // namespace oxebots_strategy