# Discoteca Online

Discoteca Online es una plataforma web con estética neon/disco pensada para ofrecer a los usuarios una experiencia inmersiva de comunidad musical. El proyecto combina un **frontend en Next.js 14** con autenticación mediante **Supabase** y un **backend en FastAPI** preparado para futuras integraciones (playlists, eventos, experiencias personalizadas, etc.).

La aplicación actual se centra en la experiencia de registro, acceso seguro y gestión del perfil del usuario, manteniendo una interfaz altamente visual con animaciones de vinilos, gradientes luminosos y componentes responsivos.

## 🧱 Arquitectura general

```
ProyectoFinal/
├── frontend/          # Aplicación Next.js (React) + Supabase
│   ├── src/
│   │   ├── pages/     # Rutas: login, registro, perfil, eventos, etc.
│   │   ├── components/ # Reutilizables: barra de navegación, popup de verificación, ...
│   │   └── styles/    # CSS Modules y hojas globales
│   └── public/        # Recursos estáticos
├── backend/           # API en FastAPI (Python) lista para extender
│   ├── main.py        # Punto de entrada del servidor
│   └── app/           # Módulos y routers futuros
└── Dj/                # Recursos adicionales del proyecto (dataset, assets, etc.)
```

## ✨ Funcionalidades destacadas

- **Autenticación con Supabase**: registro, login y logout usando email/password con almacenamiento seguro.
- **Página de registro personalizada**: formulario con validaciones de contraseña, selector de tipo de usuario y popup animado que invita a verificar el correo.
- **Página de inicio de sesión**: vinilo animado en fondo completo, efectos glow y retroalimentación visual para errores.
- **Perfil del usuario**:
  -Visualización de username, email, rol y fecha de alta.
  -Edición de username, email y contraseña.
  -Actualización inmediata del email utilizando un endpoint protegido con la Service Role Key de Supabase.
  -Botón de cierre de sesión que limpia la sesión y redirige al inicio.
- **Barra de navegación dinámica**: muestra enlaces a login/registro solo cuando el usuario no está autenticado y acceso directo al perfil cuando sí lo está.
- **Panel de actividad personal**: historial de últimas canciones, canciones con like, último DJ y playlist reproducida, todo desde una vista resumida en `/perfil`.
- **Tema disco-neón** consistente: gradientes, luces dinámicas, tarjetas con borde brillante, avatar generativo pulsante y componentes responsivos.
- **Páginas temáticas preparadas**: playlists, DJs, eventos y paneles administrativos listos para conectar con datos reales.

## 🛠 Tecnologías principales

| Capa       | Tecnologías | Detalles |
|------------|-------------|----------|
| Frontend   | Next.js 14, React 18, CSS Modules | Integración con Supabase JS, animaciones CSS personalizadas, gestión de estado con hooks. |
| Backend    | FastAPI, Uvicorn, Python 3.11 | Configuración CORS para conectar con el frontend, endpoints `/` y `/health` listos para extender. |
| Autenticación y datos | Supabase | Auth email/password, almacenamiento de metadatos del usuario, Service Role para cambios de email desde servidor. |

## 🚀 Puesta en marcha

### 1. Requisitos previos

- Node.js >= 18
- npm o pnpm
- Python >= 3.11 (para el backend)
- Cuenta y proyecto en Supabase

### 2. Configuración de variables de entorno

#### Frontend (`frontend/.env.local`)

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://TU_PROYECTO.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=tu_clave_anon_publica
SUPABASE_SERVICE_ROLE_KEY=tu_clave_service_role   # ⚠️ mantener privada, solo para API routes
```

> La `SUPABASE_SERVICE_ROLE_KEY` es necesaria para actualizar el email directamente desde la API interna `/api/profile/update-email`. Nunca la publiques ni la expongas en el cliente.

#### Backend (`backend/.env`)

```dotenv
PORT=5000
FRONTEND_URL=http://localhost:3000
SUPABASE_URL=https://TU_PROYECTO.supabase.co
SUPABASE_ANON_KEY=tu_clave_anon_publica
```

### 3. Ejecutar el frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend quedará disponible en `http://localhost:3000`.

### 4. Ejecutar el backend (opcional)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 5000
```

La API responderá en `http://localhost:5000` con las rutas de prueba listadas.

## 🔐 Flujo de autenticación y perfil

1. **Registro**: el usuario rellena el formulario, el frontend crea la cuenta en Supabase y muestra un popup animado explicando la verificación por email.
2. **Inicio de sesión**: autenticación clásica email + contraseña; al entrar se ajusta la barra de navegación para mostrar enlace al perfil.
3. **Gestión de perfil**:
   - El usuario puede editar nombre, email y contraseña.
   - Al cambiar email se invoca `POST /api/profile/update-email`, que utiliza la Service Role Key para modificarlo sin confirmación adicional.
   - Tras guardar se recarga el usuario actual con `supabase.auth.getUser()` para sincronizar datos en la UI.
   - Cerrar sesión llama a `supabase.auth.signOut()` y redirige a la pantalla principal.

## 🎨 Diseño y UX

- Paleta basada en púrpuras, fucsias y verdes neón.
- Fondos con gradientes radiales y vinilos animados rotando a velocidad constante.
- Componentes accesibles y responsivos con estados hover y focus.
- Popup de verificación con partículas flotantes y botones temáticos.
- Avatar en el perfil con borde pulsante y glow sincronizado.

## 🧪 Scripts útiles

| Comando                  | Ubicación | Descripción |
|--------------------------|-----------|-------------|
| `npm run dev`            | `frontend/` | Levanta Next.js en modo desarrollo. |
| `npm run build`          | `frontend/` | Construye la aplicación para producción. |
| `npm run start`          | `frontend/` | Sirve el build de producción. |
| `npm run lint`           | `frontend/` | Ejecuta ESLint con la configuración de Next. |
| `uvicorn main:app --reload` | `backend/` | Servidor FastAPI en caliente. |

## 📁 Estructura de carpetas destacada (frontend)

```
src/
├── components/
│   ├── BarraNavegacion.js      # Navbar sensible al estado de auth
│   ├── PopupVerificacion.js    # Modal animada tras registro
│   └── ...
├── pages/
│   ├── _app.js, _document.js   # Configuración global de Next.js
│   ├── login.js                # Pantalla de acceso con vinilo animado
│   ├── registro.js             # Formulario de alta + popup
│   ├── perfil.js               # Perfil con edición de datos y logout
│   └── api/profile/update-email.js # Endpoint interno para actualizar email
└── styles/
    ├── componentes.css         # Estilos neon, animaciones y layout general
    └── globals.css             # Reset y variables globales
```

## �️ Detalle de archivos y comunicación

### Frontend – Páginas principales (`src/pages`)

| Archivo | Rol | Depende de | Expone / Interactúa con |
|---------|-----|------------|--------------------------|
| `_app.js` | Envuelve todas las páginas y carga los estilos globales. | `globals.css`, `componentes.css` | - |
| `_document.js` | Ajusta la plantilla HTML (lang, meta tags). | Next Document API | - |
| `index.js` | Landing estática que introduce la discoteca y enlaza a otras secciones. | `BarraNavegacion` | Navegación a rutas públicas. |
| `login.js` | Formulario de inicio de sesión con animación de vinilo. | `supabase.js` (cliente), `useRouter` | Redirige al perfil tras login. |
| `registro.js` | Alta de usuarios con validaciones y popup neon. | `supabase.js`, `PopupVerificacion` | Redirige a `/login` y muestra modal tras registro. |
| `perfil.js` | Perfil personal: muestra metadata, panel de actividad (historial, likes, resumen) y permite editar username/email/password. | `supabase.js`, `BarraNavegacion`, `/api/profile/update-email`, `useListenHistory`, `useLikedTracks` | Actualiza Supabase Auth, consume `/api/user/listen-history` y `/api/user/liked-tracks`; redirige a `/login` si no hay sesión. |
| `eventos.js`, `djs.js`, `playlists.js`, `admin.js` | Páginas temáticas/preparadas para ampliar contenido (listados, dashboards, panel de admin). | Componentes específicos (p.ej. `EventoTematico`, `PanelAdmin`) | Sirven como contenedores para futuras integraciones. |
| `api/profile/update-email.js` | API Route que ejecuta en servidor Next. Usa la Service Role Key para cambiar el email directamente en Supabase sin verificación. | `@supabase/supabase-js`, variable `SUPABASE_SERVICE_ROLE_KEY` | Devuelve JSON con el nuevo email o error; consumido por `perfil.js`. |
| `api/user/listen-history.js` | Devuelve/almacena historial de escuchas con DJ, playlist y track. | `supabaseAdmin`, `getAuthenticatedUser` | Usado por `useListenHistory` para panel de actividad. |
| `api/user/liked-tracks.js` | Devuelve los `track_reactions` con like del usuario autenticado. | `supabaseAdmin`, `getAuthenticatedUser` | Usado por `useLikedTracks` para mostrar favoritos recientes. |

### Frontend – Componentes (`src/components`)

| Componente | Función | Consumido por |
|------------|---------|---------------|
| `BarraNavegacion.js` | Navbar reactiva: consulta Supabase para mostrar login/registro o enlace al perfil. | Todas las páginas públicas y privadas. |
| `PopupVerificacion.js` | Modal con animación neon que se lanza tras el registro para guiar la verificación. | `registro.js`. |
| `EventoTematico.js`, `ListaPlaylist.js`, `PanelAdmin.js`, `PerfilDJ.js`, `TarjetaPlaylist.js`, `ReproductorMusica.js` | Widgets preparados para listas de contenido, panel de admin, perfiles y reproductores. | Páginas temáticas (`eventos.js`, `djs.js`, etc.). |
| `FormularioLogin.js`, `FormularioRegistro.js` | Variantes minimalistas de formularios reutilizables. | Disponibles para integrar en futuras vistas o modales. |

### Frontend – Utilidades y estilos

- `src/utils/supabase.js`: crea el cliente de Supabase usando variables públicas, expone helpers (`auth.signUp`, `auth.signIn`, `auth.signOut`, `auth.getUser`) y una función de diagnóstico `verificarConexion`. Todo el frontend lo importa para interactuar con Supabase Auth.
- `src/styles/globals.css`: reset de estilos, tipografías y variables base (por ejemplo colores neon y gradientes).
- `src/styles/componentes.css`: hoja principal ≈28 KB con animaciones del vinilo, popups, layouts del perfil, tarjetas de contenido y clases compartidas (`auth-container`, `btn-primary`, etc.).

### Backend – FastAPI (`backend/`)

| Ruta / Módulo | Descripción | Estado |
|---------------|-------------|--------|
| `main.py` | Inicializa FastAPI, configura CORS para `http://localhost:3000` y expone `/` y `/health`. | Operativo. |
| `app/config/` | Espacio para settings y carga de variables (placeholders actuales). | Base preparada. |
| `app/routes/*.py` | Esqueletos para autenticación, usuarios, playlists, eventos y canciones. Cada archivo define funciones stub listas para implementar lógica. | En construcción (stubs). |
| `app/controllers/`, `app/middleware/`, `app/utils/` | Carpetas vacías o con plantillas para alojar la lógica de negocio, middlewares personalizados y utilidades. | Preparado para expansión. |

### Comunicación entre capas

1. **Frontend ⇄ Supabase**: todas las páginas importan el cliente desde `src/utils/supabase.js`. `login.js`, `registro.js` y `perfil.js` consumen `supabase.auth` directamente.
2. **Cambio directo de email**: `perfil.js` obtiene el token de sesión actual (`supabase.auth.getSession()`), lo envía en la cabecera `Authorization` hacia la API interna `/api/profile/update-email`. Esa ruta corre en el servidor de Next.js, crea un cliente de Supabase con la Service Role Key y llama a `supabaseAdmin.auth.admin.updateUserById`.
3. **Estado de navegación**: `BarraNavegacion` escucha `supabase.auth.onAuthStateChange`, de modo que cualquier login/logout emitido desde otros componentes sincroniza la UI de inmediato.
4. **Backend FastAPI**: aunque hoy no está conectado directamente, `main.py` queda listo para servir datos (por ejemplo, listas de eventos) que luego podrían ser consumidos con `fetch` desde `eventos.js` u otras páginas de contenido.

## �� Próximos pasos sugeridos

- Integrar servicios reales en el backend (recomendaciones musicales, eventos, etc.).
- Añadir tests (Playwright / Jest) para flujos críticos de autenticación.
- Integrar recomendaciones automáticas futuramente (sin chatbot dedicado).
- Internacionalización (i18n) y soporte multilenguaje.

## 📄 Licencia

El proyecto es de uso interno/académico. Ajusta esta sección según el modelo de distribución que el equipo decida.

---

¿Necesitas ampliar funcionalidades o automatizar despliegues? Abre un issue o continúa la colaboración con más tareas. ¡Que siga la fiesta disco! 💿✨
