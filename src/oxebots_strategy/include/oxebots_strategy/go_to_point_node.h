#pragma once

#include "behaviortree_cpp/action_node.h"
#include "rclcpp/rclcpp.hpp"
#include "oxebots_interfaces/msg/robot_cmd.hpp"
#include "oxebots_interfaces/msg/robot_game_data.hpp"
#include "oxebots_interfaces/msg/robot_position.hpp"
#include <chrono>
#include <cmath>

namespace oxebots_strategy
{

class GoToPointNode : public BT::StatefulActionNode
{
public:
  GoToPointNode(const std::string& name, const BT::NodeConfig& config, rclcpp::Node::SharedPtr node);

  static BT::PortsList providedPorts();

  void setRobotId(unsigned int robot_ID) {robot_id_= robot_ID;}
  unsigned int getRobotId() {return robot_id_;} 
  void setTarget(double X, double Y, double W) {target_x_ = X; target_y_ = Y;  target_w_ = W;}
  void setCurrentPosition(double X, double Y, double W){current_x_ = X; current_y_ = Y; current_w_ = W; has_current_state_ = true;}

  BT::NodeStatus onStart() override;
  BT::NodeStatus onRunning() override;
  void onHalted() override;

private:
  rclcpp::Node::SharedPtr node_;
  rclcpp::Publisher<oxebots_interfaces::msg::RobotCmd>::SharedPtr publisher_;
  rclcpp::Subscription<oxebots_interfaces::msg::RobotPosition>::SharedPtr robot_state_sub_; // Subscriber para a posição do robô
  
  unsigned int robot_id_;
  double target_x_, target_y_, target_w_;
  double current_x_, current_y_, current_w_; // Posição atual do robô
  bool has_current_state_ = false; // Flag para garantir que temos a posição do robô

  // Callback do subscriber
  void robotStateCallback(const oxebots_interfaces::msg::RobotPosition::SharedPtr msg);

};

} // namespace oxebots_strategy