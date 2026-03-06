const Database = require('better-sqlite3');
const path = require('path');
const bcrypt = require('bcryptjs');

const DB_PATH = process.env.NODE_ENV === 'test'
  ? ':memory:'
  : path.join(__dirname, '../bibliotheque.db');

let db;

function getDb() {
  return db;
}

function initDatabase() {
  db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'member',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS books (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      author TEXT NOT NULL,
      isbn TEXT UNIQUE,
      description TEXT,
      genre TEXT,
      published_year INTEGER,
      total_copies INTEGER NOT NULL DEFAULT 1,
      available_copies INTEGER NOT NULL DEFAULT 1,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS reservations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      book_id INTEGER NOT NULL,
      status TEXT NOT NULL DEFAULT 'active',
      reserved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (book_id) REFERENCES books(id)
    );

    CREATE TABLE IF NOT EXISTS emprunts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      book_id INTEGER NOT NULL,
      borrowed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      due_date DATETIME NOT NULL,
      returned_at DATETIME,
      status TEXT NOT NULL DEFAULT 'active',
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (book_id) REFERENCES books(id)
    );
  `);

  seedData();
  return db;
}

function seedData() {
  const adminExists = db.prepare("SELECT id FROM users WHERE email = 'admin@bibliotheque.fr'").get();
  if (!adminExists) {
    const hashedPassword = bcrypt.hashSync('admin123', 10);
    db.prepare(`
      INSERT INTO users (name, email, password, role)
      VALUES ('Administrateur', 'admin@bibliotheque.fr', ?, 'admin')
    `).run(hashedPassword);
  }

  const bookCount = db.prepare('SELECT COUNT(*) as count FROM books').get();
  if (bookCount.count === 0) {
    const books = [
      {
        title: 'Le Petit Prince',
        author: 'Antoine de Saint-Exupéry',
        isbn: '978-2-07-040850-4',
        description: 'Un aviateur tombe en panne dans le désert et rencontre un petit prince venu d\'une autre planète.',
        genre: 'Fiction',
        published_year: 1943,
        total_copies: 3,
        available_copies: 3
      },
      {
        title: 'Les Misérables',
        author: 'Victor Hugo',
        isbn: '978-2-07-040951-8',
        description: 'L\'histoire de Jean Valjean, ancien forçat, qui cherche sa rédemption dans la France du XIXe siècle.',
        genre: 'Roman historique',
        published_year: 1862,
        total_copies: 2,
        available_copies: 2
      },
      {
        title: 'L\'Étranger',
        author: 'Albert Camus',
        isbn: '978-2-07-036024-5',
        description: 'Meursault, un Français vivant en Algérie, tue un Arabe sur la plage et fait face à la justice.',
        genre: 'Roman philosophique',
        published_year: 1942,
        total_copies: 4,
        available_copies: 4
      },
      {
        title: 'Madame Bovary',
        author: 'Gustave Flaubert',
        isbn: '978-2-07-041046-0',
        description: 'Emma Bovary, épouse d\'un médecin de campagne, rêve d\'une vie plus romantique et passionnée.',
        genre: 'Roman réaliste',
        published_year: 1857,
        total_copies: 2,
        available_copies: 2
      },
      {
        title: 'Germinal',
        author: 'Émile Zola',
        isbn: '978-2-07-040032-4',
        description: 'La vie des mineurs du Nord de la France au XIXe siècle et leur lutte pour de meilleures conditions.',
        genre: 'Naturalisme',
        published_year: 1885,
        total_copies: 3,
        available_copies: 3
      },
      {
        title: 'La Peste',
        author: 'Albert Camus',
        isbn: '978-2-07-036024-6',
        description: 'Une ville algérienne est frappée par une épidémie de peste, mettant à l\'épreuve ses habitants.',
        genre: 'Roman philosophique',
        published_year: 1947,
        total_copies: 2,
        available_copies: 2
      },
      {
        title: 'Vingt mille lieues sous les mers',
        author: 'Jules Verne',
        isbn: '978-2-07-041219-8',
        description: 'Le professeur Aronnax explore les fonds marins à bord du Nautilus, sous-marin du mystérieux capitaine Nemo.',
        genre: 'Science-fiction',
        published_year: 1870,
        total_copies: 2,
        available_copies: 2
      },
      {
        title: 'Le Rouge et le Noir',
        author: 'Stendhal',
        isbn: '978-2-07-040665-4',
        description: 'Julien Sorel, jeune homme ambitieux d\'origine modeste, cherche à s\'élever dans la société.',
        genre: 'Roman réaliste',
        published_year: 1830,
        total_copies: 1,
        available_copies: 1
      },
      {
        title: 'Notre-Dame de Paris',
        author: 'Victor Hugo',
        isbn: '978-2-07-040659-3',
        description: 'L\'histoire de Quasimodo, le sonneur de cloches bossu de Notre-Dame, et de sa passion pour Esmeralda.',
        genre: 'Roman historique',
        published_year: 1831,
        total_copies: 2,
        available_copies: 2
      },
      {
        title: 'Voyage au bout de la nuit',
        author: 'Louis-Ferdinand Céline',
        isbn: '978-2-07-036028-3',
        description: 'Ferdinand Bardamu traverse la guerre, les colonies africaines et l\'Amérique dans un voyage désenchanté.',
        genre: 'Roman',
        published_year: 1932,
        total_copies: 1,
        available_copies: 1
      }
    ];

    const insertBook = db.prepare(`
      INSERT INTO books (title, author, isbn, description, genre, published_year, total_copies, available_copies)
      VALUES (@title, @author, @isbn, @description, @genre, @published_year, @total_copies, @available_copies)
    `);
    books.forEach(book => insertBook.run(book));
  }
}

module.exports = { initDatabase, getDb };
