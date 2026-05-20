/**
 * 前端交互脚本
 *
 * 使用 IIFE 封装避免全局污染，通过 window.TransSearch 暴露公共 API。
 * 主要功能：主题切换、搜索技巧下拉、标签展开/收起、PWA 安装。
 *
 * [Debt: Accessibility] 当前使用 emoji 作为图标，计划迁移为 SVG。
 * 迁移时需保留 aria-hidden="true" 装饰属性或添加 aria-label。
 */
(function() {
    'use strict';

    // ---- 配置 ----
    const CONFIG = {
        themeKey: 'theme',
        defaultTheme: 'auto',
        tipsAnimation: 'dropdownFadeIn 0.2s ease'
    };

    // ---- DOM 缓存 ----
    const dom = {};

    function cacheDom() {
        dom.body          = document.body;
        dom.themeToggle   = document.getElementById('theme-toggle');
        dom.tipsBtn       = document.getElementById('tipsBtn');
        dom.tipsDropdown  = document.getElementById('searchTipsDropdown');
        dom.moreTagsBtn   = document.getElementById('moreTagsBtn');
        dom.moreTags      = document.querySelectorAll('.tag-more');
        dom.pwaHint       = document.getElementById('pwa-hint');
        dom.pwaInstallBtn = document.getElementById('pwa-install-btn');
    }

    // ---- 主题管理 ----

    /**
     * 初始化主题（根据 localStorage 或系统偏好）
     */
    function initTheme() {
        const theme = localStorage.getItem(CONFIG.themeKey);
        let isDark = false;

        if (theme === 'dark') {
            isDark = true;
        } else if (theme === 'light') {
            isDark = false;
        } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            isDark = true;
        }

        if (isDark) {
            dom.body.classList.add('dark');
        } else {
            dom.body.classList.remove('dark');
        }

        updateThemeIcon(isDark);
    }

    /**
     * 更新主题切换按钮图标
     * @param {boolean} isDark 是否为暗黑模式
     */
    function updateThemeIcon(isDark) {
        if (dom.themeToggle) {
            // [Debt: Accessibility] 使用 SVG 替代 emoji，确保图标语义化
            // 当前保留 emoji 以保持与原界面一致，后续迭代替换为 Lucide SVG
            dom.themeToggle.innerHTML = isDark
                ? '<span aria-hidden="true">☀️</span>'
                : '<span aria-hidden="true">🌙</span>';
        }
    }

    /**
     * 切换明暗主题
     */
    function toggleTheme() {
        const isDark = dom.body.classList.toggle('dark');
        localStorage.setItem(CONFIG.themeKey, isDark ? 'dark' : 'light');
        updateThemeIcon(isDark);
    }

    // ---- 搜索技巧下拉 ----

    /**
     * 切换搜索技巧下拉框显示状态
     */
    function toggleSearchTips() {
        if (!dom.tipsDropdown || !dom.tipsBtn) return;

        const isHidden = dom.tipsDropdown.style.display === 'none' || !dom.tipsDropdown.style.display;
        if (isHidden) {
            dom.tipsDropdown.style.display = 'block';
            dom.tipsDropdown.style.animation = CONFIG.tipsAnimation;
            dom.tipsBtn.textContent = '▲ 搜索技巧';
            dom.tipsBtn.setAttribute('aria-expanded', 'true');
        } else {
            dom.tipsDropdown.style.display = 'none';
            dom.tipsBtn.textContent = '▼ 搜索技巧';
            dom.tipsBtn.setAttribute('aria-expanded', 'false');
        }
    }

    /**
     * 点击外部关闭下拉框
     * @param {MouseEvent} e 点击事件
     */
    function handleClickOutside(e) {
        if (!dom.tipsDropdown || !dom.tipsBtn) return;
        if (!dom.tipsBtn.contains(e.target) && !dom.tipsDropdown.contains(e.target)) {
            dom.tipsDropdown.style.display = 'none';
            dom.tipsBtn.textContent = '▼ 搜索技巧';
            dom.tipsBtn.setAttribute('aria-expanded', 'false');
        }
    }

    // ---- 标签展开/收起 ----

    /**
     * 切换更多标签的显示状态
     */
    function toggleMoreTags() {
        if (!dom.moreTagsBtn || dom.moreTags.length === 0) return;

        const firstTag = dom.moreTags[0];
        const isHidden = firstTag && firstTag.style.display === 'none';

        dom.moreTags.forEach(function(el) {
            el.style.display = isHidden ? 'inline' : 'none';
        });

        dom.moreTagsBtn.textContent = isHidden ? '收起' : '更多';
        dom.moreTagsBtn.setAttribute('aria-label', isHidden ? '收起多余标签' : '显示更多标签');
    }

    // ---- PWA 安装 ----

    let deferredPrompt = null;

    /**
     * 监听 beforeinstallprompt 事件
     */
    window.addEventListener('beforeinstallprompt', function(e) {
        e.preventDefault();
        deferredPrompt = e;
    });

    /**
     * 触发 PWA 安装提示
     */
    function installPWA() {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then(function(choiceResult) {
                if (choiceResult.outcome === 'accepted') {
                    console.log('User accepted the PWA install');
                }
                deferredPrompt = null;
                if (dom.pwaInstallBtn) {
                    dom.pwaInstallBtn.textContent = '已安装';
                    dom.pwaInstallBtn.disabled = true;
                }
            });
        }
    }

    // ---- 初始化 ----

    function init() {
        cacheDom();
        initTheme();

        // 显示 PWA 安装提示（仅当 Service Worker 可用时）
        if (dom.pwaHint && 'serviceWorker' in navigator) {
            dom.pwaHint.style.display = 'block';
        }

        // 注册全局事件监听
        document.addEventListener('click', handleClickOutside);
    }

    // ---- 暴露公共 API ----

    window.TransSearch = {
        toggleTheme: toggleTheme,
        toggleSearchTips: toggleSearchTips,
        toggleMoreTags: toggleMoreTags,
        installPWA: installPWA,
        // jumpToPage 由模板内联脚本注入
    };

    // 启动
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
