# 2345.desuwa.org API 文档

## 概述

2345.desuwa.org 提供免费的跨性别资源搜索 API，支持多语言筛选、简繁体中文分离等功能。

## 认证

所有 API 请求需要在 Header 中包含 API Key：

```
Authorization: Bearer YOUR_API_KEY
```

获取 API Key：访问 [API 控制台](https://2345.desuwa.org/api/console.html)

## 端点

### 搜索

```
GET /api/search
```

#### 参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| q | string | 是 | - | 搜索关键词 |
| limit | int | 否 | 10 | 返回结果数量 (1-20) |
| offset | int | 否 | 0 | 起始位置（用于分页） |
| lang | string | 否 | all | 语言筛选：zh-cn, zh-hant, zh, en, ja, es, nl, all |
| script | string | 否 | all | 中文简繁体：simplified, traditional, all |
| domain | string | 否 | - | 站点筛选（如 mtf.wiki） |
| tags | string | 否 | - | 标签筛选，逗号分隔 |

#### 响应示例

```json
{
  "results": [
    {
      "url": "https://ftm.wiki/zh-cn/hrt/overview/",
      "title": "HRT 概论 - FtM.wiki",
      "content": "...",
      "domain": "ftm.wiki",
      "tags": ["FtM", "知识库"],
      "_language": "zh",
      "_script": "simplified"
    }
  ],
  "total": 273,
  "query": "HRT",
  "credits_used": 1,
  "credits_remaining": 1999,
  "limit": 10,
  "offset": 0
}
```

### 获取 API Key 信息

```
GET /api/keys
```

#### 响应示例

```json
{
  "api_key": "xxxxx",
  "credits_used": 10,
  "credits_remaining": 1990,
  "created_at": "2026-03-17T10:00:00"
}
```

### 重新生成 API Key

```
POST /api/keys/regenerate
```

### 获取用户信息

```
GET /api/me
```

### 健康检查

```
GET /api/health
```

返回：`{"status": "ok"}`

## 速率限制

- 每分钟：10 次
- 每月：2000 次

超出限制返回 `429` 状态码。

## 错误码

| 错误码 | 说明 |
|--------|------|
| 401 | 无效的 API Key |
| 403 | 账号已被封禁 |
| 429 | 超出速率限制 |
| 500 | 服务器错误 |

## 使用示例

### cURL

```bash
# 基本搜索
curl "https://2345.desuwa.org/api/search?q=HRT" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 筛选语言和简繁体
curl "https://2345.desuwa.org/api/search?q=激素&lang=zh&script=traditional&limit=5" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 分页
curl "https://2345.desuwa.org/api/search?q=HRT&limit=10&offset=10" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Python

```python
import requests

API_KEY = "YOUR_API_KEY"
headers = {"Authorization": f"Bearer {API_KEY}"}

response = requests.get(
    "https://2345.desuwa.org/api/search",
    params={
        "q": "HRT",
        "lang": "zh",
        "limit": 10
    },
    headers=headers
)

data = response.json()
for result in data["results"]:
    print(result["title"], result["url"])
```

## 条款

- 本 API 仅供个人非商业使用
- 请参阅 [服务条款](../terms.html) 和 [免责声明](../disclaimer.html)
