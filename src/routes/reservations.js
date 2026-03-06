const express = require('express');
const { getDb } = require('../database');
const { authenticate } = require('../middleware/auth');

const router = express.Router();

// GET /api/reservations - list user's reservations
router.get('/', authenticate, (req, res) => {
  try {
    const db = getDb();
    const reservations = db.prepare(`
      SELECT r.id, r.status, r.reserved_at,
             b.id as book_id, b.title, b.author, b.isbn, b.genre
      FROM reservations r
      JOIN books b ON r.book_id = b.id
      WHERE r.user_id = ?
      ORDER BY r.reserved_at DESC
    `).all(req.user.id);
    return res.json(reservations);
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

// POST /api/reservations - create reservation
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

    const existing = db.prepare(`
      SELECT id FROM reservations
      WHERE user_id = ? AND book_id = ? AND status = 'active'
    `).get(req.user.id, bookId);
    if (existing) {
      return res.status(409).json({ error: 'Vous avez déjà une réservation active pour ce livre' });
    }

    const activeEmprunt = db.prepare(`
      SELECT id FROM emprunts
      WHERE user_id = ? AND book_id = ? AND status = 'active'
    `).get(req.user.id, bookId);
    if (activeEmprunt) {
      return res.status(409).json({ error: 'Vous avez déjà emprunté ce livre' });
    }

    const result = db.prepare(`
      INSERT INTO reservations (user_id, book_id, status)
      VALUES (?, ?, 'active')
    `).run(req.user.id, bookId);

    const reservation = db.prepare(`
      SELECT r.id, r.status, r.reserved_at,
             b.id as book_id, b.title, b.author, b.isbn, b.genre
      FROM reservations r
      JOIN books b ON r.book_id = b.id
      WHERE r.id = ?
    `).get(result.lastInsertRowid);

    return res.status(201).json(reservation);
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

// DELETE /api/reservations/:id - cancel reservation
router.delete('/:id', authenticate, (req, res) => {
  try {
    const db = getDb();
    const reservation = db.prepare('SELECT * FROM reservations WHERE id = ?').get(req.params.id);
    if (!reservation) {
      return res.status(404).json({ error: 'Réservation non trouvée' });
    }
    if (reservation.user_id !== req.user.id && req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Accès refusé' });
    }
    if (reservation.status !== 'active') {
      return res.status(400).json({ error: 'Cette réservation n\'est plus active' });
    }

    db.prepare("UPDATE reservations SET status = 'cancelled' WHERE id = ?").run(req.params.id);
    return res.json({ message: 'Réservation annulée avec succès' });
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

module.exports = router;
