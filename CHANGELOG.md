# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-03-19

### Added
- PWA application support (manifest.json, sw.js, icons)
- Language detection rules decoupled from code (frontend/language_rules.php, api/language_rules.py)
- Support for 15+ languages (zh-cn, zh-hant, en, ja, es, nl, ko, fr, de, pl, el, hu, ru, etc.)
- Google-style pagination with page jump input
- Domain default language mapping for sites without language paths
- URL pattern rules for fine-grained language detection
- API console with full parameter support for search testing
- PowerShell curl example alongside bash version
- Dynamic base URL in code examples (self-hosting friendly)

### Changed
- Frontend pagination now shows all pages with ellipsis (Google-style)
- search.js v10 with improved dark mode support
- Console code examples now use dynamic origin

### Fixed
- Security: Meilisearch production mode with Master Key authentication
- Security: Filter injection protection via whitelist validation for tags and domain format
- Security: OAuth token now uses URL fragment (#token=) instead of query string
- Security: FLASK_SECRET now required (no default fallback)
- Security: Error messages sanitized (no internal details leaked)
- Security: CORS restricted to configured SITE_URL only
- Duplicate indexing issue - now uses MD5 hash instead of Python hash() for stable document IDs across processes
- Spider now skips non-text content (images, PDFs)
- Genderdysphoria.fyi correctly detected as English (not Chinese)
- Credits persistence fix in API
- Dark mode for search tips dropdown
- Tags toggle "更多/收起" functionality
- API console token reading from URL fragment
- Frontend stats now uses API key for authenticated Meilisearch
- add_direct_links.py now reads MEILISEARCH_API_KEY from environment

## [1.1.0] - 2026-03-18

### Added
- SITE_URL environment variable for OAuth callback configuration
- MEILISEARCH_API_KEY support for API and crawler
- Fetch 100 results before language filtering to avoid empty pagination

### Changed
- Filter logic changed from OR to AND for tags and domain

### Fixed
- ProxyMiddleware now reads configuration from config.py instead of hardcoded values
- Credits persistence - now saves to db.json on each search
- Filter injection vulnerability - filter values are now escaped
- ADMIN_USERS whitespace issue - now trims whitespace
- Rate limiting IP detection behind reverse proxy
- Domain filter lost on pagination in frontend
- Spider now uses TransResourceItem instead of plain dict

## [1.0.0] - 2026-03-17

### Added
- Multi-language search support (zh-cn, zh-hant, zh, en, ja, es, nl)
- Tag filtering for search results
- Domain filtering
- GitHub OAuth authentication for API
- Free API with 2000 credits/month, 10 requests/minute
- API console for key management
- Admin panel for user management (ban/unban)
- Privacy policy, terms, and disclaimer documents
- API documentation
- Self-hosting support with detailed README

### Fixed
- Duplicate indexing issue (using URL hash as document ID)
- Language detection from URL path
- Nginx proxy configuration
- Flask environment variable loading

### Changed
- Meilisearch as search backend
- Scrapy for web crawling
- Simple PHP frontend

## [0.1.0] - 2026-01-01

### Added
- Initial project setup
- Basic search functionality
- Domain list from 2345.lgbt

---

For older releases, please refer to the git history.
