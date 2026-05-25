// Configuración del documento HTML base de Next.js
import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
  return (
    // Estructura HTML básica de la aplicación
    <Html lang="es">
      <Head>
        {/* Meta tags y configuración del head */}
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content="Namae Nashi - Plataforma de música" />
        <title>Namae Nashi</title>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Outfit:wght@300;400;500;600;700;800;900&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <link rel="icon" type="image/png" href="/logo.png" />
        <link rel="apple-touch-icon" href="/logo.png" />
      </Head>
      <body>
        {/* Contenido principal de la aplicación */}
        <Main />
        {/* Scripts de Next.js */}
        <NextScript />
      </body>
    </Html>
  )
}
