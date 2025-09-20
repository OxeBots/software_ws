// #ifndef OXEBOTS_STRATEGY_FOLLOW_BALL_NODE_H
// #define OXEBOTS_STRATEGY_FOLLOW_BALL_NODE_H

// #include "oxebots_interfaces/msg/game_data.hpp"
// #include "oxebots_interfaces/msg/robot_command.hpp"
// #include "rclcpp/rclcpp.hpp"

// namespace oxebots_strategy {
// class FollowBallNode : public rclcpp::Node {
//  public:
//   FollowBallNode();
  

//  private:
//   void ball_callback(const oxebots_interfaces::msg::GameData::SharedPtr msg);

//   rclcpp::Subscription<oxebots_interfaces::msg::GameData>::SharedPtr
//       game_data_sub_;
//   rclcpp::Publisher<oxebots_interfaces::msg::RobotCommand>::SharedPtr
//       robot_cmd_pub_;

//   const int GOALKEEPER_ID_ = 0;
//   const double GOALKEEPER_X_ = -5500.0;
//   const double GOALKEEPER_THETA_ = 0.0;
//   const double MIN_Y_ = 1100.0;
//   const double MAX_Y_ = 1900.0;
// };
// }  // namespace oxebots_strategy

// #endif  // OXEBOTS_STRATEGY_FOLLOW_BALL_NODE_H
