# software_ws

This is the Oxebot software ROS2 workspace for the SSL Robocup league. It aggregates the necessary repositories for the robot's software stack.

## Prerequisites

To run this workspace locally, you will need the following:

- Ubuntu 22.04
- [ROS2 Humble](https://docs.ros.org/en/humble/Installation.html)
- Git

## Installing

1. **Clone this repository:**

    ```bash
    git clone git@github.com:OxeBots/software_ws.git --recurse-submodule
    ```

2. **Set up the workspace using the helper script:**

    ```bash
    bash setup.sh
    ```

3. **Build with the helper script:**

    ```bash
    bash build.sh [options]
    ```

    The `build.sh` script supports several options to customize the build process:

    - **Build Types:**
        - `Debug`
        - `Release`
        - `RelWithDebInfo` (default)
        - `MinSizeRel`

        **Usage:**

        ```bash
        bash build.sh Debug
        ```

    - **Run Tests:**
        - Add the `test` argument to run tests after building.

        **Usage:**

        ```bash
        bash build.sh test
        ```

    - **Reformat Code:**
        - Use the `reformat` argument to reformat the code according to style guidelines and add missing copyright.

        **Usage:**

        ```bash
        bash build.sh reformat
        ```

    - **Combine Options:**
        - You can combine multiple options in any order.

        **Examples:**

        ```bash
        # Build in Debug mode and run tests
        bash build.sh Debug test

        # Reformat code and build in Release mode
        bash build.sh reformat Release

        # Reformat code, run tests, and build with default settings
        bash build.sh reformat test
        ```

    **Note:** If you provide an unknown argument, the script will display an error message along with the list of valid arguments.

You should be able to run the nodes and launch files after sourcing the workspace:

```bash
source install/setup.bash
```

## With Docker

Alternatively, you can run the workspace using DevContainers in Visual Studio Code with the [Remote Development](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack) extension pack. For that, you need [Docker](https://docs.docker.com/engine/install/ubuntu/) installed on your machine.

If your machine has an Nvidia GPU, you can use the [Nvidia Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker) to run the workspace with GPU acceleration. Uncomment lines 11 and 12 in the `.devcontainer/devcontainer.json` file to enable GPU acceleration.
