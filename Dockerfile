# ROS 2 Humble Base with Python 3.10 / 3.11 for Robot Arm Manipulation
FROM ros:humble-ros-base-jammy

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system utilities, OpenCV dependencies, I2C tools, and audio capture
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    i2c-tools \
    libi2c-dev \
    alsa-utils \
    libasound2-dev \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ros2_ws

# Copy workspace
COPY . /ros2_ws/src/robot_arm_nlp

# Install Python requirements
RUN pip3 install --no-cache-dir -r /ros2_ws/src/robot_arm_nlp/requirements.txt || true

# Build ROS 2 workspace
RUN . /opt/ros/humble/setup.sh && \
    colcon build --symlink-install

# Entrypoint setup
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "source /ros2_ws/install/setup.bash" >> ~/.bashrc

EXPOSE 8000

CMD ["bash", "-c", "source /opt/ros/humble/setup.bash && source /ros2_ws/install/setup.bash && ros2 launch robot_arm_nlp full_system.launch.py"]
