// Página de inicio de sesión
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaLogin() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Formulario de inicio de sesión */}
      <div className="form-content">
        <h1 className="form-title">🔐 Iniciar Sesión</h1>
        <p className="form-subtitle">Accede a tu cuenta de Discoteca Online</p>
        
        {/* Campos del formulario (próximamente funcionales) */}
        <div className="form-field">
          <p>📧 Email: (formulario próximamente)</p>
          <p>🔑 Contraseña: (formulario próximamente)</p>
          <p className="text-secondary">
            ¿No tienes cuenta? Ve a Registro
          </p>
        </div>
      </div>
    </div>
  );
}
