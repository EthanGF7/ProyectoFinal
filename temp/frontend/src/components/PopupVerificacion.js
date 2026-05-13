// Componente de popup para verificación de email
import { useEffect } from 'react';

export default function PopupVerificacion({ isOpen, onClose, email }) {
  useEffect(() => {
    if (isOpen) {
      // Bloquear scroll del body cuando el popup está abierto
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }

    // Cleanup al desmontar
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="popup-overlay" onClick={onClose}>
      <div className="popup-container" onClick={(e) => e.stopPropagation()}>
        {/* Efectos de fondo del popup */}
        <div className="popup-glow"></div>
        
        {/* Contenido del popup */}
        <div className="popup-content">
          <div className="popup-icon">
            📧
          </div>
          
          <h2 className="popup-title">
            ¡Verifica tu Email!
          </h2>
          
          <p className="popup-message">
            Te hemos enviado un email de verificación a:
          </p>
          
          <div className="popup-email">
            {email}
          </div>
          
          <p className="popup-instructions">
            Revisa tu bandeja de entrada y haz clic en el enlace de verificación 
            para activar tu cuenta en la discoteca digital.
          </p>
          
          <div className="popup-tips">
            <p>💡 <strong>Consejos:</strong></p>
            <ul>
              <li>Revisa también tu carpeta de spam</li>
              <li>El enlace expira en 24 horas</li>
              <li>Puedes cerrar esta ventana</li>
            </ul>
          </div>
          
          <div className="popup-actions">
            <button 
              className="popup-btn-primary" 
              onClick={onClose}
            >
              🎵 ¡Entendido!
            </button>
            
            <button 
              className="popup-btn-secondary"
              onClick={() => window.open('https://mail.google.com', '_blank')}
            >
              📬 Abrir Gmail
            </button>
          </div>
          
          {/* Botón de cerrar */}
          <button 
            className="popup-close" 
            onClick={onClose}
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>
        
        {/* Partículas decorativas */}
        <div className="popup-particles">
          <div className="popup-particle">✨</div>
          <div className="popup-particle">🎵</div>
          <div className="popup-particle">💫</div>
          <div className="popup-particle">🎶</div>
        </div>
      </div>
    </div>
  );
}
