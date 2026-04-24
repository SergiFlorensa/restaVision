# Dashboard operativo web

## Decisión

Crear el primer dashboard de RestaurIA como aplicación web local en `apps/dashboard`, usando Vite, React y TypeScript.

La prioridad es que el encargado pueda ver de un vistazo:

- cámara principal en directo,
- personas en sala,
- mesas libres, ocupadas, por liberar y fuera de servicio,
- cola y tiempo estimado,
- avisos operativos,
- mapa visual de mesas,
- estado general del sistema.

## Criterio visual

El diseño sigue una estética italiana cálida inspirada en La Piemontesa:

- fondo crema,
- paneles claros,
- verde albahaca para estados correctos/libres,
- rojo vino para ocupación y alertas críticas,
- dorado para mesas por liberar,
- sidebar oscuro para separar navegación de operación.

Se evita ruido visual: cada tarjeta debe responder una pregunta operativa concreta.

## Stack

- Vite para desarrollo rápido y build ligero.
- React para componentes reutilizables.
- TypeScript para contratos claros antes de conectar la API.
- CSS propio con variables de diseño para evitar dependencia visual pesada.
- `lucide-react` para iconografía consistente.
- SVG nativo para la gráfica de cola, evitando librerías de charting pesadas en el MVP.

## Encaje con el backend

La app queda preparada para consumir los endpoints ya existentes:

- `GET /api/v1/tables`,
- `GET /api/v1/events`,
- `GET /api/v1/alerts`,
- `GET /api/v1/predictions`,
- futuro endpoint de cámara/stream.

En esta fase arranca con datos operativos a cero para validar layout, jerarquía visual y experiencia operativa sin introducir ruido antes de conectar cámara y backend.

## Navegación interna

El menú lateral ya define las secciones principales y sus submenús:

- Vista General: resumen, cámara y avisos.
- Mapa de Mesas: salón principal, estados y zonas.
- Cámaras: principal, stream y calibración.
- Personas: recuento, distribución y flujo.
- Cola / Espera: estado, rangos y recepción.
- Indicadores: KPIs, rangos y salud.
- Histórico: eventos, sesiones y exportación.
- Ajustes: restaurante, umbrales y conexiones.

Cada sección abre una pantalla propia preparada para datos reales. Las acciones secundarias usan una ventana lateral con transición suave para no romper el contexto operativo.

## Cámara

La zona de cámara queda preparada de dos formas:

- webcam local desde navegador, usando permiso de cámara;
- stream servido por backend mediante `VITE_CAMERA_STREAM_URL`.

Variables disponibles en `apps/dashboard/.env.example`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_CAMERA_STREAM_URL=
```

El stream real deberá servirse desde backend cuando el pipeline de captura esté estabilizado. Para MJPEG puede usarse una etiqueta `img`; para WebRTC o vídeo real se podrá evolucionar el componente sin cambiar el layout.

## Próximos pasos

1. Añadir cliente API tipado para FastAPI.
2. Sustituir datos iniciales a cero por polling o SSE.
3. Añadir endpoint de snapshot/MJPEG para cámara.
4. Pintar overlays reales de mesas/personas sobre la cámara.
5. Añadir filtros funcionales de salón, zona y rango horario.

## Riesgos

- No conviene conectar la cámara directamente al navegador si el backend aún no normaliza el stream.
- No conviene añadir librerías de diseño pesadas antes de validar el flujo operativo.
- No conviene llenar el dashboard de gráficas; el MVP debe priorizar decisiones rápidas.
