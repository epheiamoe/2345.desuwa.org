# 跨性别资源搜索引擎 (2345.desuwa.org)

> 只收录 2345.lgbt 导航站资源的专属搜索引擎

**在线演示**: https://2345.desuwa.org

## 项目简介

这是一个可以**自托管**的跨性别资源搜索引擎，仅收录 [2345.lgbt](https://2345.lgbt) 导航站收录的网站内容，不爬取外部网站。

任何人都可以自己部署这个搜索引擎！

### 特性

- 🔍 专注：只收录 2345.lgbt 导航站的可靠资源
- 🏠 自托管：任何人可以自己部署使用
- 🏷️ 标签筛选：支持按 MtF，FtM、HRT 等标签筛选
- 🚀 简单高效：PHP + Meilisearch + Scrapy

### 技术栈

- **爬虫**: Python + Scrapy
- **搜索引擎**: Meilisearch (Docker)
- **前端**: 纯 PHP
- **API**: Flask + GitHub OAuth
- **AI 集成**: 提供 Claude Skill 方便 AI 调用搜索 API

### 数据来源

本项目数据来源于 [2345.lgbt](https://2345.lgbt) 导航站，包含两类内容：

1. **需要爬取的网站**（`domains.json` 中的 `domains` 列表）：自动爬取内容
2. **直接添加的链接**（`domains.json` 中的 `direct_urls` 列表）：直接索引 URL 和标题（如 Steam 游戏、Twitter 账号等）

详细列表见 `domains.json`。

---

## 🚀 快速部署（新版 - 推荐）

**只需一行命令，全自动部署：**

```bash
# 1. 克隆代码
git clone https://github.com/epheiamoe/2345.desuwa.org.git
cd 2345.desuwa.org

# 2. 运行部署向导（交互式）
./scripts/install.sh

# 或全自动模式（适合CI/CD）
./scripts/install.sh --mode minimal --auto \
  --domain search.example.com \
  --title "My Search"
```

部署向导会自动完成：
- ✅ 检测环境（PHP、Docker、Python）
- ✅ 生成配置文件（`.env`、`config.json`）
- ✅ 启动 Meilisearch（Docker）
- ✅ 运行爬虫抓取网站数据
- ✅ 添加直接链接（Steam游戏、社交媒体等）
- ✅ 显示 Nginx 配置

**详细部署文档：**
- [5分钟快速开始](docs/deploy/QUICKSTART.md)
- [最小模式部署](docs/deploy/MINIMAL.md)（仅搜索，无需OAuth）
- [完整模式部署](docs/deploy/FULL.md)（搜索 + API + OAuth）
- [Docker模式部署](docs/deploy/DOCKER.md)
- [品牌替换指南](docs/deploy/REBRAND.md)
- [故障排除](docs/deploy/TROUBLESHOOTING.md)

### 🤖 AI 辅助部署

本项目提供 **Claude Skill**，让 AI 自动帮你部署：

```bash
# 使用 Claude Code 或 Cursor 等 AI 编辑器
# AI 会自动读取 .claude/skills/deploy.md 并执行部署
```

AI Skill 功能：
- 自动检测环境并安装依赖
- 选择合适的部署模式
- 配置站点信息
- 运行爬虫导入数据
- 验证部署结果

详见：[.claude/skills/deploy.md](.claude/skills/deploy.md)

---

## 📦 手动部署（旧版方式）

如果你更喜欢手动控制每一步：

### 本地开发测试

```bash
# 1. 克隆代码
git clone https://github.com/epheiamoe/2345.desuwa.org.git
cd 2345.desuwa.org

# 2. 启动 Meilisearch（需要 Docker）
docker-compose up -d

# 3. 运行爬虫
cd transspider
pip install scrapy trafilatura meilisearch
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000

# 3.1 添加直接链接（如 Steam 游戏、Twitter 等）
python add_direct_links.py

# 4. 启动 PHP 服务器
cd ../frontend
php -S localhost:8080
```

访问 http://localhost:8080 测试。

### 生产环境部署

参考详细文档：
- [最小模式](docs/deploy/MINIMAL.md) - PHP + Meilisearch
- [完整模式](docs/deploy/FULL.md) - 含 API + OAuth

---

### 生产环境安全建议

1. **Meilisearch 密钥**：设置 `MEILI_MASTER_KEY` 并在配置中启用
2. **API 速率限制**：v1.3+ 已迁移到 SQLite 存储（替代内存），支持多 worker 环境
3. **数据库**：v1.3+ 使用 SQLite（WAL 模式）替代 JSON 文件，修复竞争条件
4. **Session Cookie**：生产环境建议配置 `SESSION_COOKIE_SECURE=true`（HTTPS 时）
5. **输入验证**：v1.3+ 新增 validators.py，对所有 API 参数进行校验
6. **HTTPS**：务必使用 HTTPS 部署

## 📋 从旧版迁移

如果你之前部署过旧版本，请按以下步骤迁移：

### 1. 备份数据

```bash
# 备份索引
curl -X POST 'http://localhost:7700/indexes/trans_resources/documents/fetch' \
  -H 'Authorization: Bearer YOUR_MASTER_KEY' \
  -o backup_index.json

# 备份数据库
cp api/db.json api/db.json.backup

# 备份配置
cp .env .env.backup
cp config.json config.json.backup
```

### 2. 更新代码

```bash
# 拉取最新代码
git pull origin main

# 或使用新仓库
git clone https://github.com/epheiamoe/2345.desuwa.org.git trans-search-new
cd trans-search-new
```

### 3. 迁移配置

```bash
# 复制旧配置（如有）
cp /path/to/old/.env .env
cp /path/to/old/config.json config.json

# 或使用新的配置模板
cp .env.full.example .env
cp config.example.json config.json

# 编辑配置文件
nano .env
nano config.json
```

### 4. 重新部署

```bash
# 运行部署向导
./scripts/install.sh --mode full --auto \
  --domain your-domain.com \
  --title "Your Search"
```

### 5. 恢复数据（可选）

```bash
# 如果有备份的索引数据
python3 << 'EOF'
import json, requests
key = open('.env').read().split('MEILI_MASTER_KEY=')[1].split('\n')[0]
url = 'http://localhost:7700/indexes/trans_resources/documents'
docs = json.load(open('backup_index.json'))
requests.post(url, headers={'Authorization': f'Bearer {key}'}, json=docs)
print(f'Restored {len(docs)} documents')
EOF
```

---

## 架构变更说明（v2.0 - Easy Deploy）

### 新增功能

- **一键部署**: `./scripts/install.sh` 全自动部署向导
- **三种模式**: minimal（仅搜索）/ full（+API+OAuth）/ docker（容器化）
- **自动数据导入**: 部署时自动运行爬虫和添加直接链接
- **品牌替换**: `./scripts/rebrand.sh` 一键替换所有品牌信息
- **部署验证**: `./scripts/verify.sh` 检查所有组件状态
- **License 显示**: 自动提取并显示网页版权信息
- **AI Skill**: `.claude/skills/deploy.md` 让 AI 自动部署

### 新组件

```
api/
├── app.py              # 主程序
├── config.py           # 统一配置管理
├── database.py         # SQLite 数据库层（WAL 模式）
├── rate_limiter.py     # 滑动窗口速率限制器
├── validators.py       # 输入验证器
├── wsgi.py             # Gunicorn 入口
└── env.example         # 环境变量模板

scripts/
├── install.sh          # 一键部署向导（NEW）
├── rebrand.sh          # 品牌替换（NEW）
├── verify.sh           # 部署验证（NEW）
└── migrate_db.py       # 数据库迁移

docs/deploy/
├── QUICKSTART.md       # 5分钟快速开始
├── MINIMAL.md          # 最小模式详解
├── FULL.md             # 完整模式详解
├── DOCKER.md           # Docker 模式
├── REBRAND.md          # 品牌替换指南
└── TROUBLESHOOTING.md  # 故障排除

.claude/skills/
└── deploy.md           # AI 部署 Skill
```

### 配置管理

配置已从硬编码迁移到外部文件：

- **环境变量**：`.env` 文件（敏感信息）
- **共享配置**：`config.json`（站点设置、标签列表、语言支持）
- **部署模式**：支持 minimal / full / docker 三种模式

**不再**需要直接修改代码中的配置值。

---

## 配置说明

### 域名列表

- `domains.json` - 完整的域名和标签列表（推荐使用）
- `domains_test.txt` - 测试用域名（少量）

### 配置文件

#### config.json（项目根目录）

共享配置，包含站点信息、标签列表、语言支持等：

```json
{
  "site": {
    "name": "2345.desuwa.org",
    "title": "跨性别资源搜索",
    "url": "https://2345.desuwa.org"
  },
  "tags": {
    "available": ["MtF", "FtM", "HRT", "知识库", "手术", "法律"]
  },
  "languages": {
    "supported": ["zh-cn", "zh-hant", "en", "ja", "es"]
  },
  "rate_limit": {
    "per_minute": 10,
    "per_day": 1000,
    "per_month": 2000
  }
}
```

#### .env（api/ 目录）

敏感信息和环境相关配置：

```bash
FLASK_SECRET=your_secret_key
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_secret
MEILISEARCH_API_KEY=your_api_key
```

#### Nginx 环境变量传递

PHP 通过 `getenv()` 读取环境变量，需要在 Nginx 中传递：

```nginx
location ~ \.php$ {
    fastcgi_pass unix:/tmp/php-cgi-84.sock;
    fastcgi_param MEILISEARCH_API_KEY your_search_key;
    fastcgi_param MEILISEARCH_HOST localhost;
    fastcgi_param MEILISEARCH_PORT 7700;
}
```

---

## 搜索功能

### 基本搜索

```
https://2345.desuwa.org/?q=关键词
```

### 语言筛选

```
# 只显示简体中文
https://2345.desuwa.org/?q=激素&lang=zh-cn

# 只显示繁体中文
https://2345.desuwa.org/?q=激素&lang=zh-hant

# 显示所有中文
https://2345.desuwa.org/?q=激素&lang=zh
```

可用语言：zh-cn（简体中文）、zh-hant（繁体中文）、zh（所有中文）、en、ja、es、nl

### 标签筛选

```
# 只显示 MtF 标签
https://2345.desuwa.org/?q=HRT&tags=MtF

# 显示 MtF 或 FtM 标签
https://2345.desuwa.org/?q=HRT&tags=MtF,FtM
```

可用标签：MtF、FtM、社区、性、知识库、HRT、指南、报告、学术、影视、音乐、游戏、小说、法律、医疗

---

## API 服务

项目提供免费的 REST API，支持 GitHub OAuth 登录。

### 功能

- 🔑 GitHub OAuth 登录
- 📊 每月 2000 次调用配额
- ⚡ 每分钟 10 次请求限制
- 🏷️ 支持标签、语言筛选

### 部署 API 服务

```bash
# 1. 进入 API 目录
cd api

# 2. 复制环境配置
cp env.example .env

# 3. 编辑 .env 文件，配置所有必需变量
# 4. 确认 config.json 存在于项目根目录

# 5. 数据库迁移（从 JSON 到 SQLite，如适用）
python ../scripts/migrate_db.py --source db.json --target db.sqlite

# 6. 安装依赖
pip install -r requirements.txt

# 7. 启动服务
python app.py

# 或使用部署脚本
bash ../scripts/deploy.sh
```

### GitHub OAuth 配置

1. 访问 [GitHub Developer Settings](https://github.com/settings/developers)
2. 创建 OAuth App：
   - Homepage URL: `https://your-domain.com`
   - Callback URL: `https://your-domain.com/api/auth/callback`
3. 将 Client ID 和 Secret 填入 `.env`

### API 使用

详见 [API 文档](docs/API.md)

```bash
# 搜索示例
curl "https://2345.desuwa.org/api/search?q=HRT" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## 目录结构

```
2345.desuwa.org/
├── frontend/              # PHP 前端
│   ├── index.php         # 入口（请求处理）
│   ├── template.php      # 模板渲染
│   ├── functions.php     # 安全输出辅助函数
│   ├── search.php        # 搜索逻辑
│   ├── config.php        # 配置加载器
│   ├── manifest.php      # 动态 PWA manifest
│   ├── language_rules.php # 语言检测规则
│   ├── style.css         # 样式（含 CSS 变量和暗黑模式）
│   ├── search.js         # 前端脚本
│   ├── manifest.json     # PWA 配置（静态备份）
│   └── sw.js             # Service Worker
├── transspider/           # Scrapy 爬虫
│   ├── spiders/           # 爬虫代码
│   ├── pipelines.py      # Meilisearch 推送（SHA-256 ID + License提取）
│   ├── config.py         # 爬虫配置
│   ├── items.py          # Item 定义
│   └── utils.py          # 工具函数（URL 规范化）
├── api/                   # Flask API 服务
│   ├── app.py            # 主程序
│   ├── config.py         # 统一配置管理
│   ├── database.py       # SQLite 数据库层
│   ├── rate_limiter.py   # 滑动窗口速率限制器
│   ├── validators.py     # 输入验证器
│   ├── auth.py           # 认证逻辑
│   ├── language_rules.py # 语言检测规则
│   ├── console.html      # API 控制台
│   ├── wsgi.py           # Gunicorn 入口
│   ├── Dockerfile        # API 容器化
│   └── env.example       # 环境配置示例
├── scripts/               # 部署脚本（NEW）
│   ├── install.sh        # 一键部署向导
│   ├── rebrand.sh        # 品牌替换
│   ├── verify.sh         # 部署验证
│   ├── deploy.sh         # 传统部署脚本
│   ├── health_check.sh   # 健康检查
│   └── migrate_db.py     # 数据库迁移工具
├── docs/                  # 文档
│   ├── deploy/           # 部署文档（NEW）
│   │   ├── QUICKSTART.md   # 5分钟快速开始
│   │   ├── MINIMAL.md      # 最小模式详解
│   │   ├── FULL.md         # 完整模式详解
│   │   ├── DOCKER.md       # Docker 模式
│   │   ├── REBRAND.md      # 品牌替换指南
│   │   └── TROUBLESHOOTING.md # 故障排除
│   ├── API.md            # API 文档
│   └── migration-v1.1.md # 迁移指南
├── config/                # 配置模板（NEW）
│   └── examples/
│       ├── nginx.minimal.conf   # Nginx 最小配置
│       ├── nginx.full.conf      # Nginx 完整配置
│       ├── systemd.api.service  # Systemd 服务
│       └── crontab.crawler      # 定时任务示例
├── .claude/               # AI 配置（NEW）
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
└── README.md
```
2345.desuwa.org/
├── frontend/              # PHP 前端
│   ├── index.php         # 入口（请求处理）
│   ├── template.php      # 模板渲染
│   ├── functions.php     # 安全输出辅助函数
│   ├── search.php        # 搜索逻辑
│   ├── config.php        # 配置加载器
│   ├── language_rules.php # 语言检测规则
│   ├── style.css         # 样式（含 CSS 变量和暗黑模式）
│   ├── search.js         # 前端脚本
│   ├── manifest.json     # PWA 配置
│   └── sw.js             # Service Worker
├── transspider/           # Scrapy 爬虫
│   ├── spiders/           # 爬虫代码
│   ├── pipelines.py      # Meilisearch 推送（SHA-256 ID）
│   ├── config.py         # 爬虫配置
│   └── utils.py          # 工具函数（URL 规范化）
├── api/                   # Flask API 服务
│   ├── app.py            # 主程序
│   ├── config.py         # 统一配置管理
│   ├── database.py       # SQLite 数据库层
│   ├── rate_limiter.py   # 滑动窗口速率限制器
│   ├── validators.py     # 输入验证器
│   ├── language_rules.py # 语言检测规则
│   ├── console.html      # API 控制台
│   └── env.example       # 环境配置示例
├── scripts/               # 运维脚本
│   ├── deploy.sh         # 部署脚本
│   ├── health_check.sh   # 健康检查
│   └── migrate_db.py     # 数据库迁移工具
├── docs/                  # 文档
│   ├── API.md            # API 文档
│   └── migration-v1.1.md # 迁移指南
├── config.json           # 共享配置（站点、标签、语言）
├── domains.json          # 域名和标签列表
├── domains_test.txt      # 测试用域名
├── docker-compose.yml    # Meilisearch Docker
├── CHANGELOG.md          # 变更日志
└── README.md
```

---

## 许可证

LGPLv3 - 与 2345.lgbt 相同

---

## 相关链接

- **在线演示**: https://2345.desuwa.org
- **导航站**: https://2345.lgbt
- **GitHub**: https://github.com/epheiamoe/2345.desuwa.org
