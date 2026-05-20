# AGENTS.md - AI 部署与开发指南

## 项目概述

2345.desuwa.org - 跨性别资源搜索引擎

**当前版本**: v2.0 (Easy Deploy)

## 技术栈

- **前端**: PHP 8.1+ + HTML/CSS/JS
- **搜索后端**: Meilisearch (Docker)
- **爬虫**: Python + Scrapy + trafilatura
- **API**: Flask + GitHub OAuth
- **数据库**: SQLite (WAL 模式)
- **部署**: Bash 脚本 + Docker Compose

## AI 部署 Skill

本项目提供 **Claude Skill** 用于 AI 辅助部署：

**文件**: `.claude/skills/deploy.md`

**功能**:
- 自动检测环境（PHP, Docker, Python, Nginx）
- 选择部署模式（minimal/full/docker）
- 生成配置文件
- 启动服务
- 运行爬虫导入数据
- 验证部署结果

**使用方式**:
```bash
# AI 会自动读取 skill 并执行部署
# 用户只需说："帮我部署这个搜索引擎"
```

详见: [.claude/skills/deploy.md](.claude/skills/deploy.md)

## 目录结构

```
2345.desuwa.org/
├── frontend/              # PHP 前端
│   ├── index.php         # 入口（请求处理）
│   ├── template.php      # 模板渲染
│   ├── functions.php     # 安全输出辅助函数
│   ├── search.php        # 搜索逻辑
│   ├── config.php        # 配置加载器（读取 .env + config.json）
│   ├── manifest.php      # 动态 PWA manifest
│   ├── language_rules.php # 语言检测规则
│   ├── style.css         # 样式（含 CSS 变量和暗黑模式）
│   ├── search.js         # 前端脚本
│   ├── manifest.json     # PWA 配置（静态备份）
│   └── sw.js             # Service Worker
├── transspider/           # Scrapy 爬虫
│   ├── spiders/           # 爬虫代码
│   │   └── trans_spider.py
│   ├── pipelines.py      # Meilisearch 推送
│   │                     # - SHA-256 ID（替代 MD5）
│   │                     # - License 版权信息提取
│   │                     # - 指数退避重试
│   ├── config.py         # 爬虫配置（从 config.json 加载）
│   ├── items.py          # Item 定义
│   └── utils.py          # URL 规范化工具
├── api/                   # Flask API
│   ├── app.py            # 主程序
│   ├── config.py         # 统一配置管理（.env + config.json）
│   ├── database.py       # SQLite 数据库层（WAL 模式）
│   ├── rate_limiter.py   # 滑动窗口速率限制器
│   ├── validators.py     # 输入验证器
│   ├── auth.py           # 认证逻辑
│   ├── language_rules.py # Python 语言检测规则
│   ├── console.html      # API 控制台
│   ├── wsgi.py           # Gunicorn 入口
│   ├── Dockerfile        # API 容器化
│   ├── requirements.txt  # Python 依赖
│   └── env.example       # 环境变量模板
├── scripts/               # 部署脚本
│   ├── install.sh        # 一键部署向导（交互式/自动模式）
│   ├── rebrand.sh        # 品牌替换（交互式/自动模式）
│   ├── verify.sh         # 部署验证
│   ├── deploy.sh         # 传统部署脚本
│   ├── health_check.sh   # 健康检查
│   └── migrate_db.py     # 数据库迁移工具
├── docs/                  # 文档
│   ├── deploy/           # 部署文档
│   │   ├── QUICKSTART.md   # 5分钟快速开始
│   │   ├── MINIMAL.md      # 最小模式详解
│   │   ├── FULL.md         # 完整模式详解
│   │   ├── DOCKER.md       # Docker 模式
│   │   ├── REBRAND.md      # 品牌替换指南
│   │   └── TROUBLESHOOTING.md # 故障排除
│   ├── API.md            # API 文档
│   └── migration-v1.1.md # 迁移指南
├── config/                # 配置模板
│   └── examples/
│       ├── nginx.minimal.conf   # Nginx 最小配置
│       ├── nginx.full.conf      # Nginx 完整配置
│       ├── systemd.api.service  # Systemd 服务
│       └── crontab.crawler      # 定时任务示例
├── .claude/               # AI 配置
│   └── skills/
│       └── deploy.md      # AI 部署 Skill
├── .deploy/               # 设计文档
│   ├── design.md          # 架构设计
│   └── checklist.md       # 实施清单
├── config.json           # 共享配置（站点、标签、语言）
├── config.example.json   # 配置模板
├── .env.example          # 环境变量模板
├── .env.minimal.example  # 最小模式模板
├── .env.full.example     # 完整模式模板
├── domains.json          # 域名和标签列表
├── domains_test.txt      # 测试用域名
├── docker-compose.yml    # Meilisearch Docker
├── docker-compose.full.yml # 完整 Docker Compose
├── pyproject.toml        # Python 项目配置
├── CHANGELOG.md          # 变更日志
├── README.md             # 用户文档
└── AGENTS.md             # 本文档（AI 指南）
```

## 部署模式

### 1. 最小模式（Minimal）

**组件**: PHP + Meilisearch
**时间**: ~5 分钟
**功能**: 搜索（无需 GitHub OAuth）

```bash
./scripts/install.sh --mode minimal --auto \
  --domain search.example.com \
  --title "My Search"
```

### 2. 完整模式（Full）

**组件**: PHP + Meilisearch + Flask API + GitHub OAuth
**时间**: ~15 分钟
**功能**: 搜索 + API + OAuth

```bash
./scripts/install.sh --mode full --auto \
  --domain search.example.com \
  --title "My Search" \
  --github-client-id YOUR_ID \
  --github-secret YOUR_SECRET
```

### 3. Docker 模式

**组件**: 全部容器化
**时间**: ~10 分钟

```bash
./scripts/install.sh --mode docker --auto \
  --domain search.example.com
```

## 配置文件

### .env（环境变量）

位置：项目根目录

```bash
# === 部署模式 ===
DEPLOY_MODE=minimal           # minimal | full | docker
ENABLE_API=false              # 是否启用 Flask API
ENABLE_OAUTH=false            # 是否启用 GitHub OAuth
ENABLE_CRAWLER=true           # 是否启用爬虫

# === Meilisearch ===
MEILISEARCH_HOST=localhost
MEILISEARCH_PORT=7700
MEILISEARCH_API_KEY=          # Search Key
MEILI_MASTER_KEY=             # Master Key

# === Flask（完整模式） ===
FLASK_SECRET=                 # >=32字符随机字符串

# === GitHub OAuth（完整模式） ===
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
ADMIN_USERS=                  # 管理员 GitHub 用户名

# === 站点配置 ===
SITE_URL=https://your-domain.com
SITE_NAME=YourSiteName
SITE_TITLE=Your Site Title
```

### config.json（共享配置）

位置：项目根目录

```json
{
  "site": {
    "name": "{{SITE_NAME}}",
    "title": "{{SITE_TITLE}}",
    "url": "{{SITE_URL}}"
  },
  "deploy": {
    "mode": "minimal",
    "features": {
      "api": false,
      "oauth": false,
      "crawler": true
    }
  },
  "search": {
    "index_name": "trans_resources",
    "default_limit": 10,
    "max_limit": 100
  },
  "tags": {
    "available": ["MtF", "FtM", "知识库", "HRT"]
  },
  "languages": {
    "supported": ["zh-cn", "zh-hant", "en", "ja"]
  }
}
```

## 部署流程

### 自动部署（推荐）

```bash
# 1. 克隆代码
git clone https://github.com/epheiamoe/2345.desuwa.org.git
cd 2345.desuwa.org

# 2. 运行部署向导
./scripts/install.sh

# 3. 验证部署
./scripts/verify.sh
```

### 手动部署（传统方式）

```bash
# 1. 启动 Meilisearch
docker-compose up -d

# 2. 配置环境变量
cp .env.example .env
nano .env

# 3. 配置站点信息
cp config.example.json config.json
nano config.json

# 4. 安装 API 依赖
cd api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. 启动 API
python app.py

# 6. 运行爬虫
cd ../transspider
source ../api/venv/bin/activate
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000

# 7. 添加直接链接
cd ..
python add_direct_links.py
```

## 品牌替换

```bash
# 交互式
./scripts/rebrand.sh

# 自动模式
./scripts/rebrand.sh \
  --name "MySearch" \
  --domain "search.example.com" \
  --title "My Trans Search" \
  --repo "https://github.com/myname/search"
```

替换范围：
- config.json 站点信息
- .env 域名配置
- frontend/ 默认回退值
- docs/ 品牌引用

## 关键变更（v2.0）

### 新增
- 一键部署脚本 `install.sh`
- 品牌替换脚本 `rebrand.sh`
- 部署验证脚本 `verify.sh`
- AI 部署 Skill `.claude/skills/deploy.md`
- License 版权信息提取
- 三种部署模式（minimal/full/docker）
- 动态 PWA manifest

### 修改
- 配置外置（.env + config.json）
- SQLite 替代 JSON 文件数据库
- SHA-256 替代 MD5 文档 ID
- CSS 变量系统

### 删除
- 硬编码品牌信息
- 内存速率限制
- 手动部署步骤（自动化）

## API Key 管理

### Meilisearch Keys

**Master Key**: 用于生成其他 Key，仅在部署时使用
**Search Key**: 前端和 API 使用，只有 search 权限
**Admin Key**: 爬虫使用，有 documents.add 权限

创建命令：
```bash
# Search Key
curl -X POST "http://localhost:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -d '{"actions": ["search"], "indexes": ["trans_resources"]}'

# Admin Key
curl -X POST "http://localhost:7700/keys" \
  -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  -d '{"actions": ["documents.add", "documents.delete", "indexes.*"], "indexes": ["trans_resources"]}'
```

### Flask API Keys

存储在 `api/db.sqlite`（SQLite 数据库）

迁移命令：
```bash
python scripts/migrate_db.py --source db.json --target db.sqlite
```

## 验证命令

```bash
# 验证部署
./scripts/verify.sh

# 手动验证
# Meilisearch 健康
curl http://localhost:7700/health

# API 健康
curl http://localhost:5000/api/health

# 搜索功能
curl "http://localhost/?q=HRT"

# 索引统计
curl -H "Authorization: Bearer $MEILI_MASTER_KEY" \
  http://localhost:7700/indexes/trans_resources/stats
```

## 安全要点

1. **不要提交 `.env`** - 包含密钥
2. **Master Key 保护** - 仅在服务器环境使用
3. **GitHub OAuth Secret** - 保持机密
4. **Session Cookie** - 生产环境启用 Secure/HttpOnly
5. **输入验证** - 所有 API 参数经过校验
6. **XSS 防护** - 输出使用 `htmlspecialchars()`

## 故障排除

详见 [docs/deploy/TROUBLESHOOTING.md](docs/deploy/TROUBLESHOOTING.md)

常见问题：
- Meilisearch 启动失败 → 检查 Docker
- API Key 错误 → 检查 .env 配置
- 爬虫失败 → 检查 Python 虚拟环境
- 搜索无结果 → 运行爬虫

## 相关链接

- **用户文档**: [README.md](README.md)
- **部署文档**: [docs/deploy/](docs/deploy/)
- **AI Skill**: [.claude/skills/deploy.md](.claude/skills/deploy.md)
- **API 文档**: [docs/API.md](docs/API.md)
- **变更日志**: [CHANGELOG.md](CHANGELOG.md)
