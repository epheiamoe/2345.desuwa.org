# 跨性别资源搜索引擎 (2345.desuwa.org)

> 只收录 2345.lgbt 导航站资源的专属搜索引擎

## 项目简介

本项目是一个专注于跨性别资源的搜索引擎，仅收录 [2345.lgbt](https://2345.lgbt) 导航站收录的网站内容，不爬取外部网站。

### 技术栈

- **爬虫**: Python + Scrapy
- **搜索引擎**: Meilisearch (Docker)
- **前端**: 纯 PHP + Bootstrap 风格
- **部署**: 宝塔面板 + Nginx

## 项目结构

```
2345.desuwa.org/
├── 2345-lgbt-repo/          # 2345.LGBT 仓库（克隆）
├── domains.txt              # 完整域名列表（105个）
├── domains_test.txt         # 测试用域名列表（3个）
├── docker-compose.yml       # Meilisearch Docker 配置
├── extract_domains.py       # 域名提取脚本
├── start.sh                 # 本地启动脚本
├── transspider/             # Scrapy 爬虫项目
│   ├── config.py            # 配置文件
│   ├── items.py             # 数据模型
│   ├── pipelines.py         # 数据处理管道
│   ├── settings.py          # 爬虫设置
│   ├── middlewares.py       # 中间件
│   └── spiders/
│       └── trans_spider.py  # 爬虫核心
└── frontend/
    └── index.php            # 搜索页面
```

## 本地开发

### 前置要求

- Python 3.8+
- Docker Desktop
- PHP 7.4+ (自带 PHP 可用)
- Git

### 安装依赖

```bash
# 安装 Python 依赖
pip install scrapy trafilatura meilisearch

# 克隆 2345.LGBT 仓库（已在项目中）
```

### 启动服务

#### 方式一：使用启动脚本（推荐）

```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh
```

#### 方式二：手动启动

```bash
# 1. 启动 Meilisearch
docker-compose up -d

# 2. 运行爬虫（可选，首次测试可跳过）
cd transspider
scrapy crawl trans

# 3. 启动 PHP 服务器
cd frontend
php -S localhost:8080
```

### 访问测试

- 搜索页面: http://localhost:8080
- Meilisearch: http://localhost:7700

## 域名列表

- **完整列表**: `domains.txt` (105 个域名)
- **测试列表**: `domains_test.txt` (3 个核心域名)

### 部署前清理

在部署到服务器前，需要从 `domains.txt` 中移除以下大型网站：

- 社交媒体: youtube.com, twitter.com, reddit.com, dcard.tw
- 百科全书: zh.wikipedia.org, en.wikipedia.org, ja.wikipedia.org
- 视频/电商: bilibili.com, shopee.tw, amazon.co.jp
- 其他大型网站

可以使用 `extract_domains.py` 重新生成域名列表，然后手动编辑。

## 爬虫配置

### WARP 代理（可选）

如遇到 IP 被封，可在 `transspider/config.py` 中开启 WARP 代理：

```python
USE_WARP_PROXY = True
WARP_SOCKS5_PROXY = "socks5://127.0.0.1:1080"
```

### 爬虫设置

在 `transspider/settings.py` 中可调整：

- `DOWNLOAD_DELAY`: 请求间隔（秒）
- `CONCURRENT_REQUESTS_PER_DOMAIN`: 并发数
- `ROBOTSTXT_OBEY`: 是否遵守 robots.txt

## 部署（用户验收后）

### 服务器要求

- 安装宝塔面板
- 安装 Docker
- 域名已解析到服务器

### 部署步骤

1. **上传代码**

```bash
rsync -avz --exclude '.git' ./ user@your-server:/www/wwwroot/2345.desuwa.org/
```

2. **添加站点**

在宝塔面板中添加站点：
- 域名: 2345.desuwa.org
- 根目录: /www/wwwroot/2345.desuwa.org/frontend

3. **启动 Meilisearch**

```bash
cd /www/wwwroot/2345.desuwa.org
docker-compose up -d
```

4. **配置定时任务**

添加 cron 任务，每周更新一次索引：

```bash
# 每周日凌晨 3 点运行爬虫
0 3 * * 0 cd /www/wwwroot/2345.desuwa.org/transspider && scrapy crawl trans
```

5. **配置 Nginx 反向代理**

在宝塔站点设置中添加 Meilisearch 反向代理（可选）。

## AI 概览功能（TODO）

当前版本已预留接口，后续将接入 Ollama 实现 AI 智能摘要。

```php
<!-- TODO: LLM 概览 -->
<div class="ai-overview">
    <h3>AI 智能摘要（开发中）</h3>
    <p>此功能正在开发中...</p>
</div>
```

## 安全配置

- User-Agent 随机化
- 遵守 robots.txt
- 请求限速
- 首页免责声明
- 搜索速率限制（每 IP 每分钟 20 次）

## 许可证

本项目采用 [LGPLv3](LICENSE) 开源许可证。

- 本项目代码采用 LGPLv3 许可证，允许自由使用、修改和分发
- 数据来源：2345.lgbt 导航站（同样采用 LGPLv3）

## 注意事项

1. 本搜索引擎仅收录 2345.lgbt 公开资源
2. 医疗问题请咨询专业医生
3. 遵守目标网站的 robots.txt 规则
