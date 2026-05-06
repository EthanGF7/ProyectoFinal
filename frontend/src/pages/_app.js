// Componente raíz de la aplicación Next.js
// Este archivo envuelve todas las páginas de la aplicación
import '../styles/globals.css';
import '../styles/componentes.css';

import CursorGlow from '../components/CursorGlow';

export default function App({ Component, pageProps }) {
  // Component: la página actual que se está renderizando
  // pageProps: las props que se pasan a la página
  return (
    <>
      <CursorGlow />
      <Component {...pageProps} />
    </>
  );
}
