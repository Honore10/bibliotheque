process.env.NODE_ENV = 'test';

const request = require('supertest');
const app = require('../src/app');
const { initDatabase } = require('../src/database');

let adminToken;
let memberToken;

beforeAll(() => {
  initDatabase();
});

describe('Users - Register', () => {
  test('POST /api/users/register - success', async () => {
    const res = await request(app)
      .post('/api/users/register')
      .send({ name: 'Test User', email: 'test@example.com', password: 'password123' });

    expect(res.status).toBe(201);
    expect(res.body).toHaveProperty('token');
    expect(res.body.user).toHaveProperty('id');
    expect(res.body.user.email).toBe('test@example.com');
    expect(res.body.user.role).toBe('member');
    expect(res.body.user).not.toHaveProperty('password');
    memberToken = res.body.token;
  });

  test('POST /api/users/register - missing fields', async () => {
    const res = await request(app)
      .post('/api/users/register')
      .send({ email: 'missing@example.com' });

    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty('error');
  });

  test('POST /api/users/register - password too short', async () => {
    const res = await request(app)
      .post('/api/users/register')
      .send({ name: 'Short', email: 'short@example.com', password: '123' });

    expect(res.status).toBe(400);
  });

  test('POST /api/users/register - duplicate email', async () => {
    const res = await request(app)
      .post('/api/users/register')
      .send({ name: 'Dup', email: 'test@example.com', password: 'password123' });

    expect(res.status).toBe(409);
  });
});

describe('Users - Login', () => {
  test('POST /api/users/login - success as admin', async () => {
    const res = await request(app)
      .post('/api/users/login')
      .send({ email: 'admin@bibliotheque.fr', password: 'admin123' });

    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('token');
    expect(res.body.user.role).toBe('admin');
    adminToken = res.body.token;
  });

  test('POST /api/users/login - wrong password', async () => {
    const res = await request(app)
      .post('/api/users/login')
      .send({ email: 'test@example.com', password: 'wrongpassword' });

    expect(res.status).toBe(401);
  });

  test('POST /api/users/login - unknown email', async () => {
    const res = await request(app)
      .post('/api/users/login')
      .send({ email: 'nobody@example.com', password: 'password123' });

    expect(res.status).toBe(401);
  });

  test('POST /api/users/login - missing fields', async () => {
    const res = await request(app)
      .post('/api/users/login')
      .send({ email: 'test@example.com' });

    expect(res.status).toBe(400);
  });
});

describe('Users - Profile', () => {
  test('GET /api/users/profile - authenticated', async () => {
    const res = await request(app)
      .get('/api/users/profile')
      .set('Authorization', `Bearer ${memberToken}`);

    expect(res.status).toBe(200);
    expect(res.body.email).toBe('test@example.com');
    expect(res.body).not.toHaveProperty('password');
  });

  test('GET /api/users/profile - no token', async () => {
    const res = await request(app).get('/api/users/profile');
    expect(res.status).toBe(401);
  });

  test('GET /api/users/profile - invalid token', async () => {
    const res = await request(app)
      .get('/api/users/profile')
      .set('Authorization', 'Bearer invalidtoken');

    expect(res.status).toBe(401);
  });
});
