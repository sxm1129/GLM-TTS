# GLM-TTS 部署完成总结

## ✅ 部署状态

**部署时间**: 2025-12-12  
**环境名称**: `glm-tts_env` (Conda)  
**Python版本**: 3.10  
**GPU**: L20 (CUDA 12.1)

## 📦 已完成的安装步骤

### 1. Conda环境创建
- ✅ 创建了conda环境 `glm-tts_env` (Python 3.10)

### 2. PyTorch安装
- ✅ torch==2.3.1+cu121
- ✅ torchvision==0.18.1+cu121
- ✅ torchaudio==2.3.1+cu121
- ✅ 所有CUDA 12.1相关依赖已安装

### 3. 项目依赖安装
- ✅ 已安装 `requirements.txt` 中的所有依赖包
- ✅ 包括: transformers, gradio, librosa, onnxruntime_gpu, deepspeed 等

### 4. ModelScope模型下载
- ✅ 已从 ModelScope 下载完整模型权重到 `ckpt/` 目录
- ✅ 包含以下组件:
  - `llm/` - 大语言模型权重
  - `flow/` - Flow模型权重
  - `speech_tokenizer/` - 语音tokenizer
  - `vocos2d/` - Vocos声码器
  - `hift/` - Hift声码器
  - `vq32k-phoneme-tokenizer/` - 音素tokenizer

## 🚀 使用方法

### 激活环境
```bash
conda activate glm-tts_env
cd /data1/workspace/GLM-TTS
```

### 运行推理示例

#### 1. 命令行推理
```bash
python glmtts_inference.py \
    --data=example_zh \
    --exp_name=_test \
    --use_cache
```

#### 2. 使用Shell脚本
```bash
bash glmtts_inference.sh
```

#### 3. 启动Gradio Web界面
```bash
python -m tools.gradio_app
```

### 启用音素功能（可选）
如果需要使用音素级别的发音控制，添加 `--phoneme` 参数：
```bash
python glmtts_inference.py \
    --data=example_zh \
    --exp_name=_test \
    --use_cache \
    --phoneme
```

## 📁 项目结构

```
GLM-TTS/
├── ckpt/                    # 模型权重目录（已下载）
│   ├── llm/                 # LLM模型
│   ├── flow/                # Flow模型
│   ├── speech_tokenizer/    # 语音tokenizer
│   ├── vocos2d/             # Vocos声码器
│   ├── hift/                # Hift声码器
│   └── vq32k-phoneme-tokenizer/  # 音素tokenizer
├── examples/                # 示例数据
├── configs/                 # 配置文件
├── glmtts_inference.py      # 主推理脚本
└── tools/                   # 工具脚本
    └── gradio_app.py        # Web界面
```

## ⚠️ 注意事项

1. **ffmpeg**: 系统依赖ffmpeg可能未安装（被dpkg锁占用），如需要可稍后手动安装：
   ```bash
   sudo apt-get install -y ffmpeg
   ```

2. **GPU显存**: L20 GPU显存充足，但如需处理长文本，注意监控显存使用

3. **模型路径**: 默认模型路径为 `ckpt/`，如需修改请参考 `glmtts_inference.py` 中的配置

## 🔍 验证安装

可以运行以下命令验证环境：
```bash
conda activate glm-tts_env
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"
```

## 📚 更多信息

- 项目README: `README.md` 或 `README_zh.md`
- ModelScope模型: https://modelscope.cn/models/ZhipuAI/GLM-TTS
- HuggingFace模型: https://huggingface.co/zai-org/GLM-TTS


