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
│   ├── search.js       # 前端脚本（语言检测、主题切换、PWA）
│   ├── language_rules.php  # 语言检测规则（可自定义）
│   ├── manifest.json   # PWA 配置
│   ├── sw.js           # Service Worker
│   └── icon.svg/png    # 应用图标
├── transspider/       # Scrapy 爬虫
│   ├── config.py       # 配置（从 domains.json 加载）
│   ├── pipelines.py    # 管道（MD5 hash 生成文档 ID）
│   └── spiders/trans_spider.py  # 爬虫逻辑
├── api/               # Flask API
│   ├── app.py
│   ├── language_rules.py  # Python 语言检测规则
│   └── env.example
├── docs/              # 静态文档页面
├── domains.json       # 域名配置
├── add_direct_links.py # 添加直接链接脚本
└── docker-compose.yml # Meilisearch
```

## 语言检测规则

语言检测规则已与代码解耦，自部署者可轻松自定义修改：

- **PHP 前端**: `frontend/language_rules.php`
- **Python API**: `api/language_rules.py`

### 支持的语言

通过 URL 路径检测：`zh-cn`, `zh-hant`, `en`, `ja`, `es`, `nl`, `ko`, `fr`, `de`, `pl`, `el`, `hu`, `ru` 等

### 无语言路径的域名默认语言

在 `DOMAIN_DEFAULT_LANG` 中配置，例如：
```php
$DOMAIN_DEFAULT_LANG = [
    'mtf.wiki' => 'zh-cn',
    'genderdysphoria.fyi' => 'en',  // 英文为主
    'knowsex.net' => 'zh-cn',       // 中文为主
    // ...
];
```

### URL 模式规则

在 `URL_PATTERN_RULES` 中配置，用于更细粒度的匹配，例如：
```php
$URL_PATTERN_RULES = [
    ['pattern' => '/tweets?/', 'lang' => 'en', 'weight' => 10],  // Twitter 内容默认英文
    ['pattern' => '/category\/.*[\x{4e00}-\x{9fff}]/u', 'lang' => 'zh-cn', 'weight' => 8],  // URL含中文
];
```

## PWA 应用支持

- `manifest.json`: PWA 配置（名称、图标、主题色）
- `sw.js`: Service Worker（缓存策略，离线可用）
- 安装按钮在搜索技巧下拉框中（仅 JS 可用时显示）

## 关键配置

### domains.json 结构

- `domains`: 需要爬取的网站列表（只爬取这些域名）
- `direct_urls`: 直接添加到索引的 URL（不爬取），用于：
  - Steam 游戏页面（无法爬取）
  - 社交媒体帖子（Twitter、Reddit 等）
  - 其他无法通过爬虫获取的页面

### 部署命令

```bash
# 1. 启动 Meilisearch
docker-compose up -d

# 2. 爬取网站
cd transspider && scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000

# 3. 添加直接链接（Steam游戏、社交媒体等）
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

### 重要：服务器不是 Git 部署

仓库是后续才开源的，服务器使用 `scp` 上传文件而非 `git clone`：
```bash
# 上传安全修复后的文件
scp docker-compose.yml myvps:/www/wwwroot/2345.desuwa.org/
scp frontend/index.php myvps:/www/wwwroot/2345.desuwa.org/frontend/
scp api/app.py myvps:/www/wwwroot/2345.desuwa.org/api/
scp transspider/config.py myvps:/www/wwwroot/2345.desuwa.org/transspider/
```

### 安全加固后的部署流程

1. SSH 登录服务器：`ssh myvps`
2. 备份现有文件
3. 上传新文件
4. 重启 Meilisearch（需要 Master Key）
5. 配置环境变量（API Key）
6. 重启 Flask API
7. 更新 Nginx 配置（如需要传递环境变量给 PHP）
8. 验证

### 环境变量配置

**Meilisearch Master Key**（用于生成其他 Key）：
```bash
MEILI_MASTER_KEY=your_master_key_here
```

**分层 API Key**：
- **Search Key**：前端和 API 使用（只有 search 权限）
- **Admin Key**：爬虫使用（有 documents.add 权限）

创建命令：
```bash
# Search Key
curl -X POST "http://127.0.0.1:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description": "Search-only key", "actions": ["search"], "indexes": ["trans_resources"], "expiresAt": null}'

# Admin Key（爬虫用）
curl -X POST "http://127.0.0.1:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description": "Admin key for crawler", "actions": ["documents.add", "documents.delete", "indexes.*"], "indexes": ["trans_resources"], "expiresAt": null}'
```

### PHP 环境变量传递（Nginx + PHP-FPM）

PHP 代码中 `getenv()` 读取的是 PHP-FPM 进程的环境变量，不是 Nginx 的。需要在 Nginx 配置中使用 `fastcgi_param` 传递：
```nginx
location ~ \.php$ {
    include fastcgi_params;
    fastcgi_pass unix:/tmp/php-cgi-84.sock;
    fastcgi_param MEILISEARCH_API_KEY your_search_key;
}
```

### Flask API 重启

```bash
pkill -f 'python.*api/app.py'
cd /www/wwwroot/2345.desuwa.org/api
MEILISEARCH_API_KEY=your_search_key nohup python3 app.py > /var/log/api.log 2>&1 &
```

### Cron 任务（安全加固后）

```bash
# Meilisearch Master Key 和 Admin Key 需要在环境中可用
MEILI_MASTER_KEY=xxx MEILISEARCH_API_KEY=yyy cd /www/wwwroot/2345.desuwa.org/transspider && scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000 >> /var/log/trans_spider.log 2>&1
```

### 验证命令

```bash
# 验证 Meilisearch 需要认证（应返回 401）
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7700/indexes

# 验证前端搜索正常工作
curl -s "https://2345.desuwa.org/?q=HRT" | grep "找到约"

# 验证 API 需要用户认证
curl -s "http://127.0.0.1:5000/api/search?q=test" | grep "缺少 API Key"
```

## API 配置

环境变量（参考 api/env.example）:
- GITHUB_CLIENT_ID
- GITHUB_CLIENT_SECRET
- FLASK_SECRET（必填，无默认值）
- ADMIN_USERS
- MEILISEARCH_HOST
- MEILISEARCH_PORT
- MEILISEARCH_API_KEY（Search Key）
- MEILI_MASTER_KEY（Master Key，用于生成其他 Key）
- SITE_URL
