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
- stream servido por backend mediante `VITE_CAMERA_STREAM_URL`;
- modo demo local con `/api/v1/demo/person-detection/stream`, que abre la webcam en el backend y dibuja detección básica de presencia humana;
- modo YOLO restaurante con `/api/v1/demo/yolo-restaurant/stream`, que dibuja personas y objetos COCO útiles para probar una mesa doméstica o una sala real sin activar todavía decisiones de negocio.

Variables disponibles en `apps/dashboard/.env.example`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_CAMERA_STREAM_URL=http://127.0.0.1:8000/api/v1/demo/yolo-restaurant/stream?source=0&image_size=320
```

El modo demo OpenCV usa cascada Haar frontal y fallback HOG de persona. El modo `yolo-restaurant` usa Ultralytics YOLO con clases COCO filtradas (`person`, `chair`, `dining table`, `cup`, `bottle`, `wine glass`, `bowl`, `fork`, `knife`, `spoon`, `pizza`). Ambos sirven para verificar cámara, overlay y flujo visual local; no identifican personas y no sustituyen la decisión final basada en ROI, tracking y reglas temporales.

Para probarlo:

```powershell
uvicorn apps.api.main:app --reload
cd apps/dashboard
npm run dev
```

Después abrir `http://127.0.0.1:5173`.

## Próximos pasos

1. Añadir cliente API tipado para FastAPI.
2. Sustituir datos iniciales a cero por polling o SSE.
3. Conectar el snapshot con una herramienta visual para marcar ROIs.
4. Pintar overlays reales de mesas/personas sobre la cámara.
5. Añadir filtros funcionales de salón, zona y rango horario.

## Snapshot de calibraci?n

Para congelar la vista real de la c?mara y marcar despu?s la ROI de mesa, entrada o cola, el backend expone:

```text
POST /api/v1/demo/camera-snapshot
```

Ejemplo local:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/demo/camera-snapshot?source=0"
```

El archivo se guarda en:

```text
data/calibration/snapshots/
```

La carpeta est? excluida de Git para no versionar im?genes reales. Solo se mantiene `.gitkeep`.

## Riesgos

- No conviene conectar la cámara directamente al navegador si el backend aún no normaliza el stream.
- No conviene añadir librerías de diseño pesadas antes de validar el flujo operativo.
- No conviene llenar el dashboard de gráficas; el MVP debe priorizar decisiones rápidas.
