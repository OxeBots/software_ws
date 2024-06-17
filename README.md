# software_ws

This is the Oxebot software ROS2 workspace for SSL Robocup league. It agreggates the necessary repositories for the robot's software stack.

## Prerequisites

- Ubuntu 22.04
- [ROS2 Humble](https://docs.ros.org/en/humble/Installation.html)
- Git

## Installing

1. Clone this repository:

    ```bash
    git clone git@github.com:OxeBots/software_ws.git --recurse-submodule
    ```

2. Source the ROS2 installation:

    ```bash
    source /opt/ros/$ROS_DISTRO/setup.bash
    ```

3. Install the dependencies:

    ```bash
    cd software_ws
    rosdep install --from-paths src --ignore-src -r -i -y --rosdistro $ROS_DISTRO
    ```

4. Build the workspace:

    ```bash
    colcon build --mixin compile-commands
    ```

5. Source the workspace:

    ```bash
    source install/setup.bash
    ```

Now you should be able to run the nodes and launch files.
