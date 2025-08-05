

#include "oxebots_strategy/go_to_point_node.h"

namespace oxebots_strategy
{

GoToPointNode::GoToPointNode(const std::string& name, const BT::NodeConfig& config, rclcpp::Node::SharedPtr node)
  : BT::StatefulActionNode(name, config), node_(node)
{
  publisher_ = node_->create_publisher<oxebots_interfaces::msg::RobotCommand>("/robot_command", 10);
}

BT::PortsList GoToPointNode::providedPorts()
{
  return { BT::InputPort<unsigned int>("robot_id"),
           BT::InputPort<double>("x"),
           BT::InputPort<double>("y"),
           BT::InputPort<double>("w") };
}

BT::NodeStatus GoToPointNode::onStart()
{
  unsigned int robot_id;
  double x, y, w;

  if (!getInput<unsigned int>("robot_id", robot_id) ||
      !getInput<double>("x", x) ||
      !getInput<double>("y", y) ||
      !getInput<double>("w", w))
  {
    RCLCPP_ERROR(node_->get_logger(), "Missing required input ports");
    return BT::NodeStatus::FAILURE;
  }

  oxebots_interfaces::msg::RobotCommand msg;
  msg.robot_id = robot_id;
  msg.target_x = x;
  msg.target_y = y;
  msg.target_w = w;

  publisher_->publish(msg);
  start_time_ = std::chrono::steady_clock::now();

  return BT::NodeStatus::RUNNING;
}

BT::NodeStatus GoToPointNode::onRunning()
{
  // For now, we'll just use a timeout to simulate reaching the destination.
  // In a real scenario, you would subscribe to the robot's position and check if it has reached the target.
  auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - start_time_);
  if (elapsed.count() > 2)  // 2 second timeout
  {
    return BT::NodeStatus::SUCCESS;
  }

  return BT::NodeStatus::RUNNING;
}

void GoToPointNode::onHalted()
{
  // Stop the robot by sending a command with zero velocity
  oxebots_interfaces::msg::RobotCommand msg;
  // We need the robot_id to stop the correct robot.
  // It's good practice to store it from onStart() if needed here.
  unsigned int robot_id;
  if (getInput<unsigned int>("robot_id", robot_id))
  {
    msg.robot_id = robot_id;
    msg.target_x = 0; // Or current position
    msg.target_y = 0; // Or current position
    msg.target_w = 0;
    publisher_->publish(msg);
  }
}

}  // namespace oxebots_strategy
