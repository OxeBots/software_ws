# software_ws

This is the Oxebot software ROS2 workspace for SSL Robocup league. It agreggates the necessary repositories for the robot's software stack.

## Prerequisites

To run this workspace locally, you will need the following:

- Ubuntu 22.04
- [ROS2 Humble](https://docs.ros.org/en/humble/Installation.html)
- Git

## Installing

1. Clone this repository:

    ```bash
    git clone git@github.com:OxeBots/software_ws.git --recurse-submodule
    ```

2. Set up the workspace using the helper script:

    ```bash
    bash setup.sh
    ```

3. Build with the helper script:

    ```bash
    bash build.sh
    ```

Now you should be able to run the nodes and launch files.

## With Docker

Alternatively, you can run the workspace using DevContainers in Visual Studio Code using the [Remote Development](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack) extension pack. For that you need [Docker](https://docs.docker.com/engine/install/ubuntu/) installed in your machine.

If your machine has an Nvidia GPU, you can use the [Nvidia Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker) to run the workspace with GPU acceleration. Uncomment the lines 11 and 12 in the `.devcontainer/devcontainer.json` file to enable GPU acceleration.
