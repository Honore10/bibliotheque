process.env.NODE_ENV = 'test';

const request = require('supertest');
const app = require('../src/app');
const { initDatabase } = require('../src/database');

let adminToken;
let memberToken;

beforeAll(async () => {
  initDatabase();

  const adminLogin = await request(app)
    .post('/api/users/login')
    .send({ email: 'admin@bibliotheque.fr', password: 'admin123' });
  adminToken = adminLogin.body.token;

  const memberReg = await request(app)
    .post('/api/users/register')
    .send({ name: 'Member User', email: 'member@example.com', password: 'password123' });
  memberToken = memberReg.body.token;
});

describe('Books - List', () => {
  test('GET /api/books - returns all books', async () => {
    const res = await request(app).get('/api/books');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBeGreaterThan(0);
  });

  test('GET /api/books?search= - filters by title', async () => {
    const res = await request(app).get('/api/books?search=Prince');
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.some(b => b.title.includes('Prince'))).toBe(true);
  });

  test('GET /api/books?search= - filters by author', async () => {
    const res = await request(app).get('/api/books?search=Camus');
    expect(res.status).toBe(200);
    expect(res.body.every(b => b.author.includes('Camus'))).toBe(true);
  });
});

describe('Books - Get one', () => {
  test('GET /api/books/:id - existing book', async () => {
    const res = await request(app).get('/api/books/1');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('id', 1);
    expect(res.body).toHaveProperty('title');
    expect(res.body).toHaveProperty('author');
  });

  test('GET /api/books/:id - not found', async () => {
    const res = await request(app).get('/api/books/99999');
    expect(res.status).toBe(404);
  });
});

describe('Books - Create (admin only)', () => {
  let newBookId;

  test('POST /api/books - admin can create', async () => {
    const res = await request(app)
      .post('/api/books')
      .set('Authorization', `Bearer ${adminToken}`)
      .send({
        title: 'Test Book',
        author: 'Test Author',
        isbn: '978-0-000000-00-0',
        genre: 'Test',
        publishedYear: 2024,
        totalCopies: 3
      });

    expect(res.status).toBe(201);
    expect(res.body.title).toBe('Test Book');
    expect(res.body.total_copies).toBe(3);
    expect(res.body.available_copies).toBe(3);
    newBookId = res.body.id;
  });

  test('POST /api/books - member cannot create', async () => {
    const res = await request(app)
      .post('/api/books')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({ title: 'Unauthorized', author: 'Author' });

    expect(res.status).toBe(403);
  });

  test('POST /api/books - no auth', async () => {
    const res = await request(app)
      .post('/api/books')
      .send({ title: 'No Auth', author: 'Author' });

    expect(res.status).toBe(401);
  });

  test('POST /api/books - missing required fields', async () => {
    const res = await request(app)
      .post('/api/books')
      .set('Authorization', `Bearer ${adminToken}`)
      .send({ isbn: '000' });

    expect(res.status).toBe(400);
  });

  test('POST /api/books - duplicate ISBN', async () => {
    const res = await request(app)
      .post('/api/books')
      .set('Authorization', `Bearer ${adminToken}`)
      .send({ title: 'Dup ISBN', author: 'Author', isbn: '978-0-000000-00-0' });

    expect(res.status).toBe(409);
  });
});

describe('Books - Update (admin only)', () => {
  let bookId;

  beforeAll(async () => {
    const res = await request(app)
      .post('/api/books')
      .set('Authorization', `Bearer ${adminToken}`)
      .send({ title: 'Update Me', author: 'Author', totalCopies: 2 });
    bookId = res.body.id;
  });

  test('PUT /api/books/:id - admin can update', async () => {
    const res = await request(app)
      .put(`/api/books/${bookId}`)
      .set('Authorization', `Bearer ${adminToken}`)
      .send({ title: 'Updated Title', genre: 'Fiction' });

    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Updated Title');
    expect(res.body.genre).toBe('Fiction');
  });

  test('PUT /api/books/:id - member cannot update', async () => {
    const res = await request(app)
      .put(`/api/books/${bookId}`)
      .set('Authorization', `Bearer ${memberToken}`)
      .send({ title: 'Hacked' });

    expect(res.status).toBe(403);
  });

  test('PUT /api/books/:id - not found', async () => {
    const res = await request(app)
      .put('/api/books/99999')
      .set('Authorization', `Bearer ${adminToken}`)
      .send({ title: 'Ghost' });

    expect(res.status).toBe(404);
  });
});

describe('Books - Delete (admin only)', () => {
  let bookId;

  beforeAll(async () => {
    const res = await request(app)
      .post('/api/books')
      .set('Authorization', `Bearer ${adminToken}`)
      .send({ title: 'Delete Me', author: 'Author' });
    bookId = res.body.id;
  });

  test('DELETE /api/books/:id - admin can delete', async () => {
    const res = await request(app)
      .delete(`/api/books/${bookId}`)
      .set('Authorization', `Bearer ${adminToken}`);

    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('message');
  });

  test('DELETE /api/books/:id - already deleted', async () => {
    const res = await request(app)
      .delete(`/api/books/${bookId}`)
      .set('Authorization', `Bearer ${adminToken}`);

    expect(res.status).toBe(404);
  });

  test('DELETE /api/books/:id - member cannot delete', async () => {
    const res = await request(app)
      .delete('/api/books/1')
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(403);
  });
});
