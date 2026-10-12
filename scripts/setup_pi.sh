#!/usr/bin/env bash
# ==============================================================================
# Setup Script for Raspberry Pi 5 - Natural Language Controlled Robot Arm
# ==============================================================================
set -e

echo "============================================================"
echo " Setting up Robot Arm NLP on Raspberry Pi 5..."
echo "============================================================"

# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Install essential build tools, I2C, ALSA, OpenCV dependencies
sudo apt-get install -y \
    python3-pip \
    python3-dev \
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
    cmake \
    build-essential

# Enable I2C interface on Raspberry Pi
echo "Enabling I2C bus..."
if ! grep -q "^i2c-dev" /etc/modules; then
    echo "i2c-dev" | sudo tee -a /etc/modules
fi
sudo dtparam i2c_arm=on || true

# Add current user to i2c, video, and audio groups
sudo usermod -aG i2c,video,audio "$USER"

# Install Python requirements
echo "Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Install whisper.cpp CLI (optional for voice)
if [ ! -d "whisper.cpp" ]; then
    echo "Cloning and building whisper.cpp for lightweight speech-to-text..."
    git clone https://github.com/ggerganov/whisper.cpp.git
    cd whisper.cpp
    make -j4
    # Download tiny model
    bash ./models/download-ggml-model.sh base.en
    sudo cp main /usr/local/bin/whisper-cpp || true
    cd ..
fi

# Build ROS 2 workspace if ROS 2 Humble is installed
if [ -f "/opt/ros/humble/setup.bash" ]; then
    echo "Building ROS 2 package with colcon..."
    source /opt/ros/humble/setup.bash
    colcon build --symlink-install
    echo "source $(pwd)/install/setup.bash" >> ~/.bashrc
fi

echo "============================================================"
echo " Setup complete! Please reboot your Pi to apply I2C permissions:"
echo "   sudo reboot"
echo "============================================================"
