// 检测用户浏览器语言并自动选择
function detectUserLanguage() {
    var urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('q') || urlParams.get('lang')) return;
    
    var userLang = (navigator.language || navigator.userLanguage || '').toLowerCase();
    var lang = 'zh';
    
    if (userLang.startsWith('en')) lang = 'en';
    else if (userLang.startsWith('ja')) lang = 'ja';
    else if (userLang.startsWith('es')) lang = 'es';
    else if (userLang.startsWith('nl')) lang = 'nl';
    else lang = 'zh';
    
    window.location.href = '?lang=' + lang;
}

// 暗黑模式
function initTheme() {
    var theme = localStorage.getItem('theme');
    var isDark = false;
    
    if (theme === 'dark') {
        isDark = true;
    } else if (theme === 'light') {
        isDark = false;
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        isDark = true;
    }
    
    if (isDark) {
        document.body.classList.add('dark');
    }
    
    updateThemeIcon(isDark);
}

function updateThemeIcon(isDark) {
    var themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.textContent = isDark ? '☀️' : '🌙';
    }
}

function toggleTheme() {
    var isDark = document.body.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon(isDark);
}

document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    detectUserLanguage();
    
    var themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', toggleTheme);
    }
});
