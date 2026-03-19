<?php
/**
 * 语言检测规则配置
 * 
 * 此文件定义了 URL 到语言的映射规则，用于搜索引擎的语言筛选功能。
 * 规则按优先级排序，匹配即返回。
 * 
 * 使用方法：
 *   include_once __DIR__ . '/language_rules.php';
 *   $lang = detectLanguageFromUrl($url);
 * 
 * 自部署者可以修改此文件来自定义语言检测规则。
 */

// 语言路径到语言的映射（最优先）
$LANGUAGE_PATH_MAP = [
    'zh-cn' => 'zh-cn',
    'zh-hant' => 'zh-hant',
    'zh-tw' => 'zh-hant',
    'zh-hk' => 'zh-hant',
    'zh-sg' => 'zh-cn',
    'zh' => 'zh',
    'en' => 'en',
    'ja' => 'ja',
    'es' => 'es',
    'nl' => 'nl',
    'ko' => 'ko',
    'fr' => 'fr',
    'de' => 'de',
    'pl' => 'pl',
    'el' => 'el',
    'hu' => 'hu',
    'ru' => 'ru',
    'it' => 'it',
    'pt' => 'pt',
    'th' => 'th',
    'vi' => 'vi',
    'id' => 'id',
    'ms' => 'ms',
];

// 无语言路径的域名默认语言映射
// 格式: 'domain' => 'default_language'
$DOMAIN_DEFAULT_LANG = [
    // 中文内容为主的域名
    'mtf.wiki' => 'zh-cn',           // MtF Wiki 默认中文
    'ftm.wiki' => 'zh-cn',           // FtM Wiki 默认中文
    'rle.wiki' => 'zh-cn',           // RLE Wiki 默认中文
    'tfsci.mtf.wiki' => 'zh-cn',     // TFSci 默认中文
    'blog.project-trans.org' => 'zh-cn', // Project Trans 博客
    'project-trans.org' => 'zh-cn',   // 默认中文（有 soc8cn 等中文内容）
    'docs.transonline.org.cn' => 'zh-cn',
    'transchinese.org' => 'zh-cn',
    'digital.transchinese.org' => 'zh-cn',
    'cnlgbtdata.com' => 'zh-cn',
    'aboutrans.info' => 'zh-cn',
    'transinacademia.org' => 'zh-cn',
    'viva-la-vita.org' => 'zh-cn',    // 生如夏花 - 中文内容
    'oneamongus.ca' => 'zh-cn',       // 有 zh-Hans 路径
    'hub.mtf.party' => 'zh-cn',       // 中文内容
    
    // 英文内容为主的域名
    'genderdysphoria.fyi' => 'en',   // 英文为主，但有多语言版本
    'transmanhelper.com' => 'en',    // 英文内容
    'mtf.party' => 'zh-cn',          // 中文内容（有 category/jingyan 等中文路径）
    'knowsex.net' => 'zh-cn',        // 中文内容（有 zh-tw 路径）
    
    // 其他
    'uniguide.oau.edu.kg' => 'en',   // 英文内容
];

// URL 模式正则表达式到语言的映射（用于更细粒度的匹配）
// 格式: ['pattern' => 'language', 'weight' => priority]
$URL_PATTERN_RULES = [
    // 英文模式
    ['pattern' => '/tweets?/', 'lang' => 'en', 'weight' => 10],      // Twitter 内容通常是英文
    ['pattern' => '/tweet\//', 'lang' => 'en', 'weight' => 10],
    ['pattern' => '/privacy\.html$/', 'lang' => 'en', 'weight' => 5],
    ['pattern' => '/about\.html$/', 'lang' => 'en', 'weight' => 5],
    ['pattern' => '/contact\.html$/', 'lang' => 'en', 'weight' => 5],
    
    // 中文模式
    ['pattern' => '/\/docs\//', 'lang' => 'zh-cn', 'weight' => 3],   // 中文 wiki 文档
    ['pattern' => '/category\/.*[\x{4e00}-\x{9fff}]/u', 'lang' => 'zh-cn', 'weight' => 8], // URL 含中文
    ['pattern' => '/tag\/.*[\x{4e00}-\x{9fff}]/u', 'lang' => 'zh-cn', 'weight' => 8],     // URL 含中文标签
    ['pattern' => '/\/posts?\//', 'lang' => 'zh-cn', 'weight' => 3],   // 博客文章
];

/**
 * 从 URL 检测语言
 * 
 * @param string $url 完整的 URL
 * @return string 语言代码 (zh-cn, zh-hant, en, ja, es, nl, ko, fr, de, pl, el, hu, ru, ...)
 */
function detectLanguageFromUrl($url) {
    global $LANGUAGE_PATH_MAP, $DOMAIN_DEFAULT_LANG, $URL_PATTERN_RULES;
    
    // 1. 首先检查 URL 路径中的语言路径
    foreach ($LANGUAGE_PATH_MAP as $path => $lang) {
        if (strpos($url, '/' . $path . '/') !== false) {
            return $lang;
        }
    }
    
    // 2. 检查根路径语言（如 /ja, /zh-cn 等在根目录）
    foreach ($LANGUAGE_PATH_MAP as $path => $lang) {
        // 匹配 /ja 或 /ja?query 等情况
        if (preg_match('#/' . $path . '(?:\?|$|/)#', $url)) {
            return $lang;
        }
    }
    
    // 3. 检查 URL 模式规则
    $bestMatch = null;
    $bestWeight = 0;
    
    foreach ($URL_PATTERN_RULES as $rule) {
        if (preg_match('#' . $rule['pattern'] . '#i', $url)) {
            if ($rule['weight'] > $bestWeight) {
                $bestWeight = $rule['weight'];
                $bestMatch = $rule['lang'];
            }
        }
    }
    
    if ($bestMatch) {
        return $bestMatch;
    }
    
    // 4. 从域名判断默认语言
    $parsed = parse_url($url);
    $host = $parsed['host'] ?? '';
    
    // 移除 www. 前缀
    if (strpos($host, 'www.') === 0) {
        $host = substr($host, 4);
    }
    
    if (isset($DOMAIN_DEFAULT_LANG[$host])) {
        return $DOMAIN_DEFAULT_LANG[$host];
    }
    
    // 5. 从 URL 中提取路径判断
    $path = $parsed['path'] ?? '/';
    
    // 检查是否有中文字符
    if (preg_match('/[\x{4e00}-\x{9fff}]/u', $path)) {
        return 'zh-cn';
    }
    
    // 6. 默认返回空字符串（表示未检测到语言）
    return '';
}

/**
 * 检测语言是否匹配用户选择的语言
 * 
 * @param string $url 要检测的 URL
 * @param string $selectedLang 用户选择的语言筛选
 * @return bool 是否匹配
 */
function languageMatches($url, $selectedLang) {
    if (empty($selectedLang) || $selectedLang === '') {
        return true;  // 未选择语言，返回所有
    }
    
    $detectedLang = detectLanguageFromUrl($url);
    
    // 特殊处理：zh 筛选器匹配所有中文
    if ($selectedLang === 'zh') {
        return in_array($detectedLang, ['zh-cn', 'zh-hant', 'zh', '']);
    }
    
    // 特殊处理：全部
    if ($selectedLang === '全部' || $selectedLang === 'all') {
        return true;
    }
    
    return $detectedLang === $selectedLang;
}
