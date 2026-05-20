<?php

/**
 * 安全输出辅助函数
 *
 * @package TransSearch
 * @license MIT
 */

declare(strict_types=1);

if (!defined('TRANS_SEARCH')) {
    define('TRANS_SEARCH', true);
}

/**
 * 安全输出带高亮标签的文本
 *
 * 逻辑：先转义所有 HTML 字符，再恢复安全的 <em> 标签
 * 这确保了即使输入包含恶意脚本，也会被转义
 *
 * @param string|null $text 原始文本（可能包含 <em> 高亮标签）
 * @return string 安全的 HTML 输出
 */
function format_highlighted(?string $text): string {
    if ($text === null) {
        return '';
    }

    $escaped = htmlspecialchars($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');

    $safe_tags = [
        '&lt;em&gt;'  => '<em>',
        '&lt;/em&gt;' => '</em>',
    ];

    return str_replace(array_keys($safe_tags), array_values($safe_tags), $escaped);
}

/**
 * 安全输出普通文本（无 HTML 标签）
 *
 * @param string|null $text 原始文本
 * @return string 转义后的文本
 */
function e(?string $text): string {
    if ($text === null) {
        return '';
    }
    return htmlspecialchars($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');
}
