// 暗黑模式切换（不依赖 JS 也能正常浏览，只是无法切换主题）
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

function toggleSearchTips() {
    var dropdown = document.getElementById('searchTipsDropdown');
    var btn = document.getElementById('tipsBtn');
    if (dropdown.style.display === 'none') {
        dropdown.style.display = 'block';
        dropdown.style.animation = 'dropdownFadeIn 0.2s ease';
        btn.textContent = '▲ 搜索技巧';
    } else {
        dropdown.style.display = 'none';
        btn.textContent = '▼ 搜索技巧';
    }
}

// 点击其他地方关闭下拉框
document.addEventListener('click', function(e) {
    var dropdown = document.getElementById('searchTipsDropdown');
    var btn = document.getElementById('tipsBtn');
    if (dropdown && btn && !btn.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.style.display = 'none';
        btn.textContent = '▼ 搜索技巧';
    }
});

document.addEventListener('DOMContentLoaded', function() {
    initTheme();
});
