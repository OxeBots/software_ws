FROM osrf/ros:jazzy-desktop-full

ARG USERNAME=ros2
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN apt-get update && apt-get install -y \
    sudo git bash-completion wget \
    python3-serial python3-pip \
    libserialport-dev libboost-system-dev libboost-thread-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        ONNX_URL="https://github.com/microsoft/onnxruntime/releases/download/v1.19.2/onnxruntime-linux-x64-1.19.2.tgz"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        ONNX_URL="https://github.com/microsoft/onnxruntime/releases/download/v1.19.2/onnxruntime-linux-aarch64-1.19.2.tgz"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    wget $ONNX_URL -O /tmp/onnxruntime.tgz && \
    tar -xzf /tmp/onnxruntime.tgz -C /usr/local --strip-components=1 && \
    rm /tmp/onnxruntime.tgz && \
    ldconfig

RUN if id -u $USER_UID ; then userdel `id -un $USER_UID` ; fi && \
    groupadd --gid $USER_GID $USERNAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/bash && \
    echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME && \
    usermod --append --groups video,dialout $USERNAME

USER $USERNAME
WORKDIR /home/$USERNAME

RUN pip3 install bitproto bitprotolib --break-system-packages

RUN echo "if [ -f /opt/ros/${ROS_DISTRO}/setup.bash ]; then source /opt/ros/${ROS_DISTRO}/setup.bash; fi" >> ~/.bashrc && \
    echo "if [ -f /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash ]; then source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash; fi" >> ~/.bashrc

ENV SHELL=/bin/bash
CMD ["/bin/bash"]