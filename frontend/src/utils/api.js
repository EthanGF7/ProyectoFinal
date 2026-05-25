// Funciones para comunicación con la API del backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export const api = {
  // Autenticación
  registrarUsuario: async (datosUsuario) => {
    // Aquí irá la lógica para registrar usuario
    return {};
  },

  iniciarSesion: async (email, password) => {
    // Aquí irá la lógica para iniciar sesión
    return {};
  },

  cerrarSesion: async () => {
    // Aquí irá la lógica para cerrar sesión
    return {};
  },

  // Playlists
  obtenerPlaylists: async () => {
    // Aquí irá la lógica para obtener playlists
    return [];
  },

  obtenerPlaylistPorId: async (id) => {
    // Aquí irá la lógica para obtener playlist específica
    return {};
  },

  crearPlaylist: async (datosPlaylist) => {
    // Aquí irá la lógica para crear playlist
    return {};
  }
};
