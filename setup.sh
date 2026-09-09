#!/bin/bash

git submodule update --init --recursive
sudo apt-get update
rosdep update --rosdistro=$ROS_DISTRO
rosdep install --from-paths src --ignore-src -r -i -y --rosdistro=$ROS_DISTRO
sudo chmod 666 /dev/ttyUSB*
sudo usermod -aG dialout $USER

sudo apt-get update && sudo apt-get install -y wget && \
cd /tmp && \
wget https://github.com/microsoft/onnxruntime/releases/download/v1.19.2/onnxruntime-linux-x64-1.19.2.tgz && \
sudo tar -xzf onnxruntime-linux-x64-1.19.2.tgz -C /usr/local --strip-components=1 && \
rm onnxruntime-linux-x64-1.19.2.tgz && \
sudo ldconfig

cd ../software_ws/