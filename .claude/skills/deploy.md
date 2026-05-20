# TransSearch Easy Deploy Skill

## Description

One-command deployment skill for the TransSearch project (2345.desuwa.org). This skill helps AI assistants deploy, rebrand, and maintain the transgender resource search engine.

## When to Use

Use this skill when:
- User wants to deploy their own instance of the search engine
- User needs to rebrand/customize the deployment
- User encounters deployment issues
- User wants to update/upgrade an existing deployment
- User asks about deployment modes (minimal/full/docker)

## Deployment Overview

### Supported Modes

| Mode | Components | Time | Requirements |
|------|-----------|------|-------------|
| **minimal** | PHP + Meilisearch | ~5 min | PHP, Docker |
| **full** | PHP + API + OAuth + Meilisearch | ~15 min | PHP, Python, Docker |
| **docker** | All containerized | ~10 min | Docker Compose |

### Quick Deploy Command

```bash
# Interactive mode (recommended for first-time)
./scripts/install.sh

# Auto mode - minimal
./scripts/install.sh --mode minimal --auto \
  --domain search.example.com \
  --title "My Search"

# Auto mode - full with OAuth
./scripts/install.sh --mode full --auto \
  --domain search.example.com \
  --title "My Search" \
  --github-client-id YOUR_ID \
  --github-secret YOUR_SECRET
```

## Deployment Steps

### 1. Pre-requisites Check

The script automatically detects:
- PHP version (8.0+ recommended)
- Docker (required for Meilisearch)
- Python 3.11+ (required for full mode)
- Nginx (optional, for production)

### 2. Configuration Files Generated

During deployment, the script creates:
- `.env` - Environment variables
- `config.json` - Site configuration
- Nginx config template (displayed, not auto-installed)

### 3. Data Import (Automatic)

The deployment now **automatically** runs:
1. **Web crawler** - Scrapes websites listed in `domains.json`
2. **Direct links** - Adds Steam games, social media links, etc.

This replaces the previous manual steps:
```bash
# OLD manual steps (no longer needed)
cd transspider && scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000
cd .. && python add_direct_links.py
```

### 4. Post-Deploy Actions

After deployment completes:
1. Configure Nginx (copy displayed config)
2. Set up SSL/TLS (Certbot recommended)
3. Verify: `./scripts/verify.sh`

## Customization

### Rebranding

```bash
# Interactive
./scripts/rebrand.sh

# Auto mode
./scripts/rebrand.sh \
  --name "MySearch" \
  --domain "search.example.com" \
  --title "My Trans Search" \
  --repo "https://github.com/myname/search"
```

This updates:
- `config.json` site info
- `.env` domain settings
- `frontend/` fallback values
- Documentation references

### Adding New Websites

Edit `domains.json`:
```json
{
  "domains": [
    {
      "domain": "example.com",
      "name": "Example Site",
      "url": "https://example.com/",
      "tags": ["知识库"]
    }
  ],
  "direct_urls": [
    {
      "url": "https://store.steampowered.com/app/12345",
      "title": "Game Title",
      "tags": ["游戏"]
    }
  ]
}
```

Then re-run crawler:
```bash
cd transspider && scrapy crawl trans
```

## Troubleshooting

### Common Issues

1. **Meilisearch won't start**
   - Check Docker: `docker ps`
   - Check ports: `sudo lsof -i :7700`
   - Restart: `docker-compose restart meilisearch`

2. **API Key errors**
   - Verify `.env` has correct keys
   - Check Meilisearch keys: `curl localhost:7700/keys`

3. **Crawler fails**
   - Check Python virtual environment
   - Verify `MEILISEARCH_API_KEY` in `.env`
   - View logs: `tail -f logs/crawler.log`

4. **Search returns no results**
   - Check index status: `curl localhost:7700/indexes/trans_resources/stats`
   - Run crawler if empty: `cd transspider && scrapy crawl trans`

### Verification

```bash
./scripts/verify.sh
```

Checks:
- PHP version
- Docker status
- Meilisearch health
- Configuration validity
- Nginx config
- Frontend accessibility
- Search functionality
- API health (if enabled)

## Architecture for AI Assistants

### File Structure

```
2345.desuwa.org/
├── .env                  # Environment variables
├── config.json           # Site configuration
├── docker-compose.yml    # Meilisearch only
├── docker-compose.full.yml  # Full stack (optional)
├── frontend/             # PHP frontend
│   ├── index.php
│   ├── config.php        # Config loader
│   ├── manifest.php      # Dynamic PWA manifest
│   └── ...
├── api/                  # Flask API (full mode)
│   ├── app.py
│   ├── venv/             # Python virtual env
│   └── ...
├── transspider/          # Scrapy crawler
│   ├── spiders/
│   │   └── trans_spider.py
│   └── ...
├── scripts/              # Deployment scripts
│   ├── install.sh        # Main deploy script
│   ├── rebrand.sh        # Brand customization
│   └── verify.sh         # Health check
└── docs/deploy/          # Documentation
    ├── QUICKSTART.md
    ├── MINIMAL.md
    ├── FULL.md
    └── TROUBLESHOOTING.md
```

### Key Configuration

**Minimal mode variables:**
```bash
DEPLOY_MODE=minimal
ENABLE_API=false
ENABLE_OAUTH=false
MEILISEARCH_HOST=localhost
MEILISEARCH_PORT=7700
MEILISEARCH_API_KEY=xxx
MEILI_MASTER_KEY=xxx
SITE_URL=https://your-domain.com
```

**Full mode adds:**
```bash
ENABLE_API=true
ENABLE_OAUTH=true
FLASK_SECRET=xxx
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
ADMIN_USERS=github_username
```

### Deployment Flow

```
User runs ./scripts/install.sh
    ↓
Detect environment (PHP, Docker, Python, Nginx)
    ↓
Select mode (minimal/full/docker)
    ↓
Generate .env and config.json
    ↓
Start Meilisearch (Docker)
    ↓
[Full mode] Start Flask API
    ↓
Run crawler → Index web pages
    ↓
Add direct links → Index Steam/social
    ↓
Display Nginx config
    ↓
Show deployment summary
```

## Security Notes for AI

1. **Never commit `.env`** - Contains API keys and secrets
2. **Master Key protection** - MEILI_MASTER_KEY grants full access
3. **GitHub OAuth** - Keep CLIENT_SECRET secure
4. **Rate limiting** - API has built-in rate limits
5. **SQL injection** - PHP uses prepared statements
6. **XSS prevention** - Output is escaped with `htmlspecialchars()`

## Maintenance Tasks

### Update Crawler Data

```bash
cd /path/to/project/transspider
source ../api/venv/bin/activate
scrapy crawl trans -s CLOSESPIDER_ITEMCOUNT=2000
cd ..
python add_direct_links.py
```

### Backup Index

```bash
python3 << 'EOF'
import json, requests
key = open('.env').read().split('MEILI_MASTER_KEY=')[1].split('\n')[0]
url = 'http://localhost:7700/indexes/trans_resources/documents'
docs = []
offset = 0
while True:
    r = requests.get(url, headers={'Authorization': f'Bearer {key}'}, 
                     params={'offset': offset, 'limit': 1000})
    batch = r.json().get('results', [])
    if not batch: break
    docs.extend(batch)
    offset += len(batch)
json.dump(docs, open('backup_index.json', 'w'), ensure_ascii=False)
print(f'Backed up {len(docs)} documents')
EOF
```

### Restore from Backup

```bash
python3 << 'EOF'
import json, requests
key = open('.env').read().split('MEILI_MASTER_KEY=')[1].split('\n')[0]
url = 'http://localhost:7700/indexes/trans_resources/documents'
docs = json.load(open('backup_index.json'))
requests.post(url, headers={'Authorization': f'Bearer {key}'}, 
              json=docs)
print(f'Restored {len(docs)} documents')
EOF
```

## Migration from Old Version

If upgrading from pre-feat/easy-deploy:

1. Backup existing data:
   ```bash
   cp api/db.json api/db.json.backup
   cp .env .env.backup
   ```

2. Pull new code:
   ```bash
   git pull origin main
   ```

3. Run install script (it will detect existing config):
   ```bash
   ./scripts/install.sh --mode full --auto
   ```

4. Migrate data:
   ```bash
   python scripts/migrate_db.py
   ```

## AI Assistant Guidelines

When helping users with deployment:

1. **Always check environment first** - Run verify.sh or manual checks
2. **Recommend minimal mode** for first-time deployers
3. **Warn about OAuth complexity** - Full mode requires GitHub App setup
4. **Emphasize backups** - Before any major changes
5. **Use --auto flag** for repeat deployments
6. **Check logs** when something fails
7. **Suggest rebrand.sh** after successful deployment

## License

MIT - See LICENSE file
