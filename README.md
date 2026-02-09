# svs_notion

基于 Notion 官方 API 和 FastAPI 的标准访问服务，将 Notion 数据库作为**多网站共享的中间存储组件**，提供统一的 HTTP 接口进行读写操作。

## 1. 核心特性

- ✅ **统一访问接口**：多个网站/服务通过标准 HTTP API 访问同一个 Notion 数据库
- ✅ **自动翻页查询**：一次调用获取数据库所有记录，无需手动处理分页
- ✅ **批量更新**：支持一次请求更新多条记录的属性
- ✅ **结构查询**：获取数据库 schema，了解所有可用字段和类型
- ✅ **AWS 部署友好**：环境变量配置，容器化部署

## 2. 技术栈

- **语言**: Python 3.12+
- **Web 框架**: FastAPI
- **HTTP 客户端**: httpx
- **运行方式**: uvicorn（支持本地/AWS/容器化部署）

## 3. 工程结构

```
svs_notion/
├── main.py              # FastAPI 应用入口与所有 HTTP 接口
├── requirements.txt     # Python 依赖
├── start.sh            # 快速启动脚本（需配置环境变量）
├── .env.example        # 环境变量配置模板
├── .gitignore          # Git 忽略文件（防止提交密钥）
├── README.md           # 本文档
└── notion-1.0.0/
    └── SKILL.md        # Notion API 参考文档
```

## 4. 快速开始

### 4.1 安装依赖

```bash
cd svs_notion
pip install -r requirements.txt
```

### 4.2 配置环境变量

**重要**：Notion API 2025-09-03 版本中，`database_id` 和 `data_source_id` 是两个不同的 ID。

**如何获取 `data_source_id`？**

启动服务后，执行以下命令查询：

```bash
curl -X POST "http://localhost:8001/api/notion/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "", "filter": {"value": "data_source", "property": "object"}}'
```

在返回结果中找到你的数据库，其 `id` 字段就是 `data_source_id`。

**配置方式一：使用 start.sh（推荐）**

编辑 `start.sh`，填入你的真实值：

```bash
export NOTION_API_KEY="ntn_your_key_here"
export NOTION_DATABASE_ID="your_database_id"
export NOTION_DATA_SOURCE_ID="your_data_source_id"
export PORT=8001
```

然后启动：

```bash
chmod +x start.sh
./start.sh
```

**配置方式二：手动设置环境变量**

```bash
export NOTION_API_KEY='ntn_your_api_key_here'
export NOTION_DATABASE_ID='your_database_id_here'
export NOTION_DATA_SOURCE_ID='your_data_source_id_here'
export PORT=8001

cd svs_notion
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**配置方式三：使用 .env 文件（本地开发）**

```bash
cp .env.example .env
# 编辑 .env 填入真实值
# 然后使用支持 .env 的工具启动（如 python-dotenv）
```

### 4.3 验证服务

```bash
curl http://localhost:8001/health
# 返回: {"status":"ok"}
```

## 5. HTTP API 接口文档

### 基础接口

#### 5.1 健康检查

```http
GET /health
```

**响应**：

```json
{"status": "ok"}
```

#### 5.2 搜索页面/数据源

```http
POST /api/notion/search
Content-Type: application/json

{
  "query": "关键词",
  "filter": {"value": "data_source", "property": "object"}
}
```

### 数据库核心接口（适用于中间存储场景）

#### 5.3 获取数据库结构 ⭐

**适用场景**：了解数据库有哪些字段、字段类型、选项值等

```http
GET /api/notion/database/schema
```

**响应示例**：

```json
{
  "id": "your-data-source-id",
  "properties": {
    "Title": {
      "id": "title",
      "name": "Title",
      "type": "title"
    },
    "Status": {
      "id": "abc",
      "name": "Status",
      "type": "status",
      "status": {
        "options": [
          {"id": "...", "name": "未开始", "color": "default"},
          {"id": "...", "name": "进行中", "color": "blue"},
          {"id": "...", "name": "完成", "color": "green"}
        ]
      }
    }
  }
}
```

**curl 示例**：

```bash
curl "http://localhost:8001/api/notion/database/schema"
```

#### 5.4 获取数据库所有记录 ⭐

**适用场景**：一次性获取数据库全部数据，自动处理分页

```http
GET /api/notion/database/all?filter={...}&sorts={...}
```

**查询参数**：

- `filter`（可选）：JSON 字符串，过滤条件
- `sorts`（可选）：JSON 字符串，排序条件

**curl 示例（获取所有记录）**：

```bash
curl "http://localhost:8001/api/notion/database/all"
```

**curl 示例（带过滤条件）**：

```bash
# 获取 Status = "完成" 的记录
curl "http://localhost:8001/api/notion/database/all?filter=%7B%22property%22%3A%22Status%22%2C%22status%22%3A%7B%22equals%22%3A%22%E5%AE%8C%E6%88%90%22%7D%7D"
```

**响应格式**：

```json
{
  "results": [
    {
      "object": "page",
      "id": "page_id_1",
      "properties": {
        "Title": {...},
        "Status": {...}
      }
    }
  ],
  "total": 123
}
```

#### 5.5 查询数据库（分页）

**适用场景**：需要手动控制分页时使用

```http
POST /api/notion/database/query
Content-Type: application/json

{
  "filter": {
    "property": "Status",
    "status": {"equals": "进行中"}
  },
  "sorts": [
    {"property": "Created", "direction": "descending"}
  ],
  "page_size": 50,
  "start_cursor": "可选，用于翻页"
}
```

**curl 示例**：

```bash
curl -X POST "http://localhost:8001/api/notion/database/query" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "property": "Status",
      "status": {"equals": "进行中"}
    },
    "sorts": [
      {"property": "Created", "direction": "descending"}
    ],
    "page_size": 50
  }'
```

**响应格式**：

```json
{
  "results": [...],
  "next_cursor": "...",
  "has_more": true
}
```

#### 5.6 在数据库中创建记录

**适用场景**：网站 A 往 Notion 数据库插入新记录

```http
POST /api/notion/pages
Content-Type: application/json

{
  "properties": {
    "Title": {
      "title": [{"text": {"content": "新任务"}}]
    },
    "Status": {
      "status": {"name": "未开始"}
    }
  }
}
```

**curl 示例**：

```bash
curl -X POST "http://localhost:8001/api/notion/pages" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "Title": {"title": [{"text": {"content": "测试任务"}}]},
      "Status": {"status": {"name": "未开始"}}
    }
  }'
```

#### 5.7 更新单条记录

**适用场景**：网站 B 修改某条记录的状态

```http
PATCH /api/notion/pages/{page_id}
Content-Type: application/json

{
  "properties": {
    "Status": {
      "status": {"name": "完成"}
    }
  }
}
```

**curl 示例**：

```bash
curl -X PATCH "http://localhost:8001/api/notion/pages/your_page_id_here" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "Status": {"status": {"name": "完成"}}
    }
  }'
```

#### 5.8 批量更新多条记录 ⭐

**适用场景**：网站 C 一次性更新多条记录的状态

```http
POST /api/notion/pages/batch-update
Content-Type: application/json

{
  "updates": [
    {
      "page_id": "page_id_1",
      "properties": {
        "Status": {"status": {"name": "完成"}}
      }
    },
    {
      "page_id": "page_id_2",
      "properties": {
        "Status": {"status": {"name": "进行中"}}
      }
    }
  ]
}
```

**curl 示例**：

```bash
curl -X POST "http://localhost:8001/api/notion/pages/batch-update" \
  -H "Content-Type: application/json" \
  -d '{
    "updates": [
      {
        "page_id": "your_page_id_1",
        "properties": {"Status": {"status": {"name": "完成"}}}
      },
      {
        "page_id": "your_page_id_2",
        "properties": {"Status": {"status": {"name": "进行中"}}}
      }
    ]
  }'
```

**响应格式**：

```json
{
  "success": ["page_id_1", "page_id_2"],
  "failed": [],
  "total": 2,
  "success_count": 2,
  "failed_count": 0
}
```

### 辅助接口

#### 5.9 获取页面详情

```http
GET /api/notion/pages/{page_id}
```

**curl 示例**：

```bash
curl "http://localhost:8001/api/notion/pages/your_page_id"
```

#### 5.10 获取页面内容块

**适用场景**：获取 Notion 页面的完整内容（段落、标题、列表等）

```http
GET /api/notion/pages/{page_id}/blocks?page_size=100
```

**curl 示例**：

```bash
curl "http://localhost:8001/api/notion/pages/your_page_id/blocks"
```

**使用流程**：

1. 先用 `/api/notion/database/query` 根据 Title 查询，获取 `page_id`
2. 再用 `/api/notion/pages/{page_id}/blocks` 获取完整内容

**示例**：

```bash
# 第一步：根据 Title 查询
curl -X POST "http://localhost:8001/api/notion/database/query" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "property": "Title",
      "title": {"contains": "关键词"}
    }
  }'

# 从返回的 results[0].id 拿到 page_id

# 第二步：获取页面内容
curl "http://localhost:8001/api/notion/pages/{page_id}/blocks"
```

#### 5.11 追加页面内容块

```http
PATCH /api/notion/pages/{page_id}/blocks
Content-Type: application/json

{
  "children": [
    {
      "object": "block",
      "type": "paragraph",
      "paragraph": {
        "rich_text": [{"text": {"content": "追加内容"}}]
      }
    }
  ]
}
```

## 6. 典型使用场景

### 场景 1：多网站共享任务状态

**需求**：网站 A 创建任务，网站 B 查看任务，网站 C 更新任务状态。

```bash
# 网站 A：创建任务
curl -X POST "http://your-service/api/notion/pages" \
  -d '{"properties": {"Title": {...}, "Status": {"status": {"name": "未开始"}}}}'

# 网站 B：查看所有任务
curl "http://your-service/api/notion/database/all"

# 网站 C：批量更新任务状态
curl -X POST "http://your-service/api/notion/pages/batch-update" \
  -d '{"updates": [{"page_id": "...", "properties": {...}}]}'
```

### 场景 2：获取特定状态的记录

```bash
# 获取所有 Status = "完成" 的记录
curl -X POST "http://localhost:8001/api/notion/database/query" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "property": "Status",
      "status": {"equals": "完成"}
    }
  }'
```

### 场景 3：了解数据库结构

```bash
# 第一次接入时，先查看数据库有哪些字段
curl "http://localhost:8001/api/notion/database/schema"
```

## 7. 在 AWS 上部署

### 7.1 容器化部署（推荐）

创建 `Dockerfile`：

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY main.py .
COPY __init__.py .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

构建镜像：

```bash
cd svs_notion
docker build -t svs-notion:latest .
```

运行容器：

```bash
docker run -d \
  -p 8000:8000 \
  -e NOTION_API_KEY="ntn_..." \
  -e NOTION_DATABASE_ID="..." \
  -e NOTION_DATA_SOURCE_ID="..." \
  svs-notion:latest
```

### 7.2 AWS 部署选项

| 方案 | 适用场景 | 配置要点 |
|------|---------|---------|
| **ECS Fargate** | 生产环境，自动扩缩容 | 使用 Task Definition，环境变量从 Secrets Manager 注入 |
| **App Runner** | 最简单部署 | 直接从 GitHub/ECR 部署，自动 HTTPS |
| **EC2** | 需要完全控制 | 手动安装 Python 环境，使用 systemd 管理服务 |
| **Lambda + API Gateway** | 低成本，间歇性流量 | 使用 Mangum 适配器，冷启动约 1-2 秒 |

### 7.3 密钥管理

**推荐做法**：

1. 在 AWS Secrets Manager 中创建密钥：

```json
{
  "NOTION_API_KEY": "ntn_...",
  "NOTION_DATABASE_ID": "...",
  "NOTION_DATA_SOURCE_ID": "..."
}
```

2. ECS Task Definition 中引用：

```json
{
  "secrets": [
    {
      "name": "NOTION_API_KEY",
      "valueFrom": "arn:aws:secretsmanager:region:account:secret:notion-credentials:NOTION_API_KEY::"
    }
  ]
}
```

## 8. 开发与测试

### 8.1 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发模式（自动重载）
uvicorn main:app --reload --port 8001
```

### 8.2 API 文档

FastAPI 自动生成交互式 API 文档：

- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

### 8.3 测试 Notion 权限

确保你的 Notion Integration 已共享到目标数据库：

1. 打开 Notion 数据库页面
2. 右上角 `···` → "Connections" / "连接"
3. 添加你的 Integration

## 9. 常见问题

### Q1: 报错 "object_not_found"

**原因**：数据库未共享给 Integration，或 ID 配置错误。

**解决**：
1. 检查 Notion 数据库是否已"连接"到你的 Integration
2. 确认 `NOTION_DATA_SOURCE_ID` 是否正确（通过 `/api/notion/search` 查询）

### Q2: 如何找到 data_source_id？

```bash
curl -X POST "http://localhost:8001/api/notion/search" \
  -H "Content-Type: application/json" \
  -d '{"filter": {"value": "data_source", "property": "object"}}'
```

在返回的 `results` 中找到你的数据库，其 `id` 字段就是 `data_source_id`。

### Q3: 批量更新失败怎么办？

批量更新接口会返回详细的成功/失败列表：

```json
{
  "success": ["page_id_1"],
  "failed": [
    {
      "page_id": "page_id_2",
      "error": "具体错误信息"
    }
  ]
}
```

根据 `failed` 数组中的错误信息逐条排查。

### Q4: 如何限制访问权限？

目前服务未实现鉴权，建议：

1. **网络层隔离**：部署在 VPC 内网，只允许特定 IP 访问
2. **API Gateway**：在前面加一层 API Gateway，配置 API Key
3. **自定义中间件**：在 `main.py` 中添加 FastAPI 中间件验证 Header

### Q5: GitHub 推送被阻止（检测到密钥）

**解决方法**：

1. 确保 `start.sh` 和 `README.md` 中使用占位符（如 `ntn_your_key_here`）
2. 真实密钥放在 `start_local.sh` 或 `.env` 文件中（已加入 `.gitignore`）
3. 如果历史 commit 包含密钥，需要清理 Git 历史：

```bash
# 回退到初始提交
git reset --hard <initial_commit_id>

# 重新提交
git add .
git commit -m "feat: 实现 Notion 标准访问服务"
git push -f origin main
```

## 10. 下一步优化建议

- [ ] 添加 API Key 鉴权中间件
- [ ] 添加请求日志和监控（CloudWatch Logs）
- [ ] 实现缓存层（Redis），减少 Notion API 调用
- [ ] 添加 Webhook 接口，接收 Notion 数据变更通知
- [ ] 封装业务模型层（如 Task、Article 等）

---

**如需帮助或定制开发，请提 Issue 或联系维护者。**
