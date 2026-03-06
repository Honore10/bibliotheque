const { initDatabase } = require('./database');
const app = require('./app');

initDatabase();

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Bibliothèque numérique démarrée sur http://localhost:${PORT}`);
});
