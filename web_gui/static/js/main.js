/**
 * 合成计算器 - 主JavaScript文件
 */

// ========================================
// 全局状态
// ========================================
const AppState = {
    currentGame: null,
    items: [],
    currentCalculation: null
};

// ========================================
// API请求封装
// ========================================
const API = {
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };

        try {
            showLoading();
            const response = await fetch(url, { ...defaultOptions, ...options });
            const data = await response.json();
            hideLoading();
            return data;
        } catch (error) {
            hideLoading();
            showToast('请求失败', error.message, 'error');
            throw error;
        }
    },

    // 获取配方文件列表
    getGames() {
        return this.request('/api/games');
    },

    // 选择配方文件
    selectGame(gameName) {
        return this.request('/api/select-game', {
            method: 'POST',
            body: JSON.stringify({ game: gameName })
        });
    },

    // 获取物品列表
    getItems() {
        return this.request('/api/items');
    },

    // 获取配方列表
    getRecipes(page = 1, perPage = 20, search = '') {
        const params = new URLSearchParams({ page, per_page: perPage, search });
        return this.request(`/api/recipes?${params}`);
    },

    // 获取单个配方
    getRecipe(name) {
        return this.request(`/api/recipes/${encodeURIComponent(name)}`);
    },

    // 创建配方
    createRecipe(recipe) {
        return this.request('/api/recipes', {
            method: 'POST',
            body: JSON.stringify(recipe)
        });
    },

    // 更新配方
    updateRecipe(name, recipe) {
        return this.request(`/api/recipes/${encodeURIComponent(name)}`, {
            method: 'PUT',
            body: JSON.stringify(recipe)
        });
    },

    // 删除配方
    deleteRecipe(name) {
        return this.request(`/api/recipes/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        });
    },

    // 计算生产链
    calculate(targetItem, targetRate, options = {}) {
        return this.request('/api/calculate', {
            method: 'POST',
            body: JSON.stringify({
                target_item: targetItem,
                target_rate: targetRate,
                options
            })
        });
    },

    // 获取节点的替代路径
    getAlternatives(gameName, targetItem, targetRate, nodeItem) {
        const params = new URLSearchParams({
            game_name: gameName,
            target_item: targetItem,
            target_rate: targetRate,
            node_item: nodeItem
        });
        return this.request(`/api/calculate/alternatives?${params}`);
    }
};

// ========================================
// UI工具函数
// ========================================

// 显示加载遮罩
function showLoading() {
    document.getElementById('loadingOverlay').classList.add('active');
}

// 隐藏加载遮罩
function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

// 显示Toast通知
function showToast(title, message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-title">${escapeHtml(title)}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
    `;

    container.appendChild(toast);

    // 3秒后自动移除
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 格式化数字
function formatNumber(num, decimals = 2) {
    if (num === undefined || num === null) return '-';
    return Number(num).toFixed(decimals);
}

// 格式化速率
function formatRate(rate) {
    if (rate === undefined || rate === null) return '-';
    if (rate >= 1) {
        return `${formatNumber(rate)}/s`;
    } else if (rate >= 0.0167) {
        return `${formatNumber(rate * 60)}/min`;
    } else {
        return `${formatNumber(rate * 3600)}/h`;
    }
}

// 自动补全组件
class Autocomplete {
    constructor(inputId, options = {}) {
        this.input = document.getElementById(inputId);
        this.data = options.data || [];
        this.onSelect = options.onSelect || (() => {});
        this.container = null;
        this.list = null;
        this.selectedIndex = -1;

        this.init();
    }

    init() {
        // 创建容器
        this.container = document.createElement('div');
        this.container.className = 'autocomplete-container';
        this.input.parentNode.insertBefore(this.container, this.input);
        this.container.appendChild(this.input);

        // 创建列表
        this.list = document.createElement('div');
        this.list.className = 'autocomplete-list';
        this.container.appendChild(this.list);

        // 绑定事件
        this.input.addEventListener('input', () => this.handleInput());
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('blur', () => setTimeout(() => this.hide(), 200));
    }

    setData(data) {
        this.data = data;
    }

    handleInput() {
        const value = this.input.value.toLowerCase();
        if (!value) {
            this.hide();
            return;
        }

        const matches = this.data.filter(item =>
            item.toLowerCase().includes(value)
        );

        this.render(matches);
    }

    handleKeydown(e) {
        const items = this.list.querySelectorAll('.autocomplete-item');

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
                this.updateSelection(items);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection(items);
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
                    this.select(items[this.selectedIndex].textContent);
                }
                break;
            case 'Escape':
                this.hide();
                break;
        }
    }

    updateSelection(items) {
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedIndex);
        });
    }

    render(matches) {
        if (matches.length === 0) {
            this.hide();
            return;
        }

        this.list.innerHTML = matches.map(match => `
            <div class="autocomplete-item">${escapeHtml(match)}</div>
        `).join('');

        this.list.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => this.select(item.textContent));
        });

        this.list.classList.add('active');
        this.selectedIndex = -1;
    }

    select(value) {
        this.input.value = value;
        this.hide();
        this.onSelect(value);
    }

    hide() {
        this.list.classList.remove('active');
        this.selectedIndex = -1;
    }
}

// 模态框组件
class Modal {
    constructor(id) {
        this.element = document.getElementById(id);
        if (!this.element) return;

        this.overlay = this.element.querySelector('.modal-overlay') || this.element;
        this.closeBtn = this.element.querySelector('.modal-close');

        this.closeBtn?.addEventListener('click', () => this.hide());
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) this.hide();
        });
    }

    show() {
        this.overlay.classList.add('active');
    }

    hide() {
        this.overlay.classList.remove('active');
    }
}

// ========================================
// 导航功能
// ========================================
function initNavigation() {
    const navbarToggle = document.getElementById('navbarToggle');
    const sidebar = document.getElementById('sidebar');

    navbarToggle?.addEventListener('click', () => {
        sidebar.classList.toggle('active');
    });
}

// ========================================
// 初始化
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
});

// 导出全局函数和类
window.API = API;
window.showToast = showToast;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.escapeHtml = escapeHtml;
window.formatNumber = formatNumber;
window.formatRate = formatRate;
window.Autocomplete = Autocomplete;
window.Modal = Modal;
window.AppState = AppState;
