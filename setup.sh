#!/bin/bash
set -e

git submodule update --init --recursive
sudo apt-get update
sudo apt install python3-pip
pip3 install numpy catkin_pkg empy==3.3.4
pip3 install lark --prefer-binary
rosdep update --rosdistro=$ROS_DISTRO
rosdep install --from-paths src --ignore-src -r -i -y --rosdistro=$ROS_DISTRO
