#!/bin/bash

# SVS Notion 服务启动脚本

# 设置 Notion 配置（请根据实际情况修改为你的真实值）
export NOTION_API_KEY="ntn_your_api_key_here"
export NOTION_DATABASE_ID="your_database_id_here"
export NOTION_DATA_SOURCE_ID="your_data_source_id_here"
export PORT=8001

# 启动服务
echo "正在启动 SVS Notion 服务..."
echo "监听端口: $PORT"
echo "数据库 ID: $NOTION_DATABASE_ID"
echo "Data Source ID: $NOTION_DATA_SOURCE_ID"

cd "$(dirname "$0")"
uvicorn main:app --host 0.0.0.0 --port $PORT
