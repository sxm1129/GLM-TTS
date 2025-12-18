# GLM-TTS REST API 使用文档

## 📋 目录

- [概述](#概述)
- [基础信息](#基础信息)
- [API 端点](#api-端点)
- [请求参数](#请求参数)
- [响应格式](#响应格式)
- [使用示例](#使用示例)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)
- [性能说明](#性能说明)

---

## 概述

GLM-TTS REST API 提供了基于 GLM-TTS 模型的文本转语音（Text-to-Speech）服务。支持两种使用模式：

1. **索引模式（Index Mode）**：使用预配置的参考音频和提示文本
2. **上传模式（Upload Mode）**：上传自定义参考音频和提示文本

---

## 基础信息

### 服务地址

- **Base URL**: `http://[服务器IP]:8049`
- **API 版本**: `v1`
- **协议**: HTTP/HTTPS
- **数据格式**: `multipart/form-data` (文件上传) 或 `application/json`

### 认证

当前版本无需认证，后续版本可能添加 API Key 认证。

---

## API 端点

### 1. TTS 生成端点

**端点**: `POST /api/v1/tts`

**功能**: 生成文本转语音音频

**Content-Type**: `multipart/form-data`

---

## 请求参数

### 必需参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `input_text` | string | 要转换为语音的文本内容 |

### 可选参数 - Prompt 配置（二选一）

#### 方式1：索引模式

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `index` | string | 预配置的 prompt 索引名称 | `exampleA`, `exampleB` |

#### 方式2：上传模式

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `prompt_audio` | file | 参考音频文件（支持 .wav, .mp3, .flac 等格式） | 音频文件 |
| `prompt_text` | string | 参考音频对应的文本内容 | `"这是参考音频的文本"` |

**注意**: `index` 和 `prompt_audio`+`prompt_text` 二选一，不能同时使用。

### 可选参数 - 生成配置

| 参数名 | 类型 | 默认值 | 说明 | 取值范围 |
|--------|------|--------|------|----------|
| `seed` | integer | `42` | 随机种子，用于控制生成结果的随机性 | 任意整数 |
| `sample_rate` | integer | `24000` | 音频采样率 | `24000` 或 `32000` |
| `use_cache` | boolean | `true` | 是否使用 KV 缓存加速长文本生成 | `true` 或 `false` |
| `use_phoneme` | boolean | `false` | 是否启用音素控制，提高多音字和生僻字发音准确性 | `true` 或 `false` |
| `sample_method` | string | `"ras"` | 采样方法 | `"ras"` 或 `"topk"` |
| `sampling` | integer | `25` | 采样参数，控制生成多样性 | `1-100` |
| `beam_size` | integer | `1` | Beam Size（束搜索），值越大质量越高但速度越慢 | `1-5` |

### 参数说明

- **`sample_method`**:
  - `"ras"`: Repetition-Aware Sampling（推荐），减少重复
  - `"topk"`: Top-K 采样，传统方法

- **`sampling`**: 
  - 值越大，生成多样性越高，但可能降低质量
  - 推荐范围：`20-30`

- **`beam_size`**:
  - `1`: 贪心搜索，速度最快
  - `>1`: 束搜索，质量更高但耗时更长

---

## 响应格式

### 成功响应

```json
{
    "success": true,
    "message": "TTS generation successful",
    "audio_base64": "UklGRiQAAABXQVZFZm10...",
    "sample_rate": 24000,
    "generation_time": 44.13,
    "error": null
}
```

### 响应字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `success` | boolean | 请求是否成功 |
| `message` | string | 响应消息 |
| `audio_base64` | string | Base64 编码的 WAV 格式音频数据 |
| `sample_rate` | integer | 音频采样率（Hz） |
| `generation_time` | float | 音频生成耗时（秒），保留2位小数 |
| `error` | string/null | 错误信息（成功时为 null） |

### 错误响应

```json
{
    "success": false,
    "message": "TTS generation failed",
    "audio_base64": null,
    "sample_rate": null,
    "generation_time": 0.05,
    "error": "错误详情信息"
}
```

---

## 使用示例

### 示例 1: 使用索引模式生成短文本（Python）

```python
import requests
import base64
import json

# API 配置
API_URL = "http://your-server-ip:8049/api/v1/tts"

# 请求参数
data = {
    "input_text": "我是中国人，我深深爱着我的国家",
    "index": "exampleA",
    "seed": 42,
    "sample_rate": 24000,
    "use_cache": True,
    "use_phoneme": False,
    "sample_method": "ras",
    "sampling": 25,
    "beam_size": 1
}

# 发送请求
response = requests.post(API_URL, data=data)

# 解析响应
result = response.json()

if result["success"]:
    # 解码音频数据
    audio_data = base64.b64decode(result["audio_base64"])
    
    # 保存音频文件
    with open("output.wav", "wb") as f:
        f.write(audio_data)
    
    print(f"✅ 生成成功！")
    print(f"⏱️  生成时间: {result['generation_time']} 秒")
    print(f"🎵 采样率: {result['sample_rate']} Hz")
    print(f"📁 音频已保存到: output.wav")
else:
    print(f"❌ 生成失败: {result['error']}")
```

### 示例 2: 使用上传模式（Python）

```python
import requests
import base64
import json

# API 配置
API_URL = "http://your-server-ip:8049/api/v1/tts"

# 准备文件和数据
files = {
    "prompt_audio": open("reference_audio.wav", "rb")
}

data = {
    "input_text": "这是要合成的文本内容",
    "prompt_text": "这是参考音频中说的文本",
    "seed": 42,
    "sample_rate": 24000,
    "use_cache": True,
    "use_phoneme": False,
    "sample_method": "ras",
    "sampling": 25,
    "beam_size": 1
}

# 发送请求
response = requests.post(API_URL, files=files, data=data)

# 解析响应
result = response.json()

if result["success"]:
    audio_data = base64.b64decode(result["audio_base64"])
    with open("output.wav", "wb") as f:
        f.write(audio_data)
    print(f"✅ 生成成功，耗时: {result['generation_time']} 秒")
else:
    print(f"❌ 生成失败: {result['error']}")
```

### 示例 3: 使用 cURL（索引模式）

```bash
curl -X POST "http://your-server-ip:8049/api/v1/tts" \
  -F "input_text=中华人民共和国万岁，中央人民政府万岁" \
  -F "index=exampleA" \
  -F "seed=42" \
  -F "sample_rate=24000" \
  -F "use_cache=true" \
  -F "use_phoneme=false" \
  -F "sample_method=ras" \
  -F "sampling=25" \
  -F "beam_size=1" \
  -o response.json

# 解析并保存音频
python3 << EOF
import json
import base64

with open('response.json', 'r') as f:
    result = json.load(f)

if result['success']:
    audio_data = base64.b64decode(result['audio_base64'])
    with open('output.wav', 'wb') as f:
        f.write(audio_data)
    print(f"生成成功！耗时: {result['generation_time']} 秒")
else:
    print(f"生成失败: {result['error']}")
EOF
```

### 示例 4: 使用 cURL（上传模式）

```bash
curl -X POST "http://your-server-ip:8049/api/v1/tts" \
  -F "input_text=这是要合成的文本" \
  -F "prompt_text=这是参考音频的文本" \
  -F "prompt_audio=@/path/to/reference.wav" \
  -F "seed=42" \
  -F "sample_rate=24000" \
  -F "use_cache=true" \
  -F "use_phoneme=false" \
  -F "sample_method=ras" \
  -F "sampling=25" \
  -F "beam_size=1" \
  -o response.json
```

### 示例 5: JavaScript/Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

async function generateTTS(text, index = 'exampleA') {
    const formData = new FormData();
    formData.append('input_text', text);
    formData.append('index', index);
    formData.append('seed', 42);
    formData.append('sample_rate', 24000);
    formData.append('use_cache', 'true');
    formData.append('use_phoneme', 'false');
    formData.append('sample_method', 'ras');
    formData.append('sampling', 25);
    formData.append('beam_size', 1);

    try {
        const response = await axios.post(
            'http://your-server-ip:8049/api/v1/tts',
            formData,
            {
                headers: formData.getHeaders(),
                responseType: 'json'
            }
        );

        const result = response.data;
        
        if (result.success) {
            // 解码 Base64 音频
            const audioBuffer = Buffer.from(result.audio_base64, 'base64');
            
            // 保存音频文件
            fs.writeFileSync('output.wav', audioBuffer);
            
            console.log(`✅ 生成成功！`);
            console.log(`⏱️  生成时间: ${result.generation_time} 秒`);
            console.log(`🎵 采样率: ${result.sample_rate} Hz`);
            return audioBuffer;
        } else {
            console.error(`❌ 生成失败: ${result.error}`);
            return null;
        }
    } catch (error) {
        console.error('请求错误:', error.message);
        return null;
    }
}

// 使用示例
generateTTS('你好，世界！', 'exampleA');
```

### 示例 6: 处理长文本（Python 异步）

```python
import requests
import base64
import time

def generate_long_text(text, index="exampleA", timeout=300):
    """
    生成长文本音频，设置较长的超时时间
    
    Args:
        text: 要转换的文本
        index: prompt 索引
        timeout: 请求超时时间（秒），默认5分钟
    
    Returns:
        音频数据（bytes）或 None
    """
    API_URL = "http://your-server-ip:8049/api/v1/tts"
    
    data = {
        "input_text": text,
        "index": index,
        "seed": 42,
        "sample_rate": 24000,
        "use_cache": True,  # 长文本建议启用缓存
        "use_phoneme": False,
        "sample_method": "ras",
        "sampling": 25,
        "beam_size": 1
    }
    
    print(f"📝 文本长度: {len(text)} 字符")
    print(f"⏳ 开始生成，预计需要较长时间...")
    
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, data=data, timeout=timeout)
        response.raise_for_status()
        
        result = response.json()
        
        if result["success"]:
            elapsed = time.time() - start_time
            audio_data = base64.b64decode(result["audio_base64"])
            
            print(f"✅ 生成成功！")
            print(f"⏱️  API 返回耗时: {result['generation_time']} 秒")
            print(f"⏱️  总耗时（含网络）: {elapsed:.2f} 秒")
            print(f"📊 音频大小: {len(audio_data) / 1024 / 1024:.2f} MB")
            
            return audio_data
        else:
            print(f"❌ 生成失败: {result['error']}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（>{timeout}秒）")
        return None
    except Exception as e:
        print(f"❌ 请求错误: {str(e)}")
        return None

# 使用示例
long_text = """
这是一段很长的文本内容...
可以包含多段文字...
"""
audio = generate_long_text(long_text, index="exampleA")
if audio:
    with open("long_output.wav", "wb") as f:
        f.write(audio)
```

---

## 错误处理

### HTTP 状态码

| 状态码 | 说明 | 处理建议 |
|--------|------|----------|
| `200` | 请求成功 | 检查响应中的 `success` 字段 |
| `400` | 请求参数错误 | 检查参数格式和取值范围 |
| `404` | 资源未找到 | 检查 `index` 是否存在或音频文件路径是否正确 |
| `500` | 服务器内部错误 | 查看错误信息，联系管理员 |

### 常见错误

#### 1. 参数验证错误

```json
{
    "success": false,
    "message": "TTS generation failed",
    "error": "sample_rate must be 24000 or 32000",
    "generation_time": 0.01
}
```

**解决方案**: 检查 `sample_rate` 参数值是否为 `24000` 或 `32000`

#### 2. 索引不存在

```json
{
    "success": false,
    "message": "TTS generation failed",
    "error": "Prompt index 'exampleC' not found",
    "generation_time": 0.02
}
```

**解决方案**: 使用正确的索引名称，或先查询可用索引（见下方"Prompt 管理端点"）

#### 3. 音频文件不存在

```json
{
    "success": false,
    "message": "TTS generation failed",
    "error": "Audio file not found for index 'exampleA': /path/to/audio.wav",
    "generation_time": 0.03
}
```

**解决方案**: 检查音频文件路径是否正确，文件是否存在

#### 4. 参数冲突

```json
{
    "success": false,
    "message": "TTS generation failed",
    "error": "Either 'index' or both 'prompt_audio' and 'prompt_text' must be provided",
    "generation_time": 0.01
}
```

**解决方案**: 确保提供了 `index` 或同时提供了 `prompt_audio` 和 `prompt_text`

---

## Prompt 管理端点

### 1. 列出所有 Prompt 配置

**端点**: `GET /api/v1/prompts`

**示例**:

```bash
curl http://your-server-ip:8049/api/v1/prompts
```

**响应**:

```json
{
    "success": true,
    "prompts": [
        {
            "index": "exampleA",
            "config": {
                "prompt_audio_path": "examples/prompt/exampleA.mp3",
                "prompt_text": "儿时眼睛大，睡觉确实闭不上..."
            }
        },
        {
            "index": "exampleB",
            "config": {
                "prompt_audio_path": "examples/prompt/jiayan_zh1.wav",
                "prompt_text": "他当时还跟线下其他的站姐吵架..."
            }
        }
    ]
}
```

### 2. 获取指定 Prompt 配置

**端点**: `GET /api/v1/prompts/{index}`

**示例**:

```bash
curl http://your-server-ip:8049/api/v1/prompts/exampleA
```

### 3. 添加新的 Prompt 配置

**端点**: `POST /api/v1/prompts`

**参数**:

- `index` (string, 必需): 索引名称
- `prompt_audio_path` (string, 必需): 音频文件路径
- `prompt_text` (string, 必需): 提示文本

**示例**:

```bash
curl -X POST "http://your-server-ip:8049/api/v1/prompts" \
  -F "index=exampleC" \
  -F "prompt_audio_path=examples/prompt/new_audio.wav" \
  -F "prompt_text=这是新的参考文本"
```

### 4. 更新 Prompt 配置

**端点**: `PUT /api/v1/prompts/{index}`

**示例**:

```bash
curl -X PUT "http://your-server-ip:8049/api/v1/prompts/exampleA" \
  -F "prompt_audio_path=examples/prompt/updated.wav" \
  -F "prompt_text=更新后的参考文本"
```

### 5. 删除 Prompt 配置

**端点**: `DELETE /api/v1/prompts/{index}`

**示例**:

```bash
curl -X DELETE "http://your-server-ip:8049/api/v1/prompts/exampleC"
```

---

## 健康检查端点

### 检查服务状态

**端点**: `GET /api/v1/health`

**示例**:

```bash
curl http://your-server-ip:8049/api/v1/health
```

**响应**:

```json
{
    "status": "healthy",
    "model_loaded": true,
    "model_sample_rate": 24000,
    "model_use_phoneme": false,
    "prompt_cache_count": 2
}
```

---

## 最佳实践

### 1. 文本长度建议

- **短文本**（< 100 字）: 生成速度快，推荐使用
- **中等文本**（100-500 字）: 生成时间适中，质量稳定
- **长文本**（> 500 字）: 
  - 建议启用 `use_cache=true` 加速生成
  - 设置较长的请求超时时间（建议 5-10 分钟）
  - 考虑分段处理

### 2. 参数选择建议

#### 追求速度
```python
{
    "use_cache": True,
    "beam_size": 1,
    "sampling": 20
}
```

#### 追求质量
```python
{
    "use_cache": True,
    "beam_size": 3,
    "sampling": 30,
    "use_phoneme": True  # 提高发音准确性
}
```

#### 平衡质量和速度（推荐）
```python
{
    "use_cache": True,
    "beam_size": 1,
    "sampling": 25,
    "sample_method": "ras",
    "use_phoneme": False
}
```

### 3. 错误处理

```python
import requests
from requests.exceptions import RequestException, Timeout

def safe_generate_tts(text, index="exampleA", retries=3):
    """带重试机制的 TTS 生成"""
    API_URL = "http://your-server-ip:8049/api/v1/tts"
    
    data = {
        "input_text": text,
        "index": index,
        "seed": 42,
        "sample_rate": 24000,
        "use_cache": True,
        "use_phoneme": False,
        "sample_method": "ras",
        "sampling": 25,
        "beam_size": 1
    }
    
    for attempt in range(retries):
        try:
            response = requests.post(API_URL, data=data, timeout=300)
            response.raise_for_status()
            result = response.json()
            
            if result["success"]:
                return result
            else:
                print(f"尝试 {attempt + 1}/{retries} 失败: {result['error']}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    
        except Timeout:
            print(f"尝试 {attempt + 1}/{retries} 超时")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
        except RequestException as e:
            print(f"尝试 {attempt + 1}/{retries} 网络错误: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    
    return None
```

### 4. 音频格式处理

生成的音频是 Base64 编码的 WAV 格式，采样率为 24000 或 32000 Hz，单声道，16 位。

如果需要转换为其他格式，可以使用 `ffmpeg` 或音频处理库：

```python
import subprocess

# 转换为 MP3
subprocess.run([
    "ffmpeg", "-i", "output.wav", 
    "-acodec", "libmp3lame", 
    "-ab", "192k", 
    "output.mp3"
])

# 转换为其他采样率
subprocess.run([
    "ffmpeg", "-i", "output.wav", 
    "-ar", "16000", 
    "output_16k.wav"
])
```

### 5. 并发请求

如果需要批量生成，建议：

- 控制并发数量（建议不超过 3-5 个并发请求）
- 使用异步请求库（如 `aiohttp`）
- 实现请求队列和限流机制

```python
import asyncio
import aiohttp
from aiohttp import FormData

async def generate_tts_async(session, text, index="exampleA"):
    """异步生成 TTS"""
    url = "http://your-server-ip:8049/api/v1/tts"
    
    data = FormData()
    data.add_field('input_text', text)
    data.add_field('index', index)
    data.add_field('seed', '42')
    data.add_field('sample_rate', '24000')
    data.add_field('use_cache', 'true')
    data.add_field('use_phoneme', 'false')
    data.add_field('sample_method', 'ras')
    data.add_field('sampling', '25')
    data.add_field('beam_size', '1')
    
    async with session.post(url, data=data) as response:
        return await response.json()

async def batch_generate(texts, index="exampleA", max_concurrent=3):
    """批量生成，控制并发数"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def bounded_generate(session, text):
        async with semaphore:
            return await generate_tts_async(session, text, index)
    
    async with aiohttp.ClientSession() as session:
        tasks = [bounded_generate(session, text) for text in texts]
        results = await asyncio.gather(*tasks)
        return results

# 使用示例
texts = ["文本1", "文本2", "文本3"]
results = asyncio.run(batch_generate(texts, index="exampleA"))
```

---

## 性能说明

### 生成时间参考

| 文本长度 | 预计生成时间 | 说明 |
|----------|--------------|------|
| < 50 字 | 10-30 秒 | 短文本，速度快 |
| 50-200 字 | 30-60 秒 | 中等文本 |
| 200-500 字 | 60-120 秒 | 长文本 |
| > 500 字 | 120-300+ 秒 | 超长文本，建议分段 |

**注意**: 
- 首次请求可能较慢（需要加载模型）
- 启用 `use_cache` 可以加速长文本生成
- 实际时间取决于服务器硬件配置和当前负载

### 音频时长估算

音频时长（秒）≈ 文本字符数 × 0.15 - 0.25

例如：100 字的文本大约生成 15-25 秒的音频。

---

## 技术支持

如有问题或建议，请联系技术支持团队。

---

## 更新日志

### v1.0.0 (2025-12-17)

- ✅ 初始版本发布
- ✅ 支持索引模式和上传模式
- ✅ 添加生成时间统计
- ✅ 支持多种音频格式（.wav, .mp3, .flac）
- ✅ Prompt 配置管理功能
- ✅ 健康检查端点

---

## 附录

### A. 音频格式说明

- **格式**: WAV (PCM)
- **采样率**: 24000 Hz 或 32000 Hz
- **声道**: 单声道（Mono）
- **位深**: 16 位
- **编码**: Base64 字符串

### B. 支持的音频格式（参考音频）

- WAV (.wav)
- MP3 (.mp3)
- FLAC (.flac)
- 其他 `torchaudio` 支持的格式

### C. 常见问题（FAQ）

**Q: 如何选择合适的 `index`？**

A: 使用 `GET /api/v1/prompts` 查询所有可用的索引，选择与目标音色最匹配的索引。

**Q: 生成时间过长怎么办？**

A: 
- 检查是否启用了 `use_cache=true`
- 对于超长文本，考虑分段处理
- 降低 `beam_size` 值（如设为 1）

**Q: 如何提高发音准确性？**

A: 启用 `use_phoneme=true`，特别适用于多音字和生僻字较多的文本。

**Q: 音频质量不满意怎么办？**

A: 
- 尝试提高 `sample_rate` 到 32000（如果模型支持）
- 增加 `beam_size` 值（如 2-3）
- 调整 `sampling` 参数（推荐 25-30）
- 使用更高质量的参考音频

**Q: 支持实时流式生成吗？**

A: 当前版本不支持流式生成，需要等待完整音频生成后返回。

---

**文档版本**: 1.0.0  
**最后更新**: 2025-12-17


