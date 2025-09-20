
// #include "oxebots_strategy/follow_ball_node.h"



// namespace oxebots_strategy {
// FollowBallNode::FollowBallNode() : Node("follow_ball_node") {
//   game_data_sub_ = this->create_subscription<oxebots_interfaces::msg::GameData>(
//       "/game_data", 10,
//       std::bind(&FollowBallNode::ball_callback, this, std::placeholders::_1));

//   robot_cmd_pub_ = this->create_publisher<oxebots_interfaces::msg::RobotCommand>(
//       "/robot_command", 10);

//   RCLCPP_INFO(this->get_logger(), "Follow Ball (Goalkeeper) Node has started.");
// }

// void FollowBallNode::ball_callback(
//     const oxebots_interfaces::msg::GameData::SharedPtr msg) {
//   double y_bola = msg->ball.y;
//   double y_final = 0.0;

//   if (y_bola < MIN_Y_) {
//     y_final = MIN_Y_;
//   } else if (y_bola > MAX_Y_) {
//     y_final = MAX_Y_;
//   } else {
//     y_final = y_bola;
//   }

//   auto command = oxebots_interfaces::msg::RobotCommand();
//   command.robot_id = GOALKEEPER_ID_;
//   command.target_pose.x = GOALKEEPER_X_;
//   command.target_pose.y = y_final;
//   command.target_pose.theta = GOALKEEPER_THETA_;

//   robot_cmd_pub_->publish(command);
// }

// }  // namespace oxebots_strategy

// int main(int argc, char **argv) {
//   rclcpp::init(argc, argv);
//   auto node = std::make_shared<oxebots_strategy::FollowBallNode>();
//   rclcpp::spin(node);
//   rclcpp::shutdown();
//   return 0;
// }
