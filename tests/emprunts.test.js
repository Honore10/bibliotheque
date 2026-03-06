process.env.NODE_ENV = 'test';

const request = require('supertest');
const app = require('../src/app');
const { initDatabase } = require('../src/database');

let memberToken;
let adminToken;
let empruntId;
let bookId;

beforeAll(async () => {
  initDatabase();

  const adminLogin = await request(app)
    .post('/api/users/login')
    .send({ email: 'admin@bibliotheque.fr', password: 'admin123' });
  adminToken = adminLogin.body.token;

  const memberReg = await request(app)
    .post('/api/users/register')
    .send({ name: 'Emprunt User', email: 'empruntuser@example.com', password: 'password123' });
  memberToken = memberReg.body.token;

  const bookRes = await request(app)
    .post('/api/books')
    .set('Authorization', `Bearer ${adminToken}`)
    .send({ title: 'Emprunt Book', author: 'Author', totalCopies: 2 });
  bookId = bookRes.body.id;
});

describe('Emprunts - List', () => {
  test('GET /api/emprunts - requires auth', async () => {
    const res = await request(app).get('/api/emprunts');
    expect(res.status).toBe(401);
  });

  test('GET /api/emprunts - returns empty list initially', async () => {
    const res = await request(app)
      .get('/api/emprunts')
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
    expect(res.body.length).toBe(0);
  });
});

describe('Emprunts - Borrow', () => {
  test('POST /api/emprunts - requires auth', async () => {
    const res = await request(app)
      .post('/api/emprunts')
      .send({ bookId });

    expect(res.status).toBe(401);
  });

  test('POST /api/emprunts - missing bookId', async () => {
    const res = await request(app)
      .post('/api/emprunts')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({});

    expect(res.status).toBe(400);
  });

  test('POST /api/emprunts - non-existent book', async () => {
    const res = await request(app)
      .post('/api/emprunts')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({ bookId: 99999 });

    expect(res.status).toBe(404);
  });

  test('POST /api/emprunts - success', async () => {
    const bookBefore = await request(app).get(`/api/books/${bookId}`);
    const availableBefore = bookBefore.body.available_copies;

    const res = await request(app)
      .post('/api/emprunts')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({ bookId });

    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('id');
    expect(res.body.status).toBe('active');
    expect(res.body.book_id).toBe(bookId);
    expect(res.body).toHaveProperty('due_date');
    empruntId = res.body.id;

    const bookAfter = await request(app).get(`/api/books/${bookId}`);
    expect(bookAfter.body.available_copies).toBe(availableBefore - 1);
  });

  test('POST /api/emprunts - duplicate active borrow', async () => {
    const res = await request(app)
      .post('/api/emprunts')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({ bookId });

    expect(res.status).toBe(409);
  });

  test('POST /api/emprunts - no copies available', async () => {
    const noStockBook = await request(app)
      .post('/api/books')
      .set('Authorization', `Bearer ${adminToken}`)
      .send({ title: 'No Stock', author: 'Author', totalCopies: 1 });

    await request(app)
      .post('/api/emprunts')
      .set('Authorization', `Bearer ${adminToken}`)
      .send({ bookId: noStockBook.body.id });

    const res = await request(app)
      .post('/api/emprunts')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({ bookId: noStockBook.body.id });

    expect(res.status).toBe(400);
    expect(res.body.error).toMatch(/disponible/i);
  });
});

describe('Emprunts - List after borrow', () => {
  test('GET /api/emprunts - returns active borrowing', async () => {
    const res = await request(app)
      .get('/api/emprunts')
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(200);
    expect(res.body.length).toBeGreaterThan(0);
    const active = res.body.find(e => e.id === empruntId);
    expect(active).toBeDefined();
    expect(active.status).toBe('active');
    expect(active).toHaveProperty('title');
    expect(active).toHaveProperty('due_date');
  });
});

describe('Emprunts - Return', () => {
  test('PUT /api/emprunts/:id/retour - requires auth', async () => {
    const res = await request(app).put(`/api/emprunts/${empruntId}/retour`);
    expect(res.status).toBe(401);
  });

  test('PUT /api/emprunts/:id/retour - not found', async () => {
    const res = await request(app)
      .put('/api/emprunts/99999/retour')
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(404);
  });

  test('PUT /api/emprunts/:id/retour - success', async () => {
    const bookBefore = await request(app).get(`/api/books/${bookId}`);
    const availableBefore = bookBefore.body.available_copies;

    const res = await request(app)
      .put(`/api/emprunts/${empruntId}/retour`)
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(200);
    expect(res.body.status).toBe('returned');
    expect(res.body.returned_at).not.toBeNull();

    const bookAfter = await request(app).get(`/api/books/${bookId}`);
    expect(bookAfter.body.available_copies).toBe(availableBefore + 1);
  });

  test('PUT /api/emprunts/:id/retour - already returned', async () => {
    const res = await request(app)
      .put(`/api/emprunts/${empruntId}/retour`)
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(400);
  });
});
