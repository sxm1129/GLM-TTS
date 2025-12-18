# GLM-TTS API 服务管理指南

## 服务管理脚本

### 1. restart_api.sh - 重启服务脚本

**功能**:
- 自动停止旧进程
- 清理 GPU 显存
- 释放资源
- 启动新服务
- 验证服务状态

**使用方法**:

#### 使用默认配置启动
```bash
bash restart_api.sh
```

#### 使用自定义配置启动
```bash
# 设置并发限制
SHORT_TEXT_CONCURRENCY=15 LONG_TEXT_CONCURRENCY=5 bash restart_api.sh

# 设置并发限制和工作进程数
SHORT_TEXT_CONCURRENCY=15 LONG_TEXT_CONCURRENCY=5 WORKERS=2 bash restart_api.sh

# 设置所有配置
SHORT_TEXT_CONCURRENCY=15 \
LONG_TEXT_CONCURRENCY=5 \
LONG_TEXT_TIMEOUT=900 \
WORKERS=1 \
bash restart_api.sh
```

**脚本执行步骤**:
1. 查找并停止运行中的 API 服务进程
2. 清理临时文件和 Python 缓存
3. 清理 GPU 显存
4. 等待资源释放
5. 启动新服务（使用环境变量配置）
6. 验证服务状态

### 2. start_api.sh - 启动服务脚本

**功能**: 直接启动服务（不停止旧进程）

**使用方法**:
```bash
# 默认配置
bash start_api.sh

# 自定义配置
WORKERS=4 bash start_api.sh
```

## 配置说明

### 环境变量配置

所有配置都可以通过环境变量设置：

```bash
# 并发限制
export SHORT_TEXT_CONCURRENCY=15  # 短文本并发数
export LONG_TEXT_CONCURRENCY=5    # 长文本并发数
export TEXT_LENGTH_THRESHOLD=200  # 文本长度阈值

# 超时配置（秒）
export SHORT_TEXT_TIMEOUT=60      # 短文本超时
export MEDIUM_TEXT_TIMEOUT=300    # 中等文本超时
export LONG_TEXT_TIMEOUT=600      # 长文本超时

# 多进程配置
export WORKERS=1                  # 工作进程数
```

### 推荐配置

**短文本为主场景**:
```bash
SHORT_TEXT_CONCURRENCY=20 \
LONG_TEXT_CONCURRENCY=3 \
WORKERS=1 \
bash restart_api.sh
```

**长文本为主场景**:
```bash
SHORT_TEXT_CONCURRENCY=10 \
LONG_TEXT_CONCURRENCY=5 \
LONG_TEXT_TIMEOUT=900 \
WORKERS=1 \
bash restart_api.sh
```

**高并发场景（多 GPU）**:
```bash
SHORT_TEXT_CONCURRENCY=15 \
LONG_TEXT_CONCURRENCY=5 \
WORKERS=4 \
bash restart_api.sh
```

## 服务管理命令

### 查看服务状态
```bash
# 检查进程
ps aux | grep uvicorn | grep api_server

# 检查端口
lsof -i :8049

# 健康检查
curl http://localhost:8049/api/v1/health

# 查看并发统计
curl http://localhost:8049/api/v1/stats/concurrency
```

### 查看日志
```bash
# 实时查看日志
tail -f api_server.log

# 查看最近 50 行
tail -50 api_server.log

# 搜索错误
grep -i error api_server.log
```

### 停止服务
```bash
# 方法1: 使用 restart_api.sh（推荐）
bash restart_api.sh  # 会先停止旧进程

# 方法2: 手动停止
pkill -f "uvicorn.*api_server"

# 方法3: 根据进程ID停止
kill <PID>
```

## 服务验证

### 1. 检查服务是否运行
```bash
curl http://localhost:8049/api/v1/health
```

**预期响应**:
```json
{
    "status": "healthy",
    "model_loaded": true,
    "model_sample_rate": 24000,
    "model_use_phoneme": false,
    "prompt_cache_count": 2
}
```

### 2. 检查并发配置
```bash
curl http://localhost:8049/api/v1/stats/concurrency
```

**预期响应**:
```json
{
    "success": true,
    "stats": {
        "short_text": {
            "active": 0,
            "total": 0,
            "limit": 15,
            "available": 15
        },
        "long_text": {
            "active": 0,
            "total": 0,
            "limit": 5,
            "available": 5
        }
    },
    "config": {
        "concurrency": {
            "short_text": 15,
            "long_text": 5,
            "threshold": 200
        },
        ...
    }
}
```

### 3. 测试 API 调用
```bash
curl -X POST http://localhost:8049/api/v1/tts \
  -F "input_text=测试文本" \
  -F "index=exampleA" \
  -F "sample_rate=24000"
```

## 故障排查

### 问题1: 服务启动失败

**检查项**:
1. 检查端口是否被占用: `lsof -i :8049`
2. 检查日志: `tail -f api_server.log`
3. 检查 GPU 显存: `nvidia-smi`
4. 检查 Python 环境: `which python3`

### 问题2: 配置未生效

**检查项**:
1. 确认环境变量已设置
2. 检查统计接口: `curl http://localhost:8049/api/v1/stats/concurrency`
3. 确认使用了 `restart_api.sh` 重启服务

### 问题3: 显存未释放

**解决方法**:
1. 使用 `restart_api.sh` 脚本（会自动清理显存）
2. 手动清理: `python3 -c "import torch; torch.cuda.empty_cache()"`
3. 重启服务

## 性能监控

### 监控指标

1. **并发使用情况**: `/api/v1/stats/concurrency`
2. **服务健康状态**: `/api/v1/health`
3. **系统资源**: `nvidia-smi`, `htop`

### 告警建议

- 并发使用率 > 80%
- 响应时间 > 预期超时时间的 50%
- GPU 显存使用率 > 90%
- 服务健康检查失败

## 最佳实践

1. **使用 restart_api.sh**: 确保资源完全释放
2. **监控并发统计**: 定期检查 `/api/v1/stats/concurrency`
3. **根据负载调整**: 根据实际使用情况调整并发限制
4. **日志管理**: 定期清理或轮转日志文件
5. **备份配置**: 保存有效的配置组合

## 示例场景

### 场景1: 日常使用
```bash
# 默认配置，适合大多数场景
bash restart_api.sh
```

### 场景2: 高并发短文本
```bash
SHORT_TEXT_CONCURRENCY=20 bash restart_api.sh
```

### 场景3: 长文本处理
```bash
LONG_TEXT_CONCURRENCY=5 LONG_TEXT_TIMEOUT=900 bash restart_api.sh
```

### 场景4: 多进程部署（多 GPU）
```bash
WORKERS=4 bash restart_api.sh
```

