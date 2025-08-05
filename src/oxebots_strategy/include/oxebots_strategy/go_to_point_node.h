#ifndef OXEBOTS_STRATEGY__GO_TO_POINT_NODE_H
#define OXEBOTS_STRATEGY__GO_TO_POINT_NODE_H

#include "behaviortree_cpp/behavior_tree.h"
#include "rclcpp/rclcpp.hpp"
#include "oxebots_interfaces/msg/robot_command.hpp"

namespace oxebots_strategy
{

class GoToPointNode : public BT::StatefulActionNode
{
public:
  GoToPointNode(const std::string& name, const BT::NodeConfig& config, rclcpp::Node::SharedPtr node);

  static BT::PortsList providedPorts();

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  rclcpp::Node::SharedPtr node_;
  rclcpp::Publisher<oxebots_interfaces::msg::RobotCommand>::SharedPtr publisher_;
  std::chrono::time_point<std::chrono::steady_clock> start_time_;
};

}  // namespace oxebots_strategy

#endif  // OXEBOTS_STRATEGY__GO_TO_POINT_NODE_H
