process.env.NODE_ENV = 'test';

const request = require('supertest');
const app = require('../src/app');
const { initDatabase } = require('../src/database');

let memberToken;
let reservationId;
let bookId;

beforeAll(async () => {
  initDatabase();

  const memberReg = await request(app)
    .post('/api/users/register')
    .send({ name: 'Res User', email: 'resuser@example.com', password: 'password123' });
  memberToken = memberReg.body.token;

  const adminLogin = await request(app)
    .post('/api/users/login')
    .send({ email: 'admin@bibliotheque.fr', password: 'admin123' });
  const adminToken = adminLogin.body.token;

  const bookRes = await request(app)
    .post('/api/books')
    .set('Authorization', `Bearer ${adminToken}`)
    .send({ title: 'Reservation Book', author: 'Author', totalCopies: 1 });
  bookId = bookRes.body.id;
});

describe('Reservations - List', () => {
  test('GET /api/reservations - requires auth', async () => {
    const res = await request(app).get('/api/reservations');
    expect(res.status).toBe(401);
  });

  test('GET /api/reservations - returns empty list initially', async () => {
    const res = await request(app)
      .get('/api/reservations')
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(200);
    expect(Array.isArray(res.body)).toBe(true);
  });
});

describe('Reservations - Create', () => {
  test('POST /api/reservations - requires auth', async () => {
    const res = await request(app)
      .post('/api/reservations')
      .send({ bookId });

    expect(res.status).toBe(401);
  });

  test('POST /api/reservations - missing bookId', async () => {
    const res = await request(app)
      .post('/api/reservations')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({});

    expect(res.status).toBe(400);
  });

  test('POST /api/reservations - non-existent book', async () => {
    const res = await request(app)
      .post('/api/reservations')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({ bookId: 99999 });

    expect(res.status).toBe(404);
  });

  test('POST /api/reservations - success', async () => {
    const res = await request(app)
      .post('/api/reservations')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({ bookId });

    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('id');
    expect(res.body.status).toBe('active');
    expect(res.body.book_id).toBe(bookId);
    reservationId = res.body.id;
  });

  test('POST /api/reservations - duplicate reservation', async () => {
    const res = await request(app)
      .post('/api/reservations')
      .set('Authorization', `Bearer ${memberToken}`)
      .send({ bookId });

    expect(res.status).toBe(409);
  });
});

describe('Reservations - List after create', () => {
  test('GET /api/reservations - returns list with reservation', async () => {
    const res = await request(app)
      .get('/api/reservations')
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(200);
    expect(res.body.length).toBeGreaterThan(0);
    expect(res.body[0]).toHaveProperty('title');
    expect(res.body[0]).toHaveProperty('reserved_at');
  });
});

describe('Reservations - Cancel', () => {
  test('DELETE /api/reservations/:id - requires auth', async () => {
    const res = await request(app).delete(`/api/reservations/${reservationId}`);
    expect(res.status).toBe(401);
  });

  test('DELETE /api/reservations/:id - not found', async () => {
    const res = await request(app)
      .delete('/api/reservations/99999')
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(404);
  });

  test('DELETE /api/reservations/:id - success', async () => {
    const res = await request(app)
      .delete(`/api/reservations/${reservationId}`)
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('message');
  });

  test('DELETE /api/reservations/:id - already cancelled', async () => {
    const res = await request(app)
      .delete(`/api/reservations/${reservationId}`)
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(400);
  });
});
