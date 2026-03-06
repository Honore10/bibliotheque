const express = require('express');
const { getDb } = require('../database');
const { authenticate } = require('../middleware/auth');

const router = express.Router();

// GET /api/emprunts - list user's borrowings
router.get('/', authenticate, (req, res) => {
  try {
    const db = getDb();
    const emprunts = db.prepare(`
      SELECT e.id, e.borrowed_at, e.due_date, e.returned_at, e.status,
             b.id as book_id, b.title, b.author, b.isbn, b.genre
      FROM emprunts e
      JOIN books b ON e.book_id = b.id
      WHERE e.user_id = ?
      ORDER BY e.borrowed_at DESC
    `).all(req.user.id);
    return res.json(emprunts);
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

// POST /api/emprunts - borrow a book
router.post('/', authenticate, (req, res) => {
  try {
    const { bookId } = req.body;
    if (!bookId) {
      return res.status(400).json({ error: 'L\'identifiant du livre est requis' });
    }

    const db = getDb();
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(bookId);
    if (!book) {
      return res.status(404).json({ error: 'Livre non trouvé' });
    }
    if (book.available_copies < 1) {
      return res.status(400).json({ error: 'Aucune copie disponible pour ce livre' });
    }

    const existing = db.prepare(`
      SELECT id FROM emprunts
      WHERE user_id = ? AND book_id = ? AND status = 'active'
    `).get(req.user.id, bookId);
    if (existing) {
      return res.status(409).json({ error: 'Vous avez déjà un emprunt actif pour ce livre' });
    }

    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + 14);
    const dueDateStr = dueDate.toISOString().replace('T', ' ').substring(0, 19);

    const borrowEmprunt = db.transaction(() => {
      db.prepare('UPDATE books SET available_copies = available_copies - 1 WHERE id = ?').run(bookId);

      db.prepare(`
        UPDATE reservations SET status = 'fulfilled'
        WHERE user_id = ? AND book_id = ? AND status = 'active'
      `).run(req.user.id, bookId);

      const result = db.prepare(`
        INSERT INTO emprunts (user_id, book_id, due_date, status)
        VALUES (?, ?, ?, 'active')
      `).run(req.user.id, bookId, dueDateStr);

      return result.lastInsertRowid;
    });

    const empruntId = borrowEmprunt();

    const emprunt = db.prepare(`
      SELECT e.id, e.borrowed_at, e.due_date, e.returned_at, e.status,
             b.id as book_id, b.title, b.author, b.isbn, b.genre
      FROM emprunts e
      JOIN books b ON e.book_id = b.id
      WHERE e.id = ?
    `).get(empruntId);

    return res.status(201).json(emprunt);
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

// PUT /api/emprunts/:id/retour - return a book
router.put('/:id/retour', authenticate, (req, res) => {
  try {
    const db = getDb();
    const emprunt = db.prepare('SELECT * FROM emprunts WHERE id = ?').get(req.params.id);
    if (!emprunt) {
      return res.status(404).json({ error: 'Emprunt non trouvé' });
    }
    if (emprunt.user_id !== req.user.id && req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Accès refusé' });
    }
    if (emprunt.status !== 'active') {
      return res.status(400).json({ error: 'Ce livre a déjà été retourné' });
    }

    const returnedAt = new Date().toISOString().replace('T', ' ').substring(0, 19);

    db.transaction(() => {
      db.prepare('UPDATE books SET available_copies = available_copies + 1 WHERE id = ?').run(emprunt.book_id);
      db.prepare(`
        UPDATE emprunts SET status = 'returned', returned_at = ? WHERE id = ?
      `).run(returnedAt, req.params.id);
    })();

    const updated = db.prepare(`
      SELECT e.id, e.borrowed_at, e.due_date, e.returned_at, e.status,
             b.id as book_id, b.title, b.author, b.isbn, b.genre
      FROM emprunts e
      JOIN books b ON e.book_id = b.id
      WHERE e.id = ?
    `).get(req.params.id);

    return res.json(updated);
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

module.exports = router;
