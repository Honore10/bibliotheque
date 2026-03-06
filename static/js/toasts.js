// Toast notification system
function toastContainer() {
  return {
    toasts: [],
    id: 0,
    init() {
      // Load Django messages on page load
      if (window.DJ_MESSAGES && Array.isArray(window.DJ_MESSAGES)) {
        window.DJ_MESSAGES.forEach(m => {
          this.add(m.message, m.level);
        });
      }
    },
    add(message, level = 'info') {
      const toast = {
        id: this.id++,
        message: message,
        level: level
      };
      this.toasts.push(toast);
      // Auto-remove after 5 seconds
      setTimeout(() => {
        this.remove(toast.id);
      }, 5000);
    },
    remove(id) {
      this.toasts = this.toasts.filter(t => t.id !== id);
    }
  };
}
