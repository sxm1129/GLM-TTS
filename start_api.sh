#!/bin/bash
cd /data1/workspace/GLM-TTS
source /data1/miniconda3/bin/activate glm-tts_env
export PYTHONPATH=/data1/workspace/GLM-TTS:$PYTHONPATH

# 从环境变量读取工作进程数，默认1
WORKERS=${WORKERS:-1}

uvicorn tools.api_server:app \
    --host 0.0.0.0 \
    --port 8049 \
    --workers $WORKERS


