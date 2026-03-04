// Página del chatbot de recomendaciones
import BarraNavegacion from '../components/BarraNavegacion';

export default function PaginaChatbot() {
  return (
    <div className="page-container">
      <BarraNavegacion />
      
      {/* Contenedor del chatbot */}
      <div className="chatbot-container">
        <h1 className="chatbot-title">🤖 Chatbot de Recomendaciones</h1>
        <p className="chatbot-subtitle">Dime cómo te sientes y te recomendaré la música perfecta</p>
        
        {/* Interfaz del chat */}
        <div className="chatbot-chat">
          <div className="chatbot-message">
            <strong>🤖 Bot:</strong> ¡Hola! ¿Cómo te sientes hoy?
          </div>
          <div className="chatbot-options">
            <strong>😊 Opciones:</strong>
            <p>• Feliz y con energía</p>
            <p>• Triste o melancólico</p>
            <p>• Relajado y tranquilo</p>
            <p>• Con ganas de fiesta</p>
          </div>
          <p className="help-text">
            (Chat interactivo próximamente)
          </p>
        </div>
      </div>
    </div>
  );
}
