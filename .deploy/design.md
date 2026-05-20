# Easy Deploy 设计文档

## 分支: feat/easy-deploy
## 目标: 让任何人都能5分钟内部署自己的搜索引擎

---

## 1. 架构哲学

### 核心原则
1. **最小可用**: 只传PHP文件+Docker就能跑
2. **渐进增强**: API、OAuth、爬虫都是可选插件
3. **零硬编码**: 所有品牌信息通过脚本一键替换
4. **模式化**: 三种部署模式，一键切换

### 部署模式

```
┌─────────────────────────────────────────────────────────────┐
│                     最小模式 (Minimal)                        │
│  ┌──────────┐      ┌──────────────┐                         │
│  │   PHP    │──────│ Meilisearch  │                         │
│  │ Frontend │      │   (Docker)   │                         │
│  └──────────┘      └──────────────┘                         │
│                                                             │
│  需要: PHP + Docker                                         │
│  功能: 搜索 + 爬虫                                          │
│  时间: 5分钟                                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     完整模式 (Full)                          │
│  ┌──────────┐      ┌──────────────┐      ┌──────────┐      │
│  │   PHP    │──────│ Meilisearch  │◄─────│  Flask   │      │
│  │ Frontend │      │   (Docker)   │      │   API    │      │
│  └──────────┘      └──────────────┘      └──────────┘      │
│         │                                   │               │
│         └───────────────────────────────────┘               │
│                        GitHub OAuth                         │
│                                                             │
│  需要: PHP + Python + Docker                                │
│  功能: 搜索 + API + OAuth + 爬虫                            │
│  时间: 15分钟                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Docker模式 (Docker)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Docker Compose                          │   │
│  │  ┌──────┐  ┌──────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │Nginx │  │ PHP  │  │Meilisearch│  │Flask API │   │   │
│  │  └──────┘  └──────┘  └──────────┘  └──────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  需要: Docker Compose                                       │
│  功能: 全部                                                 │
│  时间: 10分钟                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 配置系统

### 2.1 环境变量 (.env)

```bash
# === 部署模式 ===
DEPLOY_MODE=minimal           # minimal | full | docker

# === 功能开关 ===
ENABLE_API=false              # 是否启用Flask API
ENABLE_OAUTH=false            # 是否启用GitHub OAuth
ENABLE_CRAWLER=true           # 是否启用爬虫（最小模式也需要手动运行）

# === Meilisearch ===
MEILISEARCH_HOST=localhost
MEILISEARCH_PORT=7700
MEILISEARCH_API_KEY=          # Search Key
MEILI_MASTER_KEY=             # Master Key（用于生成其他Key）

# === 站点配置 ===
SITE_URL=https://your-domain.com
SITE_NAME=YourSiteName
SITE_TITLE=Your Site Title

# === Flask (完整模式) ===
FLASK_SECRET=                 # 随机生成 >=32字符
FLASK_PORT=5000

# === GitHub OAuth (完整模式) ===
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
ADMIN_USERS=                  # 逗号分隔的GitHub用户名

# === 可选 ===
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_DAY=1000
RATE_LIMIT_PER_MONTH=2000
```

### 2.2 共享配置 (config.json)

```json
{
  "site": {
    "name": "{{SITE_NAME}}",
    "title": "{{SITE_TITLE}}",
    "url": "{{SITE_URL}}",
    "github_repo": "https://github.com/yourname/your-repo",
    "partner_site": ""
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
    "max_limit": 100,
    "content_max_length": 5000
  },
  "tags": {
    "available": ["MtF", "FtM", "知识库", "HRT", "手术", "法律", "心理", "社群", "工具", "游戏", "Steam", "影视", "小说", "指南", "学术"]
  },
  "languages": {
    "supported": ["zh-cn", "zh-hant", "en", "ja", "es", "nl", "ko", "fr", "de", "pl", "el", "hu", "ru"]
  },
  "meilisearch": {
    "host": "localhost",
    "port": 7700,
    "use_ssl": false,
    "timeout": 5
  }
}
```

### 2.3 运行时适配规则

**PHP前端根据ENABLE_API自动适配：**
- `ENABLE_API=false` → 隐藏"API控制台"入口按钮
- `ENABLE_OAUTH=false` → 隐藏"登录"按钮
- 搜索始终可用（直接查Meilisearch）

**Flask API根据ENABLE_API启动：**
- `ENABLE_API=false` → 启动时跳过API路由注册，返回503
- `ENABLE_OAUTH=false` → 跳过OAuth蓝图注册

---

## 3. 文件结构

```
2345.desuwa.org/
├── .env.example              # 环境变量模板（随模式变化）
├── .env.minimal.example      # 最小模式专用模板
├── .env.full.example         # 完整模式专用模板
├── config.json               # 共享配置（运行时读取）
├── config.example.json       # 配置模板（首次部署复制）
├── docker-compose.yml        # Meilisearch（所有模式共用）
├── docker-compose.full.yml   # 完整模式（+API+PHP+Nginx）
│
├── frontend/                 # PHP前端
│   ├── index.php
│   ├── config.php            # 配置加载器
│   ├── functions.php         # 工具函数
│   ├── template.php          # 视图模板
│   ├── search.php            # 搜索逻辑
│   ├── style.css
│   ├── search.js
│   └── manifest.php          # 动态manifest（替代静态JSON）
│
├── api/                      # Flask API（可选）
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── rate_limiter.py
│   ├── validators.py
│   ├── wsgi.py
│   └── requirements.txt
│
├── transspider/              # 爬虫（可选，手动运行）
│   ├── config.py
│   ├── settings.py
│   ├── pipelines.py
│   ├── utils.py
│   └── spiders/
│       └── trans_spider.py
│
├── scripts/                  # 部署脚本
│   ├── install.sh            # 主部署向导
│   ├── rebrand.sh            # 品牌替换
│   ├── verify.sh             # 部署验证
│   └── migrate.sh            # 数据迁移
│
├── config/                   # 配置文件模板
│   ├── examples/
│   │   ├── nginx.minimal.conf
│   │   ├── nginx.full.conf
│   │   ├── systemd.api.service
│   │   └── crontab.crawler
│
└── docs/
    ├── deploy/
    │   ├── QUICKSTART.md     # 5分钟快速开始
    │   ├── MINIMAL.md        # 最小模式详解
    │   ├── FULL.md           # 完整模式详解
    │   ├── DOCKER.md         # Docker模式
    │   ├── REBRAND.md        # 品牌替换指南
    │   └── TROUBLESHOOTING.md
    └── README.md             # 项目主文档
```

---

## 4. 关键接口定义

### 4.1 install.sh 接口

```bash
# 交互式（默认）
./scripts/install.sh

# 非交互式 - 最小模式
./scripts/install.sh --mode minimal --auto \
  --domain search.example.com \
  --title "My Search" \
  --path /var/www/search

# 非交互式 - 完整模式
./scripts/install.sh --mode full --auto \
  --domain search.example.com \
  --title "My Search" \
  --path /var/www/search \
  --github-client-id xxx \
  --github-secret xxx

# Docker模式
./scripts/install.sh --mode docker --auto \
  --domain search.example.com
```

### 4.2 rebrand.sh 接口

```bash
# 交互式
./scripts/rebrand.sh

# 非交互式
./scripts/rebrand.sh \
  --name "MySearch" \
  --domain "search.example.com" \
  --title "My Trans Search" \
  --repo "https://github.com/myname/search"
```

### 4.3 verify.sh 接口

```bash
# 验证部署
./scripts/verify.sh

# 输出：
# ✓ PHP 8.1
# ✓ Meilisearch running (Docker)
# ✓ config.json valid
# ✓ .env configured
# ✓ Nginx configured
# ✓ Search working (found X docs)
```

---

## 5. License提取规范

### 5.1 提取规则

爬虫在抓取时，按优先级提取license：

1. `<meta name="license" content="CC-BY-SA-4.0">`
2. `<a rel="license" href="https://creativecommons.org/licenses/by-sa/4.0/">`
3. JSON-LD: `"license": "https://creativecommons.org/licenses/by-sa/4.0/"`
4. 页面文本中的 "Licensed under..." 模式（备选）

### 5.2 标准化存储

```python
{
    "license_type": "CC-BY-SA-4.0",  # 标准化ID
    "license_url": "https://...",     # 原始URL
    "license_name": "Creative Commons Attribution-ShareAlike 4.0"  # 显示名
}
```

### 5.3 显示规则

前端显示简短标识：
- 有license → 显示 "📄 CC-BY-SA"（可点击展开详情）
- 无license → 不显示
- 未知license → 显示 "📄 Unknown"

---

## 6. 原子化提交计划

| # | Commit | 文件 | 说明 |
|---|--------|------|------|
| 1 | `feat(deploy): add deployment mode configuration` | config.json, .env.example, .env.*.example, frontend/config.php | 配置系统 |
| 2 | `feat(deploy): add install.sh with interactive and auto modes` | scripts/install.sh, config/examples/ | 安装向导 |
| 3 | `feat(deploy): add rebrand.sh for easy customization` | scripts/rebrand.sh | 品牌替换 |
| 4 | `feat(license): extract and display HTML license metadata` | transspider/pipelines.py, frontend/ | License提取 |
| 5 | `feat(deploy): add nginx templates and documentation` | config/examples/nginx.*, docs/deploy/ | 部署文档 |
| 6 | `feat(deploy): add verify.sh and polish experience` | scripts/verify.sh, docs/ | 验证与完善 |

---

## 7. 注意事项

### 7.1 不要修改的文件（保持兼容）
- `api/app.py` 核心逻辑（只添加ENABLE_API开关）
- `frontend/search.php` 搜索逻辑（只添加license显示）
- `transspider/spiders/trans_spider.py` 爬虫逻辑

### 7.2 需要新增的文件
- `.env.minimal.example`
- `.env.full.example`
- `config.example.json`
- `frontend/manifest.php`（替代manifest.json）
- `scripts/install.sh`
- `scripts/rebrand.sh`
- `scripts/verify.sh`
- `config/examples/nginx.*`
- `docs/deploy/*.md`

### 7.3 需要修改的文件
- `config.json`（添加deploy字段）
- `.env.example`（添加DEPLOY_MODE等）
- `frontend/index.php`（读取ENABLE_API/ENABLE_OAUTH）
- `frontend/template.php`（条件显示API入口/登录按钮）
- `docker-compose.yml`（添加可选服务）
- `transspider/pipelines.py`（提取license）

---

## 8. 验收标准

### 最小模式部署（5分钟测试）
1. 新用户下载代码
2. `./scripts/install.sh --mode minimal --auto --domain test.local --title Test`
3. Docker启动Meilisearch
4. 访问 `http://test.local` → 看到搜索页面
5. 没有API控制台入口，没有登录按钮
6. 运行爬虫 → 搜索能返回结果

### 完整模式部署（15分钟测试）
1. 同上，但 `--mode full`
2. 配置GitHub OAuth
3. 有API控制台，可以登录
4. 有速率限制

### 品牌替换测试
1. `./scripts/rebrand.sh --name NewBrand --domain new.com`
2. 所有文件中的旧品牌被替换
3. 搜索页面显示新品牌

---

*本文档为 feat/easy-deploy 分支的权威设计参考，所有子代理必须遵循。*
