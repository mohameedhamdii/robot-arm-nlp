# Models Directory

This directory stores quantized model weights used for on-device reasoning and perception:

## Supported Models

### 1. Large Language Model (Task Planner)
- **Model**: `phi-3-mini-4k-instruct.Q4_K_M.gguf` (~2.3 GB) or `TinyLlama-1.1B-Chat-v1.0.Q4_K_M.gguf` (~600 MB)
- **Format**: GGUF (4-bit quantized)
- **Runtime**: `llama-cpp-python` / `llama.cpp`
- **Fallback**: If no GGUF file is downloaded, the task planner automatically falls back to the deterministic heuristic rule parser or local Ollama endpoint.

### 2. Speech-to-Text (Voice Capture)
- **Model**: `ggml-base.en.bin` (~140 MB)
- **Format**: GGML
- **Runtime**: `whisper.cpp` CLI (`whisper-cpp`)

### 3. Object Detection (Vision Upgrade)
- **Model**: `yolov8n_blocks.onnx` (~6 MB)
- **Runtime**: OpenCV DNN ONNX backend

To download models automatically, run:
```bash
bash scripts/download_models.sh
```
