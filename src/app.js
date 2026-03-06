const express = require('express');
const path = require('path');
const rateLimit = require('express-rate-limit');

const app = express();

// Rate limiting: strict limit on auth routes, general limit on all API routes
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Trop de tentatives, réessayez dans 15 minutes.' }
});

const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 300,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Trop de requêtes, réessayez dans 15 minutes.' }
});

app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));
app.use(apiLimiter);

app.use('/api/users/login', authLimiter);
app.use('/api/users/register', authLimiter);

app.use('/api/users', require('./routes/users'));
app.use('/api/books', require('./routes/books'));
app.use('/api/reservations', require('./routes/reservations'));
app.use('/api/emprunts', require('./routes/emprunts'));

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../public/index.html'));
});

module.exports = app;
