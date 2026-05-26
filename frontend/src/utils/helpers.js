// Funciones de utilidad para el frontend
export const formatearTiempo = (segundos) => {
  // Aquí irá la lógica para formatear tiempo de canciones (ej: 3:45)
  return '0:00';
};

export const validarEmail = (email) => {
  // Aquí irá la lógica para validar formato de email
  return true;
};

export const validarPassword = (password) => {
  if (!password || password.length < 8) return { ok: false, error: 'Mínimo 8 caracteres' };
  if (!/[A-Z]/.test(password)) return { ok: false, error: 'Al menos una mayúscula' };
  if (!/[0-9]/.test(password)) return { ok: false, error: 'Al menos un número' };
  if (!/[^A-Za-z0-9]/.test(password)) return { ok: false, error: 'Al menos un carácter especial (!@#$%...)' };
  return { ok: true, error: null };
};

export const passwordStrength = (password) => {
  if (!password) return { level: 0, label: '', color: '' };
  let score = 0;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;
  if (score <= 1) return { level: 1, label: 'Muy débil', color: '#ff4444' };
  if (score === 2) return { level: 2, label: 'Débil', color: '#ff8800' };
  if (score === 3) return { level: 3, label: 'Media', color: '#ffcc00' };
  if (score === 4) return { level: 4, label: 'Fuerte', color: '#88cc00' };
  return { level: 5, label: 'Muy fuerte', color: '#00ff88' };
};

export const formatearFecha = (fecha) => {
  // Aquí irá la lógica para formatear fechas
  return new Date().toLocaleDateString();
};

export const truncarTexto = (texto, longitud) => {
  // Aquí irá la lógica para truncar texto largo
  return texto;
};
