# AGENTS.md - 项目开发指南

## 项目概述

2345.desuwa.org - 跨性别资源搜索引擎

## 技术栈

- **前端**: PHP + HTML/CSS/JS
- **搜索后端**: Meilisearch (Docker)
- **爬虫**: Python + Scrapy + trafilatura
- **API**: Flask + GitHub OAuth

## 目录结构

```
2345.desuwa.org/
├── frontend/           # PHP 前端
│   ├── index.php      # 主搜索页面
│   ├── style.css      # 样式（含暗黑模式）
│   └── search.js      # 前端脚本（语言检测、主题切换）
├── transspider/       # Scrapy 爬虫
│   ├── config.py      # 配置（从 domains.json 加载）
│   └── spiders/trans_spider.py  # 爬虫逻辑
├── api/               # Flask API
│   ├── app.py
│   └── env.example
├── docs/              # 静态文档页面
├── domains.json       # 域名配置
├── add_direct_links.py # 添加直接链接脚本
└── docker-compose.yml # Meilisearch
```

## 关键配置

### domains.json 结构

- `domains`: 需要爬取的网站列表（只爬取这些域名）
- `direct_urls`: 直接添加到索引的 URL（不爬取）

### 部署命令

```bash
# 1. 启动 Meilisearch
docker-compose up -d

# 2. 爬取网站
cd transspider && scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000

# 3. 添加直接链接
cd .. && python add_direct_links.py
```

### Cron 任务（每周日3点）

```bash
cd /www/wwwroot/2345.desuwa.org/transspider && scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000 >> /var/log/trans_spider.log 2>&1
cd /www/wwwroot/2345.desuwa.org && python3 add_direct_links.py >> /var/log/trans_spider.log 2>&1
```

## 常见任务

### 添加新网站到爬取列表

在 `domains.json` 的 `domains` 数组中添加：
```json
{"domain": "example.com", "name": "示例", "url": "https://example.com/", "tags": ["知识库"]}
```

### 添加直接链接

在 `domains.json` 的 `direct_urls` 数组中添加：
```json
{"url": "https://example.com/page", "title": "页面标题", "tags": ["标签"]}
```

然后运行 `python add_direct_links.py`

### 部署到服务器

1. 使用 scp 上传文件到服务器
2. SSH 连接服务器检查
3. 测试 curl 验证

### 注意事项

1. **不要提交敏感文件**: .gitignore 已排除 api/.env, api/db.json, backup_meilisearch.json
2. **CDN 缓存**: 上传后添加版本参数如 `?v=5`
3. **暗黑模式**: CSS 中 light mode 在前，dark mode 覆盖在后
4. **静态HTML**: docs 目录下的 HTML 不执行 PHP，链接要用 `/` 而不是 PHP 代码

## API 配置

环境变量（参考 api/env.example）:
- GITHUB_CLIENT_ID
- GITHUB_CLIENT_SECRET
- FLASK_SECRET
- ADMIN_USERS
