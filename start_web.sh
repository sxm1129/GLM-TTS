#!/bin/bash
cd /data1/workspace/GLM-TTS
source /data1/miniconda3/bin/activate glm-tts_env
export PYTHONPATH=/data1/workspace/GLM-TTS:$PYTHONPATH
python -m tools.gradio_app


