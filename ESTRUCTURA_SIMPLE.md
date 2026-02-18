# Estructura Simple - Discoteca Online

## Descripción
Aplicación web tipo Spotify con usuarios (Admin/DJ/Normal), playlists por géneros, chatbot de recomendaciones y eventos temáticos.

## Estructura de Carpetas

```
ProyectoFinal/
├── frontend/                    # React/Next.js
│   ├── src/
│   │   ├── components/          # Componentes React
│   │   ├── pages/              # Páginas de la app
│   │   ├── styles/             # CSS/estilos
│   │   └── utils/              # Utilidades
│   ├── public/                 # Archivos estáticos
│   └── package.json
│
├── backend/                     # Node.js + Express
│   ├── src/
│   │   ├── routes/             # Rutas de la API
│   │   ├── controllers/        # Lógica de negocio
│   │   ├── middleware/         # Middlewares
│   │   └── config/             # Configuración
│   └── package.json
│
├── supabase/                    # Base de datos
│   ├── migrations/             # Migraciones SQL
│   └── seed.sql               # Datos iniciales
│
└── package.json                # Scripts principales
```

## Funcionalidades Principales

### Tipos de Usuario
- **Admin**: Gestiona todo
- **DJ**: Crea playlists y sube canciones
- **Usuario**: Navega y escucha música

### Características
- **Autenticación**: Login/registro con Supabase Auth
- **Playlists**: Organizadas por géneros musicales
- **Chatbot**: Recomendaciones basadas en estado de ánimo
- **Eventos**: Cambios visuales temáticos
- **Perfiles DJ**: Páginas personalizadas

### Géneros Musicales
Pop, Rock, Reggaeton, Trap, Hip Hop, Electronic, Jazz, Latino, Urbano, etc.

## Tecnologías
- **Frontend**: Next.js + TypeScript + TailwindCSS
- **Backend**: Node.js + Express
- **Base de Datos**: Supabase (PostgreSQL + Auth + Storage)
- **Tiempo Real**: Socket.io

## Comandos
- `npm run dev` - Inicia frontend y backend
- `npm run install:all` - Instala todas las dependencias
- `npm run build` - Build de producción
