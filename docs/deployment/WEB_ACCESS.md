# GLM-TTS Web界面访问说明

## ✅ Web服务状态

**服务状态**: ✅ 已启动并运行  
**进程ID**: 535163  
**监听端口**: 8048  
**服务器IP**: 172.16.85.214  
**HTTP状态**: ✅ 正常响应 (200 OK)

## 🌐 访问方式

### 方式1: 本地访问
如果在本机访问，打开浏览器访问：
```
http://localhost:8048
```

### 方式2: 远程访问
如果从其他机器访问，使用服务器IP：
```
http://172.16.85.214:8048
```

## 📝 使用说明

### 1. 上传提示音频（Prompt Audio）
- 点击"Upload Prompt Audio"上传参考音频文件
- 默认已加载示例音频：`examples/prompt/jiayan_zh.wav`
- 建议使用3-10秒的清晰语音作为参考

### 2. 输入提示文本（Prompt Text）
- 在"Prompt Text"框中输入提示音频中说的确切文本
- 默认示例：`他当时还跟线下其他的站姐吵架，然后，打架进局子了。`
- 准确的提示文本可以提高说话人相似度

### 3. 输入要合成的文本（Text to Synthesize）
- 在"Text to Synthesize"框中输入要转换为语音的文本
- 默认示例：`我最爱吃人参果，你喜欢吃吗？`
- 支持中文和英文混合文本

### 4. 高级设置（Advanced Settings）

#### 基础设置
- **Sample Rate (Hz)**: 选择采样率
  - `24000`: 标准质量（默认）
  - `32000`: 更高质量（如果模型支持）
- **Seed**: 随机种子，用于控制生成结果的随机性（默认：42）
- **Use KV Cache**: 启用KV缓存，长文本生成更快（默认：启用）

#### 高级功能（新增）
- **启用音素控制 (Phoneme Control)**: 
  - 解决多音字和生僻字发音问题
  - 提高发音准确性
  
- **采样方法 (Sampling Method)**:
  - `ras`: Repetition-Aware Sampling（推荐，默认）
  - `topk`: Top-K采样
  
- **采样参数 (Sampling/Top-K)**: 
  - 范围：1-100（默认：25）
  - 控制生成多样性
  
- **Beam Size (束搜索)**: 
  - 范围：1-5（默认：1）
  - 值越大质量越高，但速度越慢

### 5. 生成音频
- 点击"🚀 Generate Audio"按钮开始生成
- 生成完成后，音频将显示在"Output"区域
- 可以播放、下载生成的音频文件

### 6. 清理显存
- 如果遇到显存不足，点击"🧹 Clear VRAM"按钮清理显存
- 清理后，下次推理时会重新加载模型

## 🔧 服务管理

### 查看服务状态
```bash
# 检查端口是否监听
lsof -i :8048
# 或
netstat -tlnp | grep 8048
```

### 查看服务日志
```bash
cd /data1/workspace/GLM-TTS
tail -f gradio_output.log
```

### 重启服务
```bash
cd /data1/workspace/GLM-TTS
# 停止服务
pkill -f "gradio_app"

# 启动服务
source /data1/miniconda3/bin/activate glm-tts_env
nohup python -m tools.gradio_app > gradio_output.log 2>&1 &
```

### 停止服务
```bash
pkill -f "gradio_app"
```

## ⚠️ 注意事项

1. **首次加载**: 首次使用时，模型加载可能需要几分钟时间，请耐心等待
2. **显存要求**: L20 GPU显存充足，但处理长文本时注意监控显存使用
3. **网络访问**: 如果无法访问，请检查防火墙设置，确保8048端口开放
4. **示例音频**: 默认使用的示例音频位于 `examples/prompt/` 目录

## 🐛 故障排除

### 问题1: 无法访问Web界面
- 检查服务是否运行：`ps aux | grep gradio_app`
- 检查端口是否监听：`lsof -i :8048`
- 检查防火墙设置

### 问题2: 生成失败
- 检查日志：`tail -f gradio_output.log`
- 确保提示音频和文本匹配
- 尝试清理显存后重新生成

### 问题3: 显存不足
- 点击"Clear VRAM"按钮
- 或重启服务释放显存

## 📚 更多信息

- 项目文档: `README.md` 或 `README_zh.md`
- 部署文档: `DEPLOYMENT.md`
- ModelScope: https://modelscope.cn/models/ZhipuAI/GLM-TTS

