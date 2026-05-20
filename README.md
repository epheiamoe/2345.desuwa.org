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

## 快速部署

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

### 生产环境部署（Docker + Nginx）

#### 1. 克隆代码

```bash
git clone https://github.com/epheiamoe/2345.desuwa.org.git /var/www/2345.desuwa.org
cd /var/www/2345.desuwa.org
```

#### 2. 启动 Meilisearch

```bash
docker-compose up -d
```

#### 3. 配置 API 服务

```bash
cd api
cp env.example .env
```

编辑 `.env` 文件，配置以下内容：

```bash
# 必填：GitHub OAuth（用于登录）
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# 必填：Flask session 密钥（随机字符串，至少32字符）
FLASK_SECRET=your_random_secret_key

# 必填：站点 URL（用于 OAuth 回调）
SITE_URL=https://your-domain.com

# 可选：管理员 GitHub 用户名（逗号分隔）
ADMIN_USERS=your_github_username

# 可选：Meilisearch 配置
MEILISEARCH_HOST=localhost
MEILISEARCH_PORT=7700
MEILISEARCH_INDEX=trans_resources
MEILISEARCH_API_KEY=  # 生产环境必须设置
MEILI_MASTER_KEY=      # 用于生成其他 Key

# 可选：速率限制（覆盖 config.json 默认值）
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_DAY=1000
RATE_LIMIT_PER_MONTH=2000

API_PORT=5000
```

启动 API 服务：

```bash
pip install -r requirements.txt

# 如果使用新组件（推荐）
python app.py

# 或使用部署脚本
bash ../scripts/deploy.sh
```

#### 4. 配置 Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/2345.desuwa.org/frontend;
    index index.php;

    # PHP-FPM
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 5. 运行爬虫

```bash
cd /var/www/2345.desuwa.org/transspider
pip install scrapy trafilatura meilisearch

# 首次爬取
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000

# 添加直接链接
python add_direct_links.py
```

#### 6. 设置定时任务

```bash
# 每周日凌晨3点更新索引
0 3 * * 0 cd /var/www/2345.desuwa.org/transspider && MEILI_MASTER_KEY=xxx MEILISEARCH_API_KEY=yyy scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000 >> /var/log/trans-spider.log 2>&1
0 3 * * 1 cd /var/www/2345.desuwa.org && MEILISEARCH_API_KEY=yyy python add_direct_links.py >> /var/log/trans-spider.log 2>&1
```

#### 7. 启用健康检查（可选）

```bash
# 添加健康检查到定时任务（每5分钟）
*/5 * * * * /var/www/2345.desuwa.org/scripts/health_check.sh >> /var/log/health-check.log 2>&1
```

---

### 生产环境安全建议

1. **Meilisearch 密钥**：设置 `MEILI_MASTER_KEY` 并在配置中启用
2. **API 速率限制**：v1.3+ 已迁移到 SQLite 存储（替代内存），支持多 worker 环境
3. **数据库**：v1.3+ 使用 SQLite（WAL 模式）替代 JSON 文件，修复竞争条件
4. **Session Cookie**：生产环境建议配置 `SESSION_COOKIE_SECURE=true`（HTTPS 时）
5. **输入验证**：v1.3+ 新增 validators.py，对所有 API 参数进行校验
6. **HTTPS**：务必使用 HTTPS 部署

## 架构变更说明（v1.3）

### 新组件

```
api/
├── app.py              # 主程序（待集成新组件）
├── config.py           # 统一配置管理（.env + config.json）
├── database.py         # SQLite 数据库层（WAL 模式）
├── rate_limiter.py     # 滑动窗口速率限制器
├── validators.py       # 输入验证器
└── env.example         # 环境变量模板
```

### 配置管理

配置已从硬编码迁移到外部文件：

- **环境变量**：`.env` 文件（敏感信息）
- **共享配置**：`config.json`（站点设置、标签列表、语言支持）

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

### 已知限制

**v1.3 新组件待集成**：

以下新组件已创建但尚未在 `api/app.py` 中启用：

- `database.py` - SQLite 数据库层
- `rate_limiter.py` - 滑动窗口速率限制器
- `validators.py` - 输入验证器
- `config.py` - 统一配置管理

当前 `app.py` 仍使用旧代码（内存速率限制、JSON 数据库）。
如需启用新组件，需手动修改 `app.py` 导入并使用这些模块。

迁移指南详见：[docs/migration-v1.1.md](docs/migration-v1.1.md)

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
