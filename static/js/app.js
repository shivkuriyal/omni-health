/**
 * OmniHealth-Rec — Core JavaScript Module
 * Authentication, API calls, toast notifications, and shared utilities.
 */

const API = {
    baseUrl: '',

    /** Get stored auth token */
    getToken() {
        return localStorage.getItem('oh_token');
    },

    /** Get current user data */
    getUser() {
        const data = localStorage.getItem('oh_user');
        return data ? JSON.parse(data) : null;
    },

    /** Get current role */
    getRole() {
        return localStorage.getItem('oh_role') || 'patient';
    },

    /** Save auth data */
    saveAuth(token, user, role) {
        localStorage.setItem('oh_token', token);
        localStorage.setItem('oh_user', JSON.stringify(user));
        localStorage.setItem('oh_role', role);
    },

    /** Clear auth data and redirect */
    logout() {
        localStorage.removeItem('oh_token');
        localStorage.removeItem('oh_user');
        localStorage.removeItem('oh_role');
        window.location.href = '/login';
    },

    /** Make authenticated API request */
    async request(url, options = {}) {
        const token = this.getToken();
        const headers = {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...(options.headers || {}),
        };

        try {
            const response = await fetch(`${this.baseUrl}${url}`, {
                ...options,
                headers,
            });

            const data = await response.json();

            if (response.status === 401) {
                this.logout();
                return null;
            }

            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }

            return data;
        } catch (err) {
            console.error('API Error:', err);
            Toast.show(err.message, 'error');
            throw err;
        }
    },

    get(url) { return this.request(url); },
    post(url, body) { return this.request(url, { method: 'POST', body: JSON.stringify(body) }); },
    put(url, body) { return this.request(url, { method: 'PUT', body: JSON.stringify(body) }); },
    delete(url) { return this.request(url, { method: 'DELETE' }); },
};


/**
 * Toast notification system
 */
const Toast = {
    container: null,

    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },

    show(message, type = 'info', duration = 4000) {
        this.init();

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ',
        };

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span style="font-weight:700; font-size:1.1rem;">${icons[type] || 'ℹ'}</span>
            <span>${message}</span>
        `;

        this.container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(40px)';
            toast.style.transition = 'all 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },
};


/**
 * Modal management
 */
const Modal = {
    open(id) {
        const overlay = document.getElementById(id);
        if (overlay) overlay.classList.add('active');
    },

    close(id) {
        const overlay = document.getElementById(id);
        if (overlay) overlay.classList.remove('active');
    },

    closeAll() {
        document.querySelectorAll('.modal-overlay.active').forEach(el => {
            el.classList.remove('active');
        });
    },
};

// Close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});


/**
 * Utility: format date for display
 */
function formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatDateTime(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 30) return `${days}d ago`;
    return formatDate(dateStr);
}


/**
 * Color palette for avatars
 */
const AVATAR_COLORS = [
    '#2d8cff', '#14b8a6', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#06b6d4', '#22c55e',
];

function getAvatarColor(name) {
    let hash = 0;
    for (let i = 0; i < (name || '').length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function getInitials(name) {
    if (!name) return '?';
    return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
}


/**
 * Severity badge helper
 */
function severityBadge(severity) {
    const map = {
        low: 'badge-gray',
        moderate: 'badge-warning',
        high: 'badge-danger',
        critical: 'badge-danger',
    };
    return `<span class="badge ${map[severity] || 'badge-gray'}">${severity || 'Low'}</span>`;
}

/**
 * Record type icon
 */
function recordTypeIcon(type) {
    const icons = {
        diagnosis: '🩺',
        prescription: '💊',
        lab: '🧪',
        surgery: '🔪',
        vaccination: '💉',
        general: '📋',
    };
    return icons[type] || '📋';
}


/**
 * Auth guard — redirect to login if not authenticated
 */
function requireAuth(allowedRoles = []) {
    const token = API.getToken();
    const role = API.getRole();

    if (!token) {
        window.location.href = '/login';
        return false;
    }

    if (allowedRoles.length > 0 && !allowedRoles.includes(role)) {
        Toast.show('Access denied for your role', 'error');
        window.location.href = '/dashboard';
        return false;
    }

    return true;
}


/**
 * Mobile sidebar toggle
 */
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) sidebar.classList.toggle('open');
}
