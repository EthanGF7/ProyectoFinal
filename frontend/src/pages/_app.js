// Componente raíz de la aplicación Next.js
// Este archivo envuelve todas las páginas de la aplicación
export default function App({ Component, pageProps }) {
  // Component: la página actual que se está renderizando
  // pageProps: las props que se pasan a la página
  return <Component {...pageProps} />
}
