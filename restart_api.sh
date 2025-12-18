#!/bin/bash
# GLM-TTS API 服务重启脚本
# 功能：停止旧进程，释放显存，然后启动新服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GLM-TTS API 服务重启${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 1. 查找并停止旧进程
echo -e "${YELLOW}步骤 1: 查找运行中的 API 服务...${NC}"
API_PIDS=$(ps aux | grep -E "uvicorn.*api_server|api_server.*uvicorn" | grep -v grep | awk '{print $2}' || true)

if [ -z "$API_PIDS" ]; then
    echo -e "${GREEN}未发现运行中的 API 服务${NC}"
else
    echo -e "${YELLOW}发现运行中的进程: ${API_PIDS}${NC}"
    for PID in $API_PIDS; do
        echo -e "${YELLOW}正在停止进程 ${PID}...${NC}"
        kill -TERM $PID 2>/dev/null || true
    done
    
    # 等待进程优雅退出
    echo -e "${YELLOW}等待进程退出（最多 10 秒）...${NC}"
    sleep 2
    
    # 检查是否还有进程在运行
    REMAINING_PIDS=$(ps aux | grep -E "uvicorn.*api_server|api_server.*uvicorn" | grep -v grep | awk '{print $2}' || true)
    if [ ! -z "$REMAINING_PIDS" ]; then
        echo -e "${YELLOW}强制停止剩余进程...${NC}"
        for PID in $REMAINING_PIDS; do
            kill -9 $PID 2>/dev/null || true
        done
        sleep 1
    fi
    
    echo -e "${GREEN}旧进程已停止${NC}"
fi

# 2. 清理 Python 缓存和临时文件（可选）
echo ""
echo -e "${YELLOW}步骤 2: 清理临时文件...${NC}"
# 清理 __pycache__
find tools -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}临时文件已清理${NC}"

# 3. 清理 GPU 显存（通过 Python 脚本）
echo ""
echo -e "${YELLOW}步骤 3: 清理 GPU 显存...${NC}"
python3 << 'EOF' 2>/dev/null || true
import torch
if torch.cuda.is_available():
    torch.cuda.empty_cache()
    print("GPU cache cleared")
else:
    print("No GPU available")
EOF
echo -e "${GREEN}GPU 显存清理完成${NC}"

# 4. 等待一段时间确保资源释放
echo ""
echo -e "${YELLOW}步骤 4: 等待资源释放...${NC}"
sleep 2

# 5. 启动新服务
echo ""
echo -e "${GREEN}步骤 5: 启动新的 API 服务...${NC}"
echo ""

# 读取环境变量配置
SHORT_TEXT_CONCURRENCY=${SHORT_TEXT_CONCURRENCY:-10}
LONG_TEXT_CONCURRENCY=${LONG_TEXT_CONCURRENCY:-3}
WORKERS=${WORKERS:-1}

echo -e "${GREEN}配置信息:${NC}"
echo "  - 短文本并发数: $SHORT_TEXT_CONCURRENCY"
echo "  - 长文本并发数: $LONG_TEXT_CONCURRENCY"
echo "  - 工作进程数: $WORKERS"
echo ""

# 激活环境并启动服务
source /data1/miniconda3/bin/activate glm-tts_env
export PYTHONPATH=/data1/workspace/GLM-TTS:$PYTHONPATH

# 导出配置到环境变量
export SHORT_TEXT_CONCURRENCY
export LONG_TEXT_CONCURRENCY
export WORKERS

# 启动服务（后台运行）
echo -e "${GREEN}正在启动服务...${NC}"
nohup uvicorn tools.api_server:app \
    --host 0.0.0.0 \
    --port 8049 \
    --workers $WORKERS \
    > api_server.log 2>&1 &

NEW_PID=$!
echo -e "${GREEN}服务已启动，进程 ID: ${NEW_PID}${NC}"
echo ""

# 6. 等待服务启动并检查状态
echo -e "${YELLOW}等待服务启动（5 秒）...${NC}"
sleep 5

# 检查服务是否正常运行
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务运行正常${NC}"
    
    # 尝试访问健康检查端点
    if curl -s http://localhost:8049/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API 服务响应正常${NC}"
        echo ""
        echo -e "${GREEN}服务信息:${NC}"
        echo "  - 进程 ID: $NEW_PID"
        echo "  - 端口: 8049"
        echo "  - 日志文件: api_server.log"
        echo ""
        echo -e "${GREEN}查看日志: tail -f api_server.log${NC}"
        echo -e "${GREEN}查看状态: curl http://localhost:8049/api/v1/health${NC}"
        echo -e "${GREEN}查看并发统计: curl http://localhost:8049/api/v1/stats/concurrency${NC}"
    else
        echo -e "${YELLOW}⚠️  服务进程运行中，但 API 尚未就绪，请稍后检查${NC}"
        echo -e "${YELLOW}查看日志: tail -f api_server.log${NC}"
    fi
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    echo -e "${RED}请查看日志: tail -f api_server.log${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}重启完成！${NC}"
echo -e "${GREEN}========================================${NC}"

