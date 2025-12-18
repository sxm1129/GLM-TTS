# GLM-TTS 优化架构建议

## 当前架构分析

### 现状
- **API 服务器**: FastAPI + uvicorn (单进程)
- **模型加载**: 全局共享 MODEL_CACHE
- **请求处理**: 直接调用推理函数，无并发控制
- **超时设置**: 无内置超时机制

## 优化方案分层建议

### 方案对比

| 优化项 | 在本项目实现 | 在调度层实现 | 推荐方案 |
|--------|------------|------------|---------|
| **并发限制** | ✅ 推荐 | ⚠️ 可选 | **本项目** |
| **请求队列** | ✅ 推荐 | ⚠️ 可选 | **本项目** |
| **超时设置** | ✅ 推荐 | ✅ 可选 | **两层都做** |
| **多进程部署** | ✅ 推荐 | ❌ 不适合 | **本项目** |
| **动态超时调整** | ✅ 推荐 | ⚠️ 可选 | **本项目** |

## 详细建议

### 1. 并发限制 (推荐: 本项目实现)

**为什么在本项目实现**:
- ✅ 了解模型的实际处理能力
- ✅ 可以基于文本长度动态调整
- ✅ 避免资源竞争导致的性能下降
- ✅ 提供更好的错误处理和反馈

**实现方式**:
```python
# 在 api_server.py 中添加
from asyncio import Semaphore

# 根据文本长度设置不同的并发限制
SHORT_TEXT_CONCURRENCY = 10  # 短文本并发数
LONG_TEXT_CONCURRENCY = 3   # 长文本并发数

short_text_semaphore = Semaphore(SHORT_TEXT_CONCURRENCY)
long_text_semaphore = Semaphore(LONG_TEXT_CONCURRENCY)

@app.post("/api/v1/tts")
async def generate_tts(...):
    # 根据文本长度选择不同的信号量
    text_length = len(input_text)
    semaphore = long_text_semaphore if text_length > 200 else short_text_semaphore
    
    async with semaphore:
        # 处理请求
        ...
```

**调度层实现** (备选):
- 使用 Nginx rate limiting
- 使用 API Gateway (如 Kong, Traefik)
- 优点: 不侵入业务代码
- 缺点: 无法根据文本长度动态调整

### 2. 请求队列 (推荐: 本项目实现)

**为什么在本项目实现**:
- ✅ 可以按优先级排序
- ✅ 可以基于文本长度智能调度
- ✅ 提供队列状态查询接口
- ✅ 更好的资源利用率

**实现方式**:
```python
# 使用 asyncio.Queue 实现请求队列
from asyncio import Queue
import asyncio

request_queue = Queue(maxsize=100)
worker_tasks = []

async def worker():
    """工作协程，从队列中取出请求并处理"""
    while True:
        request_data = await request_queue.get()
        try:
            # 处理请求
            await process_request(request_data)
        finally:
            request_queue.task_done()

@app.on_event("startup")
async def startup_event():
    # 启动多个工作协程
    for _ in range(5):
        worker_tasks.append(asyncio.create_task(worker()))

@app.post("/api/v1/tts")
async def generate_tts(...):
    # 将请求放入队列
    await request_queue.put({
        'input_text': input_text,
        ...
    })
    # 返回任务ID，客户端可以轮询状态
    return {"task_id": task_id, "status": "queued"}
```

**调度层实现** (备选):
- 使用消息队列 (RabbitMQ, Redis Queue)
- 使用任务调度系统 (Celery)
- 优点: 解耦，支持分布式
- 缺点: 增加系统复杂度，需要额外基础设施

### 3. 超时设置 (推荐: 两层都实现)

**在本项目实现**:
- ✅ 可以基于文本长度动态调整
- ✅ 提供更精确的超时控制
- ✅ 可以在超时前进行清理工作

**实现方式**:
```python
import asyncio

@app.post("/api/v1/tts")
async def generate_tts(...):
    text_length = len(input_text)
    
    # 根据文本长度动态设置超时
    if text_length > 200:
        timeout = 600  # 长文本 10 分钟
    else:
        timeout = 60   # 短文本 1 分钟
    
    try:
        result = await asyncio.wait_for(
            tts_inference_wrapper(...),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail=f"Request timeout after {timeout} seconds"
        )
```

**在调度层实现**:
- Nginx: `proxy_read_timeout`
- API Gateway: 超时配置
- 优点: 统一管理，不侵入代码
- 缺点: 无法根据文本长度动态调整

**最佳实践**: 两层都设置，调度层作为最后防线

### 4. 多进程部署 (推荐: 本项目实现)

**为什么在本项目实现**:
- ✅ 充分利用多核 CPU
- ✅ 提高并发处理能力
- ✅ 进程隔离，提高稳定性

**实现方式**:
```bash
# 修改 start_api.sh
uvicorn tools.api_server:app \
    --host 0.0.0.0 \
    --port 8049 \
    --workers 4  # 根据 CPU 核心数设置
```

**注意事项**:
- 每个进程会独立加载模型，需要足够的 GPU 显存
- 如果只有单 GPU，多进程可能不会带来性能提升
- 建议: 如果有多个 GPU，每个进程绑定一个 GPU

**调度层实现**: 不适用，这是应用层配置

### 5. 动态超时调整 (推荐: 本项目实现)

**为什么在本项目实现**:
- ✅ 可以精确计算预期处理时间
- ✅ 基于历史数据优化
- ✅ 提供更好的用户体验

**实现方式**:
```python
def calculate_timeout(text_length: int) -> int:
    """
    根据文本长度计算超时时间
    基于测试数据: 短文本 ~3.5秒, 长文本 ~80秒
    """
    if text_length <= 50:
        # 短文本: 基础时间 + 缓冲
        base_time = 3.5
        buffer = 10
        return int(base_time * 2 + buffer)  # ~17秒
    elif text_length <= 200:
        # 中等文本: 线性插值
        ratio = text_length / 200
        base_time = 3.5 + (80 - 3.5) * ratio
        return int(base_time * 1.5)  # 1.5倍缓冲
    else:
        # 长文本: 基础时间 + 缓冲
        base_time = 80
        buffer = 120  # 2分钟缓冲
        return int(base_time * 1.5 + buffer)  # ~240秒
```

**调度层实现**: 不适用，需要了解业务逻辑

## 推荐实现方案

### 方案 A: 在本项目实现 (推荐)

**优点**:
- ✅ 完整的控制权
- ✅ 可以基于业务逻辑优化
- ✅ 更好的用户体验
- ✅ 统一的错误处理

**缺点**:
- ⚠️ 需要修改代码
- ⚠️ 增加代码复杂度

**适用场景**:
- GLM-TTS 作为独立服务部署
- 需要精细化的性能控制
- 有开发资源进行优化

### 方案 B: 在调度层实现

**优点**:
- ✅ 不侵入业务代码
- ✅ 统一管理多个服务
- ✅ 易于扩展和维护

**缺点**:
- ❌ 无法基于文本长度动态调整
- ❌ 需要额外的基础设施
- ❌ 错误处理不够精细

**适用场景**:
- GLM-TTS 作为微服务的一部分
- 有统一的 API Gateway
- 需要快速上线，暂时不修改代码

### 方案 C: 混合方案 (最佳实践)

**分层实现**:
1. **本项目**: 实现核心优化
   - 并发限制 (基于文本长度)
   - 请求队列
   - 动态超时调整
   - 多进程部署配置

2. **调度层**: 实现保护机制
   - 全局超时限制 (最后防线)
   - 限流保护 (防止突发流量)
   - 负载均衡

**优点**:
- ✅ 最佳性能
- ✅ 多层保护
- ✅ 灵活可扩展

## 实施建议

### 阶段 1: 快速优化 (调度层)
1. 在 Nginx/API Gateway 配置超时和限流
2. 快速上线，缓解当前问题

### 阶段 2: 核心优化 (本项目)
1. 实现并发限制
2. 实现动态超时
3. 配置多进程部署

### 阶段 3: 高级优化 (本项目)
1. 实现请求队列
2. 添加监控和告警
3. 性能调优

## 代码示例

### 快速实现: 并发限制 + 动态超时

```python
# tools/api_server.py 中添加

from asyncio import Semaphore
import asyncio

# 并发限制
SHORT_TEXT_CONCURRENCY = 10
LONG_TEXT_CONCURRENCY = 3

short_text_semaphore = Semaphore(SHORT_TEXT_CONCURRENCY)
long_text_semaphore = Semaphore(LONG_TEXT_CONCURRENCY)

def get_timeout(text_length: int) -> int:
    """根据文本长度计算超时时间"""
    if text_length <= 50:
        return 60  # 短文本 1 分钟
    elif text_length <= 200:
        return 300  # 中等文本 5 分钟
    else:
        return 600  # 长文本 10 分钟

@app.post("/api/v1/tts", response_model=TTSResponse)
async def generate_tts(...):
    text_length = len(input_text)
    
    # 选择信号量
    semaphore = long_text_semaphore if text_length > 200 else short_text_semaphore
    timeout = get_timeout(text_length)
    
    async with semaphore:
        try:
            result = await asyncio.wait_for(
                process_tts_request(...),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=408,
                detail=f"Request timeout after {timeout} seconds"
            )
```

## 总结

**推荐方案**: **在本项目实现核心优化，调度层作为保护层**

- ✅ 并发限制: **本项目实现** (可以基于文本长度)
- ✅ 请求队列: **本项目实现** (更好的控制)
- ✅ 超时设置: **两层都实现** (本项目动态调整，调度层最后防线)
- ✅ 多进程部署: **本项目实现** (应用层配置)
- ✅ 动态超时: **本项目实现** (需要业务逻辑)

这样既能充分利用业务逻辑进行优化，又有调度层的保护，是最佳实践。


