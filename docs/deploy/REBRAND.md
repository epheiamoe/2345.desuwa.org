# 品牌替换指南

> 🎨 将默认品牌替换为你自己的站点信息

## 使用 rebrand.sh（推荐）

### 交互式

```bash
./scripts/rebrand.sh
```

按提示输入：
- 站点名称
- 域名
- 标题
- GitHub 仓库地址

### 非交互式

```bash
./scripts/rebrand.sh \
  --name "MySearch" \
  --domain "search.example.com" \
  --title "My Trans Search" \
  --repo "https://github.com/myname/search"
```

脚本会自动替换所有文件中的品牌信息。

## 手动替换（如果不用脚本）

### 需要修改的文件清单

#### 1. 配置文件

**`.env`**
```bash
SITE_URL=https://your-domain.com
SITE_NAME=YourSiteName
SITE_TITLE=Your Site Title
```

**`config.json`**
```json
{
  "site": {
    "name": "YourSiteName",
    "title": "Your Site Title",
    "url": "https://your-domain.com",
    "github_repo": "https://github.com/yourname/your-repo"
  }
}
```

#### 2. PHP 前端

**`frontend/index.php`**
- 默认标题（fallback）
- 默认描述（fallback）

**`frontend/template.php`**
- 页脚版权信息
- 默认站点名称

#### 3. PWA 配置

**`frontend/manifest.json`**（或 `manifest.php`）
```json
{
  "name": "Your Site Title",
  "short_name": "YourSiteName",
  "description": "Your site description"
}
```

#### 4. 文档

**`README.md`**
- 项目标题
- 在线演示链接
- 相关链接

**`docs/deploy/*.md`**
- 所有文档中的域名引用

#### 5. Nginx 配置

**`config/examples/nginx.*.conf`**
- server_name
- root 路径

#### 6. 爬虫配置

**`transspider/config.py`**（如需要）
- 默认 User-Agent

### 替换检查清单

- [ ] `.env` — 站点 URL、名称、标题
- [ ] `config.json` — 站点信息、GitHub 仓库
- [ ] `frontend/index.php` — fallback 标题和描述
- [ ] `frontend/template.php` — 页脚信息
- [ ] `frontend/manifest.json` — PWA 名称和描述
- [ ] `README.md` — 所有品牌引用
- [ ] `docs/` — 文档中的示例域名
- [ ] Nginx 配置模板 — server_name
- [ ] `docker-compose*.yml` — 容器名称（可选）

## 图标替换

### PWA 图标

替换 `frontend/` 目录下的图标文件：

| 文件 | 尺寸 | 用途 |
|------|------|------|
| `icon.svg` | 矢量 | 主图标（推荐） |
| `icon-192.png` | 192x192 | PWA 图标 |
| `icon-512.png` | 512x512 | PWA 启动画面 |
| `favicon.ico` | 多尺寸 | 浏览器标签页 |
| `apple-touch-icon.png` | 180x180 | iOS 主屏幕 |

### 图标生成工具

```bash
# 使用 ImageMagick 生成各种尺寸
convert icon-512.png -resize 192x192 icon-192.png
convert icon-512.png -resize 180x180 apple-touch-icon.png

# 或使用在线工具
# https://realfavicongenerator.net/
```

### manifest.json 更新

```json
{
  "icons": [
    {
      "src": "icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

## 主题色替换

在 `frontend/style.css` 中修改 CSS 变量：

```css
:root {
  --primary-color: #your-color;
  --secondary-color: #your-color;
  --accent-color: #your-color;
}
```

同时更新 `frontend/manifest.json`：

```json
{
  "theme_color": "#your-color",
  "background_color": "#your-color"
}
```

## 验证替换

运行验证脚本：

```bash
./scripts/verify.sh
```

检查输出中的品牌信息是否正确。

## 常见问题

### Q: rebrand.sh 会修改哪些文件？

**A**: 默认修改：
- `config.json`
- `.env`
- `frontend/index.php`
- `frontend/template.php`
- `frontend/manifest.json`
- `README.md`
- `docs/deploy/*.md`

### Q: 替换后需要重启服务吗？

**A**: 
- PHP 前端：无需重启（PHP 每次请求重新读取）
- Flask API：需要重启（读取 `.env`）
- Meilisearch：无需重启
- Nginx：需要 reload（如果修改了配置）

### Q: 可以保留原品牌的同时添加新品牌吗？

**A**: 不可以。rebrand.sh 是替换操作，会覆盖原品牌信息。如需保留，请先备份。

---

## 相关文档

- [快速开始](QUICKSTART.md)
- [故障排除](TROUBLESHOOTING.md)
