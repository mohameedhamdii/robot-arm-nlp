#!/usr/bin/env bash
# ==============================================================================
# Model Downloader for Robot Arm NLP
# Downloads quantized LLM GGUF models and Whisper STT models
# ==============================================================================
set -e

MODELS_DIR="models"
mkdir -p "$MODELS_DIR"

echo "============================================================"
echo " Robot Arm Model Downloader"
echo "============================================================"

# Default LLM: Phi-3 Mini 4K Instruct GGUF (~2.3 GB)
PHI3_URL="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
PHI3_DEST="$MODELS_DIR/phi-3-mini-4k-instruct.Q4_K_M.gguf"

if [ ! -f "$PHI3_DEST" ]; then
    echo "Downloading Phi-3 Mini 4K Instruct GGUF..."
    curl -L "$PHI3_URL" -o "$PHI3_DEST"
else
    echo "Phi-3 GGUF model already exists at $PHI3_DEST"
fi

# Whisper Speech Model (Base English ~140 MB)
WHISPER_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
WHISPER_DEST="$MODELS_DIR/ggml-base.en.bin"

if [ ! -f "$WHISPER_DEST" ]; then
    echo "Downloading Whisper base.en model..."
    curl -L "$WHISPER_URL" -o "$WHISPER_DEST"
else
    echo "Whisper model already exists at $WHISPER_DEST"
fi

echo "All models ready in ./$MODELS_DIR"
