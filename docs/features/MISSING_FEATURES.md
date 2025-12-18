# GLM-TTS Web界面缺失的高级功能

## 📊 功能对比

### ✅ 已集成到Web界面的功能

1. **基本零样本语音克隆** ✅
   - 上传参考音频
   - 输入提示文本和合成文本
   - 生成语音输出

2. **采样率选择** ✅
   - 24000 Hz（标准）
   - 32000 Hz（高质量）

3. **随机种子控制** ✅
   - 可设置随机种子用于结果复现

4. **KV缓存开关** ✅
   - 启用/禁用KV缓存以优化长文本生成

---

### ❌ 未集成到Web界面的高级功能

#### 1. **音素级别控制（Phoneme-in）** ⚠️

**功能描述**：
- 支持音素级别的文本到语音转换
- 可以解决多音字和生僻字的发音歧义问题
- 支持"Hybrid Phoneme + Text"混合输入

**代码支持**：
- `load_models()` 函数支持 `use_phoneme` 参数
- `generate_long()` 函数支持 `use_phoneme` 参数
- `TextFrontEnd` 类支持 `g2p_infer()` 方法

**当前状态**：
- Web界面中 `get_models()` 调用时设置了 `use_phoneme=True`
- 但 `generate_long()` 调用时硬编码为 `use_phoneme=False`
- **实际上音素功能未启用**

**建议**：
- 在Web界面添加"启用音素控制"开关
- 修复代码使其真正启用音素功能

---

#### 2. **采样方法选择** ❌

**功能描述**：
- 支持多种采样策略来控制生成质量

**代码支持**：
- `sample_method` 参数支持两种方法：
  - `"ras"`: Repetition-Aware Sampling（默认）
  - `"topk"`: Top-K采样

**当前状态**：
- Web界面硬编码为 `sample_method="ras"`
- 用户无法选择其他采样方法

**建议**：
- 添加采样方法选择下拉菜单
- 允许用户在"ras"和"topk"之间选择

---

#### 3. **采样参数（Sampling/Top-K）** ❌

**功能描述**：
- 控制采样时的候选token数量
- 影响生成结果的多样性和质量

**代码支持**：
- `local_llm_forward()` 函数支持 `sampling` 参数（默认25）
- 用于控制top-k采样的k值

**当前状态**：
- Web界面未暴露此参数
- 使用默认值25

**建议**：
- 添加采样参数滑块（范围：1-100）
- 允许用户调整生成多样性

---

#### 4. **Beam Search（束搜索）** ❌

**功能描述**：
- 使用束搜索可以生成更高质量的语音
- 通过探索多个候选路径选择最佳结果

**代码支持**：
- `local_llm_forward()` 函数支持 `beam_size` 参数（默认1）
- `llm.inference()` 方法支持beam search

**当前状态**：
- Web界面未暴露此参数
- 使用默认值1（即不使用beam search）

**建议**：
- 添加Beam Size选择（1-5）
- 注意：beam_size > 1会增加计算时间和显存占用

---

#### 5. **流式推理（Streaming Inference）** ❌

**功能描述**：
- 支持实时流式音频生成
- 适用于交互式应用场景
- 可以边生成边播放

**代码支持**：
- `flow/flow.py` 中有 `inference_with_cache()` 方法支持流式推理
- 支持 `is_causal` 和 `block_pattern` 参数

**当前状态**：
- Web界面未实现流式推理
- 需要等待完整生成后才能播放

**建议**：
- 实现流式推理功能
- 添加"启用流式生成"选项
- 实现音频流式播放

---

#### 6. **RL增强模型选择** ❌

**功能描述**：
- 项目提到有RL（强化学习）优化后的模型权重
- RL模型在CER指标上从1.03降低到0.89
- 情感表达更自然

**代码支持**：
- `grpo/` 目录包含RL训练相关代码
- 可能需要加载不同的模型权重

**当前状态**：
- Web界面只使用基础模型
- 未提供RL模型选择选项

**建议**：
- 如果RL模型权重可用，添加模型选择选项
- 允许用户在"基础模型"和"RL增强模型"之间选择

---

## 🔧 代码修改建议

### 1. 启用音素功能

**文件**: `tools/gradio_app.py`

**修改位置**: 第123行
```python
# 当前代码（错误）:
use_phoneme=False

# 应该改为:
use_phoneme=use_phoneme_flag  # 从UI获取
```

### 2. 添加采样方法选择

**文件**: `tools/gradio_app.py`

**需要添加**:
- UI组件：`gr.Radio(choices=["ras", "topk"], value="ras", label="采样方法")`
- 传递给 `generate_long()` 函数

### 3. 添加采样参数控制

**文件**: `tools/gradio_app.py`

**需要添加**:
- UI组件：`gr.Slider(minimum=1, maximum=100, value=25, step=1, label="采样参数")`
- 传递给 `local_llm_forward()` 函数

### 4. 添加Beam Search选项

**文件**: `tools/gradio_app.py`

**需要添加**:
- UI组件：`gr.Slider(minimum=1, maximum=5, value=1, step=1, label="Beam Size")`
- 传递给 `local_llm_forward()` 函数

---

## 📝 优先级建议

### 高优先级
1. **修复音素功能** - 代码已支持但未启用
2. **添加采样方法选择** - 简单易实现，影响明显

### 中优先级
3. **添加采样参数控制** - 提升用户体验
4. **添加Beam Search** - 提升质量但增加计算成本

### 低优先级
5. **实现流式推理** - 需要较大改动
6. **RL模型选择** - 需要确认模型权重可用性

---

## 🚀 快速修复示例

如果要快速启用音素功能，可以修改 `tools/gradio_app.py`:

```python
# 在第189行左右添加音素选项
use_phoneme = gr.Checkbox(
    label="启用音素控制", 
    value=False, 
    info="解决多音字和生僻字发音问题"
)

# 修改第77行
frontend, text_frontend, _, llm, flow = get_models(
    use_phoneme=use_phoneme,  # 从UI获取
    sample_rate=sample_rate
)

# 修改第123行
use_phoneme=use_phoneme  # 从UI获取，而不是False
```

---

## 📚 参考文档

- 项目README: `README.md` / `README_zh.md`
- 音素功能说明: README第109-120行
- 采样方法实现: `llm/glmtts.py` 第248-267行
- 流式推理实现: `flow/flow.py` 第90-167行


