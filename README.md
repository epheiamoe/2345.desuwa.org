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

### 数据来源

本项目数据来源于 [2345.lgbt](https://2345.lgbt) 导航站，包含两类内容：

1. **需要爬取的网站**（`domains.json` 中的网站）：自动爬取内容
2. **直接添加的链接**：直接索引 URL 和标题（如 Twitter、Steam 游戏等）

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
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=200

# 4. 启动 PHP 服务器
cd ../frontend
php -S localhost:8080
```

访问 http://localhost:8080 测试。

### 生产环境部署（Docker + Nginx）

#### 1. 安装依赖

```bash
# 安装 Docker 和 Docker Compose
```

#### 2. 部署代码

```bash
git clone https://github.com/epheiamoe/2345.desuwa.org.git /var/www/2345.desuwa.org
cd /var/www/2345.desuwa.org
```

#### 3. 启动 Meilisearch

```bash
docker-compose up -d
```

#### 4. 配置 Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/2345.desuwa.org/frontend;
    index index.php;

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

#### 5. 运行爬虫

```bash
cd /var/www/2345.desuwa.org/transspider
pip install scrapy trafilatura meilisearch
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=500
```

#### 6. 设置定时任务

```bash
# 每周日凌晨3点更新索引
0 3 * * 0 cd /var/www/2345.desuwa.org/transspider && scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=500 >> /var/log/trans-spider.log 2>&1
```

---

## 配置说明

### 域名列表

- `domains.json` - 完整的域名和标签列表（推荐使用）
- `domains_test.txt` - 测试用域名（少量）

### Meilisearch 配置

在 `transspider/config.py` 中：

```python
MEILISEARCH_HOST = "localhost"
MEILISEARCH_PORT = 7700
MEILISEARCH_INDEX = "trans_resources"
```

### PHP 前端配置

在 `frontend/index.php` 中：

```php
$MEILISEARCH_HOST = 'localhost';
$MEILISEARCH_PORT = '7700';
$MEILISEARCH_INDEX = 'trans_resources';
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

# 3. 编辑 .env 文件，配置以下内容：
# - GITHUB_CLIENT_ID: GitHub OAuth App Client ID
# - GITHUB_CLIENT_SECRET: GitHub OAuth App Client Secret
# - FLASK_SECRET: Flask session 密钥
# - ADMIN_USERS: 管理员 GitHub 用户名（逗号分隔）

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动服务
python app.py
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
│   ├── index.php         # 搜索页面
│   ├── style.css         # 样式
│   └── search.js         # 前端脚本
├── transspider/           # Scrapy 爬虫
│   ├── spiders/           # 爬虫代码
│   ├── pipelines.py      # Meilisearch 推送
│   └── config.py          # 配置
├── api/                   # Flask API 服务
│   ├── app.py             # 主程序
│   ├── console.html       # API 控制台
│   └── env.example        # 环境配置示例
├── docs/                  # 文档
├── domains.json          # 域名和标签列表
├── domains_test.txt      # 测试用域名
├── docker-compose.yml    # Meilisearch Docker
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
