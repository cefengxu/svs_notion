import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Body, FastAPI, HTTPException


NOTION_BASE_URL = "https://api.notion.com/v1"
# 与 skill 中保持一致
NOTION_VERSION = "2025-09-03"

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
# 在 2025-09-03 版本中，查询使用 data_source_id，这里允许单独配置；
# 若未配置，则默认与 NOTION_DATABASE_ID 相同，方便直接使用你给出的 ID。
NOTION_DATA_SOURCE_ID = os.getenv("NOTION_DATA_SOURCE_ID", NOTION_DATABASE_ID)


if not NOTION_API_KEY:
    raise RuntimeError("环境变量 NOTION_API_KEY 未设置（Notion 集成密钥）")

if not NOTION_DATABASE_ID:
    raise RuntimeError("环境变量 NOTION_DATABASE_ID 未设置（Notion 数据库 ID）")


app = FastAPI(
    title="SVS Notion Service",
    description="基于 FastAPI 封装的 Notion 标准访问服务，参考 svs_notion/notion-1.0.0 skill。",
    version="1.0.0",
)


async def _notion_request(
    method: str,
    path: str,
    json: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """对 Notion 发起 HTTP 请求的通用封装。"""
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(
            method=method,
            url=f"{NOTION_BASE_URL}{path}",
            headers=headers,
            json=json,
            params=params,
        )

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        # 直接透传 Notion 的错误结构，方便排查
        raise HTTPException(status_code=resp.status_code, detail=data)

    return data


@app.get("/health")
async def health() -> Dict[str, str]:
    """健康检查接口。"""
    return {"status": "ok"}


@app.post("/api/notion/search")
async def search(body: Dict[str, Any] = Body(...)) -> Any:
    """
    包装 Notion `/v1/search`。

    请求体将被原样透传给 Notion，默认用来按关键词搜索页面 / 数据源。
    """
    return await _notion_request("POST", "/search", json=body)


@app.get("/api/notion/pages/{page_id}")
async def get_page(page_id: str) -> Any:
    """获取页面元信息（对应 Notion `GET /v1/pages/{page_id}`）。"""
    return await _notion_request("GET", f"/pages/{page_id}")


@app.get("/api/notion/pages/{page_id}/blocks")
async def get_page_blocks(
    page_id: str,
    start_cursor: Optional[str] = None,
    page_size: int = 100,
) -> Any:
    """
    获取页面内容块（blocks），对应 `GET /v1/blocks/{page_id}/children`。
    """
    params: Dict[str, Any] = {"page_size": page_size}
    if start_cursor:
        params["start_cursor"] = start_cursor

    return await _notion_request("GET", f"/blocks/{page_id}/children", params=params)


@app.post("/api/notion/pages")
async def create_page(
    properties: Dict[str, Any] = Body(..., description="Notion 页面属性对象（properties）"),
    children: Optional[List[Dict[str, Any]]] = Body(
        default=None,
        description="可选，页面初始 blocks 内容 children",
    ),
) -> Any:
    """
    在预配置的数据库中创建页面。

    - parent.database_id 使用环境变量 `NOTION_DATABASE_ID`
    - properties/children 结构与官方 Notion API 完全一致
    """
    payload: Dict[str, Any] = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties,
    }
    if children:
        payload["children"] = children

    return await _notion_request("POST", "/pages", json=payload)


@app.post("/api/notion/database/query")
async def query_database(body: Dict[str, Any] = Body(default_factory=dict)) -> Any:
    """
    查询数据库（data source）。

    对应 `POST /v1/data_sources/{data_source_id}/query`。

    - 默认使用环境变量 `NOTION_DATA_SOURCE_ID`（若未设置，则等于 `NOTION_DATABASE_ID`）
    - body（filter、sorts、page_size 等）原样透传给 Notion
    """
    data_source_id = NOTION_DATA_SOURCE_ID or NOTION_DATABASE_ID
    if not data_source_id:
        raise HTTPException(
            status_code=500,
            detail="NOTION_DATA_SOURCE_ID 与 NOTION_DATABASE_ID 均未配置",
        )

    return await _notion_request(
        "POST", f"/data_sources/{data_source_id}/query", json=body
    )


@app.patch("/api/notion/pages/{page_id}")
async def update_page_properties(
    page_id: str,
    properties: Dict[str, Any] = Body(..., description="要更新的页面 properties"),
) -> Any:
    """
    更新页面属性，对应 `PATCH /v1/pages/{page_id}`。
    """
    payload = {"properties": properties}
    return await _notion_request("PATCH", f"/pages/{page_id}", json=payload)


@app.patch("/api/notion/pages/{page_id}/blocks")
async def append_blocks(
    page_id: str,
    children: List[Dict[str, Any]] = Body(..., description="要追加的 blocks 数组"),
) -> Any:
    """
    往页面末尾追加 blocks，对应 `PATCH /v1/blocks/{page_id}/children`。
    """
    payload = {"children": children}
    return await _notion_request(
        "PATCH", f"/blocks/{page_id}/children", json=payload
    )


@app.get("/api/notion/database/schema")
async def get_database_schema() -> Any:
    """
    获取数据库结构（schema）信息。
    
    返回数据库的所有属性定义（properties），包括字段名、类型、选项等。
    适用于了解数据库有哪些字段可以读写。
    """
    data_source_id = NOTION_DATA_SOURCE_ID or NOTION_DATABASE_ID
    if not data_source_id:
        raise HTTPException(
            status_code=500,
            detail="NOTION_DATA_SOURCE_ID 与 NOTION_DATABASE_ID 均未配置",
        )
    
    return await _notion_request("GET", f"/data_sources/{data_source_id}")


@app.get("/api/notion/database/all")
async def get_all_database_records(
    filter: Optional[str] = None,
    sorts: Optional[str] = None,
) -> Dict[str, Any]:
    """
    自动翻页，获取数据库所有记录。
    
    - filter: 可选，JSON 字符串格式的过滤条件
    - sorts: 可选，JSON 字符串格式的排序条件
    
    返回格式：
    {
        "results": [...],  // 所有记录
        "total": 123       // 总记录数
    }
    """
    import json
    
    data_source_id = NOTION_DATA_SOURCE_ID or NOTION_DATABASE_ID
    if not data_source_id:
        raise HTTPException(
            status_code=500,
            detail="NOTION_DATA_SOURCE_ID 与 NOTION_DATABASE_ID 均未配置",
        )
    
    all_results: List[Dict[str, Any]] = []
    has_more = True
    start_cursor: Optional[str] = None
    
    # 构建查询体
    query_body: Dict[str, Any] = {}
    if filter:
        try:
            query_body["filter"] = json.loads(filter)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="filter 参数不是有效的 JSON")
    
    if sorts:
        try:
            query_body["sorts"] = json.loads(sorts)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="sorts 参数不是有效的 JSON")
    
    # 自动翻页
    while has_more:
        if start_cursor:
            query_body["start_cursor"] = start_cursor
        
        response = await _notion_request(
            "POST", f"/data_sources/{data_source_id}/query", json=query_body
        )
        
        all_results.extend(response.get("results", []))
        has_more = response.get("has_more", False)
        start_cursor = response.get("next_cursor")
    
    return {
        "results": all_results,
        "total": len(all_results),
    }


@app.post("/api/notion/pages/batch-update")
async def batch_update_pages(
    updates: List[Dict[str, Any]] = Body(
        ...,
        description="批量更新列表，每项包含 page_id 和 properties",
        example=[
            {
                "page_id": "xxx-yyy-zzz",
                "properties": {
                    "StatusWeb": {"status": {"name": "完成"}}
                }
            }
        ],
    )
) -> Dict[str, Any]:
    """
    批量更新多个页面的属性。
    
    请求体格式：
    [
        {
            "page_id": "页面ID",
            "properties": {
                "字段名": {...}
            }
        },
        ...
    ]
    
    返回格式：
    {
        "success": [...],  // 成功更新的页面 ID 列表
        "failed": [...]    // 失败的页面 ID 及错误信息
    }
    """
    success: List[str] = []
    failed: List[Dict[str, Any]] = []
    
    for item in updates:
        page_id = item.get("page_id")
        properties = item.get("properties")
        
        if not page_id or not properties:
            failed.append({
                "page_id": page_id or "unknown",
                "error": "缺少 page_id 或 properties"
            })
            continue
        
        try:
            await _notion_request(
                "PATCH",
                f"/pages/{page_id}",
                json={"properties": properties}
            )
            success.append(page_id)
        except HTTPException as e:
            failed.append({
                "page_id": page_id,
                "error": str(e.detail)
            })
        except Exception as e:
            failed.append({
                "page_id": page_id,
                "error": str(e)
            })
    
    return {
        "success": success,
        "failed": failed,
        "total": len(updates),
        "success_count": len(success),
        "failed_count": len(failed),
    }


if __name__ == "__main__":
    # 方便本地调试：python -m svs_notion.main
    import uvicorn

    uvicorn.run(
        "svs_notion.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
