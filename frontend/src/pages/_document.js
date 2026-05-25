// Configuración del documento HTML base de Next.js
import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
  return (
    // Estructura HTML básica de la aplicación
    <Html lang="es">
      <Head>
        {/* Meta tags y configuración del head */}
        <meta charSet="utf-8" />
        <meta name="description" content="Discoteca Online - Plataforma de música" />
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
