cmake_minimum_required(VERSION 3.8)
project(oxebots_workspace)

# Só seve para o CLION não se perder, continue usando o colcon para buildar (build.sh)

set(CMAKE_PREFIX_PATH "/opt/ros/jazzy" "${CMAKE_CURRENT_SOURCE_DIR}/install" ${CMAKE_PREFIX_PATH})

set(ENV{AMENT_PREFIX_PATH} "/opt/ros/jazzy:${CMAKE_CURRENT_SOURCE_DIR}/install")
set(ENV{PYTHONPATH} "/opt/ros/jazzy/lib/python3.12/site-packages:$ENV{PYTHONPATH}")

add_subdirectory(src/oxebots_interfaces)
add_subdirectory(src/oxebots_bringup)
add_subdirectory(src/oxebots_comms)
add_subdirectory(src/oxebots_observers)
add_subdirectory(src/oxebots_prediction)
add_subdirectory(src/oxebots_strategy)

add_subdirectory(src/ssl_ros_bridge/ssl_league_protobufs)
add_subdirectory(src/ssl_ros_bridge/ssl_league_msgs)
add_subdirectory(src/ssl_ros_bridge/ssl_ros_bridge_msgs)
add_subdirectory(src/ssl_ros_bridge/ssl_ros_bridge)