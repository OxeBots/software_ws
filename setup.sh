#!/bin/bash

git submodule update --init --recursive
sudo apt-get update
rosdep update --rosdistro=$ROS_DISTRO
rosdep install --from-paths src --ignore-src -r -i -y --rosdistro=$ROS_DISTRO
