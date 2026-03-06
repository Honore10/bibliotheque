const express = require('express');
const { getDb } = require('../database');
const { authenticate, requireAdmin } = require('../middleware/auth');

const router = express.Router();

// GET /api/books
router.get('/', (req, res) => {
  try {
    const db = getDb();
    const { search } = req.query;
    let books;
    if (search) {
      const term = `%${search}%`;
      books = db.prepare(`
        SELECT * FROM books
        WHERE title LIKE ? OR author LIKE ? OR genre LIKE ? OR isbn LIKE ?
        ORDER BY title ASC
      `).all(term, term, term, term);
    } else {
      books = db.prepare('SELECT * FROM books ORDER BY title ASC').all();
    }
    return res.json(books);
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

// GET /api/books/:id
router.get('/:id', (req, res) => {
  try {
    const db = getDb();
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!book) {
      return res.status(404).json({ error: 'Livre non trouvé' });
    }
    return res.json(book);
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

// POST /api/books (admin only)
router.post('/', authenticate, requireAdmin, (req, res) => {
  try {
    const { title, author, isbn, description, genre, publishedYear, totalCopies } = req.body;
    if (!title || !author) {
      return res.status(400).json({ error: 'Le titre et l\'auteur sont requis' });
    }

    const copies = totalCopies !== undefined ? parseInt(totalCopies, 10) : 1;
    if (isNaN(copies) || copies < 1) {
      return res.status(400).json({ error: 'Le nombre de copies doit être un entier positif' });
    }

    const db = getDb();

    if (isbn) {
      const existing = db.prepare('SELECT id FROM books WHERE isbn = ?').get(isbn);
      if (existing) {
        return res.status(409).json({ error: 'Un livre avec cet ISBN existe déjà' });
      }
    }

    const result = db.prepare(`
      INSERT INTO books (title, author, isbn, description, genre, published_year, total_copies, available_copies)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(title, author, isbn || null, description || null, genre || null, publishedYear || null, copies, copies);

    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(result.lastInsertRowid);
    return res.status(201).json(book);
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

// PUT /api/books/:id (admin only)
router.put('/:id', authenticate, requireAdmin, (req, res) => {
  try {
    const db = getDb();
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!book) {
      return res.status(404).json({ error: 'Livre non trouvé' });
    }

    const { title, author, isbn, description, genre, publishedYear, totalCopies } = req.body;

    const newTitle = title !== undefined ? title : book.title;
    const newAuthor = author !== undefined ? author : book.author;
    const newIsbn = isbn !== undefined ? isbn : book.isbn;
    const newDescription = description !== undefined ? description : book.description;
    const newGenre = genre !== undefined ? genre : book.genre;
    const newPublishedYear = publishedYear !== undefined ? publishedYear : book.published_year;

    let newTotalCopies = book.total_copies;
    let newAvailableCopies = book.available_copies;
    if (totalCopies !== undefined) {
      const parsed = parseInt(totalCopies, 10);
      if (isNaN(parsed) || parsed < 1) {
        return res.status(400).json({ error: 'Le nombre de copies doit être un entier positif' });
      }
      const diff = parsed - book.total_copies;
      newTotalCopies = parsed;
      newAvailableCopies = Math.max(0, book.available_copies + diff);
    }

    if (isbn && isbn !== book.isbn) {
      const existing = db.prepare('SELECT id FROM books WHERE isbn = ? AND id != ?').get(isbn, req.params.id);
      if (existing) {
        return res.status(409).json({ error: 'Un livre avec cet ISBN existe déjà' });
      }
    }

    db.prepare(`
      UPDATE books
      SET title = ?, author = ?, isbn = ?, description = ?, genre = ?,
          published_year = ?, total_copies = ?, available_copies = ?
      WHERE id = ?
    `).run(newTitle, newAuthor, newIsbn, newDescription, newGenre, newPublishedYear, newTotalCopies, newAvailableCopies, req.params.id);

    const updated = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    return res.json(updated);
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

// DELETE /api/books/:id (admin only)
router.delete('/:id', authenticate, requireAdmin, (req, res) => {
  try {
    const db = getDb();
    const book = db.prepare('SELECT * FROM books WHERE id = ?').get(req.params.id);
    if (!book) {
      return res.status(404).json({ error: 'Livre non trouvé' });
    }

    db.prepare('DELETE FROM emprunts WHERE book_id = ?').run(req.params.id);
    db.prepare('DELETE FROM reservations WHERE book_id = ?').run(req.params.id);
    db.prepare('DELETE FROM books WHERE id = ?').run(req.params.id);

    return res.json({ message: 'Livre supprimé avec succès' });
  } catch (err) {
    return res.status(500).json({ error: 'Erreur interne du serveur' });
  }
});

module.exports = router;
