/* ==============================================
   Bibliothèque Numérique - Frontend Application
   ============================================== */

const API_BASE = '/api';

// ── State ─────────────────────────────────────
let token = localStorage.getItem('token');
let currentUser = JSON.parse(localStorage.getItem('user') || 'null');

// ── Utilities ─────────────────────────────────
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

async function apiFetch(endpoint, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw { status: res.status, message: data.error || 'Erreur inconnue' };
  return data;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

function isOverdue(dueDateStr) {
  return dueDateStr && new Date(dueDateStr) < new Date();
}

// ── Navigation ────────────────────────────────
function switchTab(tabName) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`tab-${tabName}`).classList.add('active');
  document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

  if (tabName === 'catalogue') loadBooks();
  if (tabName === 'reservations') loadReservations();
  if (tabName === 'emprunts') loadEmprunts();
  if (tabName === 'auth') renderAuthSection();
}

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ── Auth Logic ────────────────────────────────
function renderAuthSection() {
  const loginSection = document.getElementById('login-section');
  const registerSection = document.getElementById('register-section');
  const profileSection = document.getElementById('profile-section');
  const authNavBtn = document.getElementById('auth-nav-btn');

  if (currentUser) {
    loginSection.classList.add('hidden');
    registerSection.classList.add('hidden');
    profileSection.classList.remove('hidden');
    authNavBtn.textContent = currentUser.name.split(' ')[0];
    renderProfile();
  } else {
    loginSection.classList.remove('hidden');
    registerSection.classList.add('hidden');
    profileSection.classList.add('hidden');
    authNavBtn.textContent = 'Connexion';
  }
}

function renderProfile() {
  const container = document.getElementById('profile-info');
  const initial = currentUser.name.charAt(0).toUpperCase();
  const roleBadge = currentUser.role === 'admin'
    ? '<span class="badge badge-genre">Administrateur</span>'
    : '<span class="badge badge-available">Membre</span>';

  container.innerHTML = `
    <div class="profile-avatar">${initial}</div>
    <div class="profile-field">
      <label>Nom</label>
      <span>${currentUser.name}</span>
    </div>
    <div class="profile-field">
      <label>Email</label>
      <span>${currentUser.email}</span>
    </div>
    <div class="profile-field">
      <label>Rôle</label>
      <span>${roleBadge}</span>
    </div>
    <div class="profile-field">
      <label>Membre depuis</label>
      <span>${formatDate(currentUser.created_at)}</span>
    </div>
  `;
}

document.getElementById('show-register').addEventListener('click', e => {
  e.preventDefault();
  document.getElementById('login-section').classList.add('hidden');
  document.getElementById('register-section').classList.remove('hidden');
});

document.getElementById('show-login').addEventListener('click', e => {
  e.preventDefault();
  document.getElementById('register-section').classList.add('hidden');
  document.getElementById('login-section').classList.remove('hidden');
});

document.getElementById('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  try {
    const data = await apiFetch('/users/login', {
      method: 'POST',
      body: JSON.stringify({ email: form.email.value, password: form.password.value })
    });
    token = data.token;
    currentUser = data.user;
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(currentUser));
    showToast(`Bienvenue, ${currentUser.name} !`, 'success');
    renderAuthSection();
    switchTab('catalogue');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
  }
});

document.getElementById('register-form').addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  try {
    const data = await apiFetch('/users/register', {
      method: 'POST',
      body: JSON.stringify({ name: form.name.value, email: form.email.value, password: form.password.value })
    });
    token = data.token;
    currentUser = data.user;
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(currentUser));
    showToast(`Compte créé ! Bienvenue, ${currentUser.name} !`, 'success');
    renderAuthSection();
    switchTab('catalogue');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
  }
});

document.getElementById('logout-btn').addEventListener('click', () => {
  token = null;
  currentUser = null;
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  showToast('Déconnexion réussie', 'info');
  renderAuthSection();
  switchTab('catalogue');
});

// ── Books ──────────────────────────────────────
async function loadBooks(search = '') {
  const grid = document.getElementById('books-grid');
  grid.innerHTML = '<div class="loading">Chargement des livres...</div>';

  const adminPanel = document.getElementById('admin-add-book-panel');
  if (currentUser && currentUser.role === 'admin') {
    adminPanel.classList.remove('hidden');
  } else {
    adminPanel.classList.add('hidden');
  }

  try {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    const books = await apiFetch(`/books${query}`);
    if (books.length === 0) {
      grid.innerHTML = `
        <div class="empty-state" style="grid-column: 1/-1;">
          <div class="empty-icon">📭</div>
          <p>Aucun livre trouvé</p>
        </div>`;
      return;
    }
    grid.innerHTML = books.map(renderBookCard).join('');
  } catch (err) {
    grid.innerHTML = `<div class="empty-state" style="grid-column: 1/-1;">❌ Erreur de chargement</div>`;
  }
}

function renderBookCard(book) {
  const available = book.available_copies > 0;
  const availBadge = available
    ? `<span class="badge badge-available">${book.available_copies} dispo.</span>`
    : `<span class="badge badge-unavailable">Indisponible</span>`;
  const genreBadge = book.genre ? `<span class="badge badge-genre">${book.genre}</span>` : '';
  const yearBadge = book.published_year ? `<span class="badge badge-year">${book.published_year}</span>` : '';

  const coverEmojis = ['📘', '📗', '📙', '📕', '📓'];
  const emoji = coverEmojis[book.id % coverEmojis.length];

  const adminActions = currentUser && currentUser.role === 'admin' ? `
    <button class="btn btn-outline" onclick="event.stopPropagation(); openEditModal(${book.id})">✏️ Modifier</button>
    <button class="btn btn-danger" onclick="event.stopPropagation(); deleteBook(${book.id})">🗑️ Supprimer</button>
  ` : '';

  return `
    <div class="book-card" onclick="openBookModal(${book.id})">
      <div class="book-cover">${emoji}</div>
      <div class="book-title">${book.title}</div>
      <div class="book-author">par ${book.author}</div>
      <div class="book-meta">${genreBadge}${yearBadge}${availBadge}</div>
      <div class="book-actions" onclick="event.stopPropagation()">
        ${currentUser ? `
          <button class="btn btn-success" onclick="borrowBook(${book.id})" ${!available ? 'disabled' : ''}>
            📖 Emprunter
          </button>
          <button class="btn btn-warning" onclick="reserveBook(${book.id})">
            🔖 Réserver
          </button>
        ` : `<button class="btn btn-outline" onclick="switchTab('auth')">Connectez-vous</button>`}
        ${adminActions}
      </div>
    </div>`;
}

// ── Search ────────────────────────────────────
document.getElementById('search-btn').addEventListener('click', () => {
  loadBooks(document.getElementById('search-input').value);
});

document.getElementById('search-input').addEventListener('keypress', e => {
  if (e.key === 'Enter') loadBooks(e.target.value);
});

// ── Book Modal ────────────────────────────────
async function openBookModal(bookId) {
  const overlay = document.getElementById('modal-overlay');
  const content = document.getElementById('modal-content');
  overlay.classList.remove('hidden');
  content.innerHTML = '<div class="loading">Chargement...</div>';

  try {
    const book = await apiFetch(`/books/${bookId}`);
    const available = book.available_copies > 0;
    const availBadge = available
      ? `<span class="badge badge-available">${book.available_copies} / ${book.total_copies} disponible(s)</span>`
      : `<span class="badge badge-unavailable">Indisponible (0 / ${book.total_copies})</span>`;

    content.innerHTML = `
      <div class="modal-book-title">${book.title}</div>
      <div class="modal-book-author">par ${book.author}</div>
      <div class="modal-book-meta">
        ${book.genre ? `<span class="badge badge-genre">${book.genre}</span>` : ''}
        ${book.published_year ? `<span class="badge badge-year">${book.published_year}</span>` : ''}
        ${availBadge}
      </div>
      ${book.description ? `<p class="modal-description">${book.description}</p>` : ''}
      <div class="modal-book-details">
        <dl>
          ${book.isbn ? `<dt>ISBN</dt><dd>${book.isbn}</dd>` : ''}
          <dt>Copies totales</dt><dd>${book.total_copies}</dd>
          <dt>Disponibles</dt><dd>${book.available_copies}</dd>
        </dl>
      </div>
      <div class="modal-actions">
        ${currentUser ? `
          <button class="btn btn-success" onclick="borrowBook(${book.id}); closeModal()" ${!available ? 'disabled' : ''}>
            📖 Emprunter
          </button>
          <button class="btn btn-warning" onclick="reserveBook(${book.id}); closeModal()">
            🔖 Réserver
          </button>
        ` : `<button class="btn btn-primary" onclick="closeModal(); switchTab('auth')">Se connecter pour emprunter</button>`}
      </div>
    `;
  } catch (err) {
    content.innerHTML = `<p>Erreur de chargement du livre.</p>`;
  }
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

document.getElementById('modal-close-btn').addEventListener('click', closeModal);
document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
});

// ── Borrow & Reserve ──────────────────────────
async function borrowBook(bookId) {
  if (!currentUser) { switchTab('auth'); return; }
  try {
    await apiFetch('/emprunts', { method: 'POST', body: JSON.stringify({ bookId }) });
    showToast('Livre emprunté avec succès ! Date de retour dans 14 jours.', 'success');
    loadBooks(document.getElementById('search-input').value);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function reserveBook(bookId) {
  if (!currentUser) { switchTab('auth'); return; }
  try {
    await apiFetch('/reservations', { method: 'POST', body: JSON.stringify({ bookId }) });
    showToast('Réservation effectuée avec succès !', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ── Add Book (Admin) ──────────────────────────
document.getElementById('add-book-form').addEventListener('submit', async e => {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  try {
    const formData = {
      title: form.title.value,
      author: form.author.value,
      isbn: form.isbn.value || undefined,
      genre: form.genre.value || undefined,
      publishedYear: form.publishedYear.value ? parseInt(form.publishedYear.value) : undefined,
      totalCopies: parseInt(form.totalCopies.value) || 1,
      description: form.description.value || undefined
    };
    await apiFetch('/books', { method: 'POST', body: JSON.stringify(formData) });
    showToast('Livre ajouté avec succès !', 'success');
    form.reset();
    form.totalCopies.value = '1';
    loadBooks();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
  }
});

// ── Delete Book (Admin) ───────────────────────
async function deleteBook(bookId) {
  if (!confirm('Êtes-vous sûr de vouloir supprimer ce livre ?')) return;
  try {
    await apiFetch(`/books/${bookId}`, { method: 'DELETE' });
    showToast('Livre supprimé avec succès.', 'success');
    loadBooks(document.getElementById('search-input').value);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ── Edit Book Modal (Admin) ───────────────────
async function openEditModal(bookId) {
  const overlay = document.getElementById('modal-overlay');
  const content = document.getElementById('modal-content');
  overlay.classList.remove('hidden');

  try {
    const book = await apiFetch(`/books/${bookId}`);
    content.innerHTML = `
      <h3 style="margin-bottom:1.25rem;font-size:1.2rem;">✏️ Modifier le livre</h3>
      <form id="edit-book-form" class="book-form">
        <div class="form-row">
          <input type="text" name="title" placeholder="Titre *" value="${book.title}" required />
          <input type="text" name="author" placeholder="Auteur *" value="${book.author}" required />
        </div>
        <div class="form-row">
          <input type="text" name="isbn" placeholder="ISBN" value="${book.isbn || ''}" />
          <input type="text" name="genre" placeholder="Genre" value="${book.genre || ''}" />
        </div>
        <div class="form-row">
          <input type="number" name="publishedYear" placeholder="Année" value="${book.published_year || ''}" min="1" max="2099" />
          <input type="number" name="totalCopies" placeholder="Copies" value="${book.total_copies}" min="1" />
        </div>
        <textarea name="description" placeholder="Description">${book.description || ''}</textarea>
        <div style="display:flex;gap:.5rem;margin-top:.25rem;">
          <button type="submit" class="btn btn-primary">💾 Enregistrer</button>
          <button type="button" class="btn btn-outline" onclick="closeModal()">Annuler</button>
        </div>
      </form>
    `;

    document.getElementById('edit-book-form').addEventListener('submit', async ev => {
      ev.preventDefault();
      const form = ev.target;
      const btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      try {
        await apiFetch(`/books/${bookId}`, {
          method: 'PUT',
          body: JSON.stringify({
            title: form.title.value,
            author: form.author.value,
            isbn: form.isbn.value || undefined,
            genre: form.genre.value || undefined,
            publishedYear: form.publishedYear.value ? parseInt(form.publishedYear.value) : undefined,
            totalCopies: parseInt(form.totalCopies.value) || 1,
            description: form.description.value || undefined
          })
        });
        showToast('Livre mis à jour avec succès !', 'success');
        closeModal();
        loadBooks(document.getElementById('search-input').value);
      } catch (err) {
        showToast(err.message, 'error');
        btn.disabled = false;
      }
    });
  } catch (err) {
    content.innerHTML = `<p>Erreur de chargement.</p>`;
  }
}

// ── Reservations ──────────────────────────────
async function loadReservations() {
  const list = document.getElementById('reservations-list');
  if (!currentUser) {
    list.innerHTML = '<div class="auth-required">🔒 Connectez-vous pour voir vos réservations.</div>';
    return;
  }

  list.innerHTML = '<div class="loading">Chargement...</div>';
  try {
    const reservations = await apiFetch('/reservations');
    if (reservations.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔖</div>
          <p>Vous n'avez aucune réservation.</p>
        </div>`;
      return;
    }
    list.innerHTML = reservations.map(r => `
      <div class="item-card">
        <div class="item-icon">🔖</div>
        <div class="item-body">
          <div class="item-title">${r.title}</div>
          <div class="item-subtitle">par ${r.author}</div>
          <div class="item-dates">
            <span>Réservé le ${formatDate(r.reserved_at)}</span>
            ${r.genre ? `<span>Genre : ${r.genre}</span>` : ''}
          </div>
          <div class="item-actions">
            ${r.status === 'active'
              ? `<span class="status-active">● Active</span>
                 <button class="btn btn-danger" onclick="cancelReservation(${r.id})">Annuler</button>`
              : r.status === 'fulfilled'
                ? `<span class="status-returned">✔ Réalisée</span>`
                : `<span class="status-cancelled">✕ Annulée</span>`
            }
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    list.innerHTML = `<div class="empty-state">❌ Erreur de chargement</div>`;
  }
}

async function cancelReservation(id) {
  if (!confirm('Annuler cette réservation ?')) return;
  try {
    await apiFetch(`/reservations/${id}`, { method: 'DELETE' });
    showToast('Réservation annulée.', 'success');
    loadReservations();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ── Emprunts ──────────────────────────────────
async function loadEmprunts() {
  const list = document.getElementById('emprunts-list');
  if (!currentUser) {
    list.innerHTML = '<div class="auth-required">🔒 Connectez-vous pour voir vos emprunts.</div>';
    return;
  }

  list.innerHTML = '<div class="loading">Chargement...</div>';
  try {
    const emprunts = await apiFetch('/emprunts');
    if (emprunts.length === 0) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">📖</div>
          <p>Vous n'avez aucun emprunt.</p>
        </div>`;
      return;
    }
    list.innerHTML = emprunts.map(e => {
      const overdue = e.status === 'active' && isOverdue(e.due_date);
      const statusHtml = e.status === 'active'
        ? (overdue
            ? `<span class="status-overdue">⚠ En retard</span>`
            : `<span class="status-active">● En cours</span>`)
        : `<span class="status-returned">✔ Retourné le ${formatDate(e.returned_at)}</span>`;

      return `
        <div class="item-card">
          <div class="item-icon">📖</div>
          <div class="item-body">
            <div class="item-title">${e.title}</div>
            <div class="item-subtitle">par ${e.author}</div>
            <div class="item-dates">
              <span>Emprunté le ${formatDate(e.borrowed_at)}</span>
              <span>Retour prévu : ${formatDate(e.due_date)}</span>
            </div>
            <div class="item-actions">
              ${statusHtml}
              ${e.status === 'active'
                ? `<button class="btn btn-primary" onclick="returnBook(${e.id})">↩️ Retourner</button>`
                : ''}
            </div>
          </div>
        </div>`;
    }).join('');
  } catch (err) {
    list.innerHTML = `<div class="empty-state">❌ Erreur de chargement</div>`;
  }
}

async function returnBook(empruntId) {
  if (!confirm('Confirmer le retour de ce livre ?')) return;
  try {
    await apiFetch(`/emprunts/${empruntId}/retour`, { method: 'PUT' });
    showToast('Livre retourné avec succès !', 'success');
    loadEmprunts();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ── Init ──────────────────────────────────────
renderAuthSection();
loadBooks();
