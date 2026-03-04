// Página de registro de usuarios
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaRegistro() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Formulario de registro */}
      <div className="form-content">
        <h1 className="form-title">📝 Registro</h1>
        <p className="form-subtitle">Crea tu cuenta en Discoteca Online</p>
        
        {/* Campos del formulario (próximamente funcionales) */}
        <div className="form-field">
          <p>👤 Username: (formulario próximamente)</p>
          <p>📧 Email: (formulario próximamente)</p>
          <p>🔑 Contraseña: (formulario próximamente)</p>
          <p>🎭 Tipo de usuario: (Admin/DJ/Usuario)</p>
          <p className="text-secondary">
            ¿Ya tienes cuenta? Ve a Login
          </p>
        </div>
      </div>
    </div>
  );
}
