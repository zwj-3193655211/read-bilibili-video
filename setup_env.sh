#!/bin/bash

echo "========================================"
echo "B 站视频理解 Skill - 环境初始化"
echo "========================================"
echo ""

echo "[1/5] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.8+"
    exit 1
fi
python3 --version
echo ""

echo "[2/5] 创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[成功] 虚拟环境创建完成"
else
    echo "[信息] 虚拟环境已存在，跳过"
fi
echo ""

echo "[3/5] 激活虚拟环境..."
source venv/bin/activate
echo "[成功] 虚拟环境已激活"
echo ""

echo "[4/5] 升级 pip..."
pip install --upgrade pip -q
echo ""

echo "[5/5] 安装依赖..."
pip install -r requirements.txt
echo ""

echo "========================================"
echo "[6/6] 下载模型（首次使用约需 10 分钟）"
echo "模型大小约 900MB，请确保网络连接正常"
echo "========================================"
echo ""
read -p "是否立即下载模型？(y/N): " confirm
if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    python bilibili_video.py --init
else
    echo "[信息] 跳过模型下载，可在需要时运行：python bilibili_video.py --init"
fi

echo ""
echo "========================================"
echo "环境初始化完成！"
echo "========================================"
echo ""
echo "使用方法:"
echo "  python bilibili_video.py --status     检查状态"
echo "  python bilibili_video.py BV1xx411c7mD  分析视频"
echo "  python bilibili_video.py --clear-cache 清理缓存"
echo ""
