<?php

declare(strict_types=1);

/**
 * 前端模板渲染函数
 *
 * 将 HTML 视图逻辑从入口文件中提取出来，实现关注点分离。
 * 每个渲染函数接收统一的 $data 数组参数，包含页面所需的所有数据。
 *
 * @package TransSearch
 * @license MIT
 */

if (!defined('TRANS_SEARCH')) {
    define('TRANS_SEARCH', true);
}

/**
 * 渲染页面头部（含 HTML 骨架、head 标签、header 导航）
 *
 * @param array $data 页面数据，需包含 selected_lang 等
 */
function render_header(array $data): void {
    $site_name  = e(AppConfig::get('site.name', '2345.desuwa.org'));
    $site_title = e(AppConfig::get('site.title', '跨性别资源搜索'));
    $selected_lang = $data['selected_lang'] ?? '';
    $home_url = $selected_lang ? '/?lang=' . urlencode($selected_lang) : '/';
    ?>
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo $site_name . ' - ' . $site_title; ?></title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1a73e8">
    <link rel="icon" type="image/svg+xml" href="/icon.svg">
    <link rel="apple-touch-icon" href="/icon-192.png">
    <link rel="stylesheet" href="style.css?v=14">
</head>
<body>
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').then(function(registration) {
            console.log('ServiceWorker registration successful');
        }).catch(function(err) {
            console.log('ServiceWorker registration failed: ', err);
        });
    }
    </script>
    <header class="header">
        <a href="<?php echo $home_url; ?>" class="logo"><?php echo $site_name; ?></a>
        <nav class="nav-links" aria-label="主导航">
            <a href="<?php echo e(AppConfig::get('site.partner_site', 'https://2345.lgbt')); ?>" target="_blank" rel="noopener"><?php echo e(AppConfig::get('site.partner_site_name', '2345.lgbt 导航站')); ?></a>
            <a href="<?php echo e(AppConfig::get('site.github_repo', 'https://github.com/epheiamoe/2345.desuwa.org')); ?>" target="_blank" rel="noopener" style="color:#1a73e8;">⭐ 开源</a>
            <?php if (AppConfig::isApiEnabled()): ?>
            <a href="/api/console.html" target="_blank" rel="noopener">API 控制台</a>
            <a href="/docs/api.html" target="_blank" rel="noopener">API 文档</a>
            <?php endif; ?>
            <a href="javascript:window.TransSearch && window.TransSearch.toggleTheme()" id="theme-toggle" title="切换主题" aria-label="切换明暗主题"><span aria-hidden="true">🌙</span></a>
        </nav>
    </header>

    <main class="main">
<?php
}

/**
 * 渲染搜索表单（含搜索框、语言筛选、标签筛选）
 *
 * @param array $data 页面数据
 */
function render_search_form(array $data): void {
    $query          = $data['query'] ?? '';
    $selected_tags  = $data['selected_tags'] ?? [];
    $selected_lang  = $data['selected_lang'] ?? '';
    $selected_site  = $data['selected_site'] ?? '';
    $total_docs     = $data['total_docs'] ?? 0;
    $available_tags = $data['available_tags'] ?? [];
    $available_languages = $data['available_languages'] ?? [];
    $has_query      = !empty($query);
    $site_param     = $selected_site ? '&site=' . urlencode($selected_site) : '';
    ?>
        <div class="search-box">
            <form method="GET" action="" class="search-form" role="search" aria-label="站内搜索">
                <input
                    type="text"
                    name="q"
                    class="search-input"
                    placeholder="搜索跨性别资源..."
                    value="<?php echo e($query); ?>"
                    autofocus
                    aria-label="搜索关键词"
                >
                <input type="hidden" name="tags" id="tags-input" value="<?php echo e(implode(',', $selected_tags)); ?>">
                <input type="hidden" name="lang" id="lang-input" value="<?php echo e($selected_lang); ?>">
                <button type="submit" class="search-btn" aria-label="搜索">搜索</button>
            </form>

            <!-- 语言筛选 -->
            <div style="margin-top:12px;">
                <span style="color:#666;font-size:13px;margin-right:8px;">语言：</span>
                <?php foreach ($available_languages as $lang_code => $lang_name): ?>
                    <a href="?q=<?php echo urlencode($query); ?><?php render_tag_params($selected_tags); ?><?php echo $site_param; ?>&lang=<?php echo urlencode($lang_code); ?>"
                       class="lang-link <?php echo $selected_lang === $lang_code ? 'active' : ''; ?>">
                        <?php echo e($lang_name); ?>
                    </a>
                <?php endforeach; ?>
                <a href="?q=<?php echo urlencode($query); ?><?php render_tag_params($selected_tags); ?><?php echo $site_param; ?>"
                   class="lang-link <?php echo $selected_lang === '' ? 'active' : ''; ?>">
                    全部
                </a>
            </div>

            <?php if (!$has_query): ?>
            <p style="margin-top:15px;color:#666;font-size:14px;">共收录 <?php echo number_format($total_docs); ?> 条跨性别资源</p>
            <?php endif; ?>

            <!-- 标签筛选 -->
            <div style="margin-top:10px;">
                <span style="color:#666;font-size:13px;margin-right:8px;">标签：</span>
                <?php render_tag_links($query, $selected_tags, $selected_lang, $selected_site, $available_tags); ?>
                <button onclick="window.TransSearch && window.TransSearch.toggleMoreTags()" id="moreTagsBtn" style="background:none;border:none;color:#1a73e8;font-size:13px;cursor:pointer;padding:2px 6px;" aria-label="显示更多标签">更多</button>
            </div>
        </div>
<?php
}

/**
 * 渲染标签参数（用于 URL 拼接）
 *
 * @param array $selected_tags 已选中的标签数组
 */
function render_tag_params(array $selected_tags): void {
    if ($selected_tags) {
        echo '&tags=' . urlencode(implode(',', $selected_tags));
    }
}

/**
 * 渲染标签链接列表
 *
 * @param string $query 当前搜索词
 * @param array $selected_tags 已选中的标签
 * @param string $selected_lang 已选中的语言
 * @param string $selected_site 已选中的站点
 * @param array $available_tags 可用标签列表
 */
function render_tag_links(string $query, array $selected_tags, string $selected_lang, string $selected_site, array $available_tags): void {
    $total_tags = count($available_tags);
    $visible_count = 8;

    foreach ($available_tags as $i => $tag) {
        if ($i === $visible_count) {
            echo '<span class="tag-more" style="display:none;">';
        }

        if (in_array($tag, $selected_tags, true)) {
            $new_tags = array_filter($selected_tags, function ($t) use ($tag) { return $t !== $tag; });
            $tag_link = $new_tags ? '&tags=' . urlencode(implode(',', $new_tags)) : '';
        } else {
            $new_tags = array_merge($selected_tags, [$tag]);
            $tag_link = '&tags=' . urlencode(implode(',', $new_tags));
        }

        $site_param = $selected_site ? '&site=' . urlencode($selected_site) : '';
        $lang_param = $selected_lang ? '&lang=' . urlencode($selected_lang) : '';
        $is_active  = in_array($tag, $selected_tags, true);
        ?>
        <a href="?q=<?php echo urlencode($query); ?><?php echo $lang_param; ?><?php echo $site_param; ?><?php echo $tag_link; ?>"
           class="tag-link <?php echo $is_active ? 'active' : ''; ?>">
            <?php echo e($tag); ?>
        </a>
        <?php
        if ($i === $total_tags - 1) {
            echo '</span>';
        }
    }
}

/**
 * 渲染搜索结果区域（含错误提示、结果列表、分页、AI 概览、搜索技巧）
 *
 * @param array $data 页面数据
 */
function render_results(array $data): void {
    $query = $data['query'] ?? '';
    $error = $data['error'] ?? '';
    $results = $data['results'] ?? [];
    $total_hits = $data['total_hits'] ?? 0;
    $search_time = $data['search_time'] ?? 0;

    if ($error) {
        echo '<div class="error-msg">' . e($error) . '</div>';
    }

    if ($query && !$error) {
        render_results_info($total_hits, $search_time);
        render_domain_filter($data);

        if (empty($results)) {
            echo '<div class="no-results"><p>没有找到相关结果，请尝试其他关键词</p></div>';
        } else {
            render_results_list($results);
            render_pagination($data);
        }

        render_ai_overview();
    }

    render_search_tips();
}

/**
 * 渲染搜索结果统计信息
 *
 * @param int $total_hits 总命中数
 * @param int $search_time 搜索耗时（毫秒）
 */
function render_results_info(int $total_hits, int $search_time): void {
    ?>
    <div class="results-info">
        找到约 <?php echo number_format($total_hits); ?> 个结果
        (<?php echo $search_time; ?> 毫秒)
    </div>
    <?php
}

/**
 * 渲染域名筛选器
 *
 * @param array $data 页面数据
 */
function render_domain_filter(array $data): void {
    $query         = $data['query'] ?? '';
    $results       = $data['results'] ?? [];
    $selected_tags = $data['selected_tags'] ?? [];
    $selected_lang = $data['selected_lang'] ?? '';
    $selected_site = $data['selected_site'] ?? '';

    $domain_counts = [];
    foreach ($results as $r) {
        $d = $r['domain'] ?? '';
        if ($d) {
            $domain_counts[$d] = ($domain_counts[$d] ?? 0) + 1;
        }
    }

    if (empty($results) || count($domain_counts) === 0) {
        return;
    }

    $tag_params = '';
    if ($selected_tags) {
        foreach ($selected_tags as $t) {
            $tag_params .= '&tags=' . urlencode($t);
        }
    }
    $lang_param = $selected_lang ? '&lang=' . urlencode($selected_lang) : '';
    $total_domains = count($domain_counts);
    ?>
    <div class="domain-filter">
        <span style="color:#666;">来源：</span>
        <?php if ($selected_site): ?>
        <a href="?q=<?php echo urlencode($query); ?><?php echo $tag_params; ?><?php echo $lang_param; ?>"
           class="domain-link" style="background:#d93025;color:#fff;border-color:#d93025;" title="清除站点筛选">
            <?php echo e($selected_site); ?> ✕
        </a>
        <?php endif; ?>
        <?php
        $i = 0;
        foreach (array_keys($domain_counts) as $domain):
            if ($domain === $selected_site) {
                continue;
            }
            $i++;
            $show  = $i <= 5;
            $style = $show ? '' : 'display:none;';
        ?>
            <a href="?q=<?php echo urlencode($query); ?><?php echo $tag_params; ?><?php echo $lang_param; ?>&site=<?php echo urlencode($domain); ?>"
               class="domain-link" style="<?php echo $style; ?>"
               title="只看 <?php echo e($domain); ?>">
                <?php echo e($domain); ?> (<?php echo $domain_counts[$domain]; ?>)
            </a>
        <?php endforeach; ?>
        <?php if ($total_domains > 5): ?>
            <a href="javascript:void(0)" onclick="var links=document.querySelectorAll('.domain-link-hidden');links.forEach(l=>l.style.display='inline');this.style.display='none';" class="domain-link-more">更多 (<?php echo $total_domains - 5; ?>)</a>
        <?php endif; ?>
    </div>
    <?php
}

/**
 * 渲染搜索结果列表
 *
 * @param array $results 搜索结果数组
 */
function format_license(string $license_type): string {
    $cc_names = [
        'CC-BY-4.0' => 'CC BY',
        'CC-BY-SA-4.0' => 'CC BY-SA',
        'CC-BY-NC-4.0' => 'CC BY-NC',
        'CC-BY-NC-SA-4.0' => 'CC BY-NC-SA',
        'CC-BY-ND-4.0' => 'CC BY-ND',
        'CC-BY-NC-ND-4.0' => 'CC BY-NC-ND',
    ];
    return $cc_names[$license_type] ?? $license_type;
}

function render_results_list(array $results): void {
    ?>
    <div class="results-list">
    <?php foreach ($results as $result): ?>
        <article class="result-item">
            <div class="result-title">
                <?php
                $link_url = $result['url'] ?? '';
                if (!preg_match('/^https?:\/\/[^\/]+(\/.*)?$/i', $link_url)) {
                    $link_url = 'https://' . ($result['domain'] ?? '');
                }
                $title = !empty($result['_formatted']['title'])
                    ? format_highlighted($result['_formatted']['title'] ?? null)
                    : e($result['title'] ?? null);
                ?>
                <a href="<?php echo e($link_url); ?>" target="_blank" rel="noopener">
                    <?php echo $title; ?>
                </a>
            </div>
            <div class="result-url">
                <?php
                $url    = $result['url'] ?? '';
                $domain = $result['domain'] ?? '';

                $url_valid = !empty($url) && preg_match('/^https?:\/\/[^\/]+(\/.*)?$/i', $url);
                if (!$url_valid) {
                    $url = 'https://' . $domain . '/';
                }

                $display_url = strlen($url) > 80 ? substr($url, 0, 80) . '...' : $url;
                $url_path    = preg_replace('/^https?:\/\/' . preg_quote($domain, '/') . '/i', '', $display_url);
                if ($url_path === $display_url || $url_path === '') {
                    $url_path = '/';
                }
                ?>
                <strong><?php echo e($domain); ?></strong>
                <span style="color:#545454;"> - <?php echo e($url_path); ?></span>
            </div>
            <?php if (!empty($result['tags'])): ?>
            <div class="result-tags">
                <?php foreach ($result['tags'] as $tag): ?>
                    <span class="tag-badge"><?php echo e($tag); ?></span>
                <?php endforeach; ?>
            </div>
            <?php endif; ?>
            <div class="result-snippet">
                <?php if (!empty($result['_formatted']['content'])): ?>
                    <?php echo format_highlighted($result['_formatted']['content'] ?? null); ?>
                <?php else: ?>
                    <?php echo e(mb_substr($result['content'] ?? '', 0, 200)); ?>...
                <?php endif; ?>
            </div>
            <?php if (!empty($result['license_type'])): ?>
            <div class="result-license">
                <span class="license-badge" title="<?= e($result['license_type']) ?>">
                    <svg class="license-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                    <?= e(format_license($result['license_type'])) ?>
                </span>
            </div>
            <?php endif; ?>
        </article>
    <?php endforeach; ?>
    </div>
    <?php
}

/**
 * 渲染分页导航
 *
 * @param array $data 页面数据
 */
function render_pagination(array $data): void {
    $query         = $data['query'] ?? '';
    $page          = $data['page'] ?? 1;
    $total_hits    = $data['total_hits'] ?? 0;
    $selected_tags = $data['selected_tags'] ?? [];
    $selected_lang = $data['selected_lang'] ?? '';
    $selected_site = $data['selected_site'] ?? '';
    $limit         = $data['limit'] ?? 10;

    $total_pages = (int) ceil($total_hits / $limit);
    if ($total_pages <= 1) {
        return;
    }

    $base_params = 'q=' . urlencode($query);
    foreach ($selected_tags as $tag) {
        $base_params .= '&tags[]=' . urlencode($tag);
    }
    if ($selected_lang) {
        $base_params .= '&lang=' . urlencode($selected_lang);
    }
    if ($selected_site) {
        $base_params .= '&site=' . urlencode($selected_site);
    }

    $show_pages = 7;
    $half       = floor($show_pages / 2);
    ?>
    <nav class="pagination" aria-label="搜索结果分页">
        <?php if ($page > 1): ?>
            <a href="?<?php echo $base_params; ?>&page=<?php echo $page - 1; ?>">上一页</a>
        <?php endif; ?>

        <?php if ($total_pages <= $show_pages + 2): ?>
            <?php for ($i = 1; $i <= $total_pages; $i++): ?>
                <?php if ($i == $page): ?>
                    <span class="current" aria-current="page"><?php echo $i; ?></span>
                <?php else: ?>
                    <a href="?<?php echo $base_params; ?>&page=<?php echo $i; ?>"><?php echo $i; ?></a>
                <?php endif; ?>
            <?php endfor; ?>
        <?php else: ?>
            <?php
            $start_page = max(1, $page - $half);
            $end_page   = min($total_pages, $page + $half);

            if ($start_page > $total_pages - $show_pages + 1) {
                $start_page = $total_pages - $show_pages + 1;
                $end_page   = $total_pages;
            }
            if ($end_page < $show_pages) {
                $end_page   = $show_pages;
                $start_page = 1;
            }
            ?>

            <?php if ($start_page > 1): ?>
                <a href="?<?php echo $base_params; ?>&page=1">1</a>
                <?php if ($start_page > 2): ?>
                    <span style="padding: 6px 4px;" aria-hidden="true">...</span>
                <?php endif; ?>
            <?php endif; ?>

            <?php for ($i = $start_page; $i <= $end_page; $i++): ?>
                <?php if ($i == $page): ?>
                    <span class="current" aria-current="page"><?php echo $i; ?></span>
                <?php else: ?>
                    <a href="?<?php echo $base_params; ?>&page=<?php echo $i; ?>"><?php echo $i; ?></a>
                <?php endif; ?>
            <?php endfor; ?>

            <?php if ($end_page < $total_pages): ?>
                <?php if ($end_page < $total_pages - 1): ?>
                    <span style="padding: 6px 4px;" aria-hidden="true">...</span>
                <?php endif; ?>
                <a href="?<?php echo $base_params; ?>&page=<?php echo $total_pages; ?>"><?php echo $total_pages; ?></a>
            <?php endif; ?>
        <?php endif; ?>

        <div class="page-jump">
            <input type="number" id="pageInput" min="1" max="<?php echo $total_pages; ?>" placeholder="页码" aria-label="跳转到页码">
            <button onclick="window.TransSearch && window.TransSearch.jumpToPage()" aria-label="跳转">跳转</button>
        </div>

        <?php if ($page < $total_pages): ?>
            <a href="?<?php echo $base_params; ?>&page=<?php echo $page + 1; ?>">下一页</a>
        <?php endif; ?>
    </nav>
    <script>
    window.TransSearch = window.TransSearch || {};
    window.TransSearch.jumpToPage = function() {
        var input = document.getElementById('pageInput');
        var page  = input.value;
        if (page >= 1 && page <= <?php echo $total_pages; ?>) {
            window.location.href = '?' + <?php echo json_encode($base_params); ?> + '&page=' + page;
        }
    };
    document.getElementById('pageInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') window.TransSearch.jumpToPage();
    });
    </script>
    <?php
}

/**
 * 渲染 AI 智能摘要占位区域
 */
function render_ai_overview(): void {
    ?>
    <div class="ai-overview">
        <h3>AI 智能摘要（开发中）</h3>
        <p>此功能正在开发中，预计后续版本将提供LLM智能摘要功能。</p>
    </div>
    <?php
}

/**
 * 渲染搜索技巧下拉组件
 */
function render_search_tips(): void {
    ?>
    <div style="text-align:center;margin-top:20px;position:relative;display:inline-block;width:100%;">
        <button onclick="window.TransSearch && window.TransSearch.toggleSearchTips()" id="tipsBtn" style="background:#f1f3f4;border:1px solid #dfe1e5;border-radius:16px;color:#666;font-size:12px;padding:6px 16px;cursor:pointer;" aria-label="搜索技巧" aria-expanded="false">
            ▼ 搜索技巧
        </button>
        <div class="search-tips-dropdown" id="searchTipsDropdown" style="display:none;position:absolute;left:50%;transform:translateX(-50%);top:100%;z-index:100;background:#fff;border:1px solid #dfe1e5;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);padding:15px 20px;text-align:left;min-width:280px;margin-top:8px;">
            <div style="font-size:13px;color:#333;line-height:1.8;">
                <div style="margin-bottom:10px;"><strong>搜索语法</strong></div>
                <div style="margin-bottom:6px;"><code style="background:#f1f3f4;padding:2px 6px;border-radius:3px;color:#1a73e8;">"精确短语"</code> 精确匹配</div>
                <div style="margin-bottom:6px;"><code style="background:#f1f3f4;padding:2px 6px;border-radius:3px;color:#1a73e8;">word1 OR word2</code> 或匹配</div>
                <div style="margin-bottom:6px;"><code style="background:#f1f3f4;padding:2px 6px;border-radius:3px;color:#1a73e8;">word1 NOT word2</code> 排除</div>
                <div style="margin-bottom:10px;"><code style="background:#f1f3f4;padding:2px 6px;border-radius:3px;color:#1a73e8;">word*</code> 前缀匹配</div>
                <div><strong>快捷筛选</strong></div>
                <div style="margin-bottom:10px;"><code style="background:#f1f3f4;padding:2px 6px;border-radius:3px;color:#1a73e8;">site:example.com</code> 站点筛选</div>
                <div id="pwa-hint" style="display:none;border-top:1px solid #dfe1e5;padding-top:10px;margin-top:8px;">
                    <div style="margin-bottom:6px;"><strong>PWA 应用</strong></div>
                    <div style="margin-bottom:6px;"><button onclick="window.TransSearch && window.TransSearch.installPWA()" id="pwa-install-btn" style="background:#1a73e8;color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;" aria-label="安装PWA应用">安装应用</button></div>
                </div>
            </div>
        </div>
    </div>
    <?php
}

/**
 * 渲染页面页脚
 *
 * @param array $data 页面数据
 */
function render_footer(array $data): void {
    ?>
    </main>

    <footer class="footer">
        <div class="footer-content">
            <div class="disclaimer">
                <strong><?php echo e(AppConfig::get('footer.disclaimer_label', '免责声明：')); ?></strong><?php echo e(AppConfig::get('footer.disclaimer_text', '本搜索引擎仅收录 2345.lgbt 公开资源，仅供参考。医疗问题请咨询专业医生，本网站不承担任何责任。')); ?>
            </div>
            <p>
                <a href="/docs/about.html"><?php echo e(AppConfig::get('footer.links.about', '关于')); ?></a> |
                <a href="/docs/terms.html"><?php echo e(AppConfig::get('footer.links.terms', '服务条款')); ?></a> |
                <a href="/docs/privacy.html"><?php echo e(AppConfig::get('footer.links.privacy', '隐私政策')); ?></a> |
                <a href="/docs/disclaimer.html"><?php echo e(AppConfig::get('footer.links.disclaimer', '免责声明')); ?></a> |
                <a href="<?php echo e(AppConfig::get('site.github_repo', 'https://github.com/epheiamoe/2345.desuwa.org')); ?>" target="_blank" rel="noopener"><?php echo e(AppConfig::get('footer.links.opensource', '开源')); ?></a> |
                <?php echo e(AppConfig::get('footer.copyright', '© 2026 2345.desuwa.org')); ?> |
                <?php echo e(AppConfig::get('footer.data_source_label', '数据来源：')); ?><a href="<?php echo e(AppConfig::get('site.partner_site', 'https://2345.lgbt')); ?>" target="_blank" rel="noopener"><?php echo e(AppConfig::get('site.partner_site_name', '2345.lgbt')); ?></a>
            </p>
        </div>
    </footer>
    <script src="search.js?v=11"></script>
</body>
</html>
    <?php
}
