// Importamos las librerías necesarias
const express = require('express');  // Framework web para Node.js
const cors = require('cors');        // Permite peticiones desde el frontend
require('dotenv').config();          // Carga variables de entorno desde .env

// Creamos la aplicación Express
const app = express();
const PORT = process.env.PORT || 5000;  // Puerto del servidor (5000 por defecto)

// Configuramos middlewares
app.use(cors());            // Permite peticiones desde cualquier origen
app.use(express.json());    // Permite recibir datos JSON en las peticiones

// Ruta principal - responde con un mensaje de confirmación
app.get('/', (req, res) => {
  res.json({ message: 'Backend funcionando!' });
});

// Iniciamos el servidor en el puerto especificado
app.listen(PORT, () => {
  console.log(`🚀 Backend ejecutándose en puerto ${PORT}`);
});
