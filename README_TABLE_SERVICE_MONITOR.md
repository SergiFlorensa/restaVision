# 🎥 Análisis de Servicio de Mesa en Tiempo Real - RestaurIA

Este módulo integra **detección YOLO** con **análisis de servicio de mesa** para monitorear en tiempo real:

- ✅ **Cubiertos** (tenedor, cuchillo, cuchara)
- ✅ **Platos** (platos, recipientes, boles)
- ✅ **Comida** detectada y servida
- ✅ **Personas** en la mesa
- ✅ **Gestos de atención** (mano levantada, llamadas)
- ✅ **Eventos de mesa** (llegada, partida, plato retirado, etc.)
- ✅ **Alertas operacionales** (servicio incompleto, cliente necesita atención)

## 🚀 Inicio Rápido

### 1. Opción A: Prueba Local con Webcam (Recomendado para empezar)

```bash
# Activar venv
source .venv/Scripts/activate  # Windows

# Ejecutar el script de prueba
python test_table_service_webcam.py
```

**Qué esperar:**
- Se abrirá una ventana con tu webcam
- Verás en tiempo real:
  - Detecciones de YOLO (cuadros alrededor de objetos)
  - Estado de la mesa (personas, cubiertos, platos, comida)
  - Alertas si falta algo
  - Eventos en consola (mano levantada, cliente se levanta, etc.)

---

### 2. Opción B: Usar API REST en vivo

**Terminal 1 - Iniciar servidor API:**

```bash
source .venv/Scripts/activate
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - Streaming en tiempo real:**

```bash
# Ver stream MJPEG + análisis
# Abre en navegador:
http://localhost:8000/api/v1/demo/table-service/stream?source=0&table_id=table_01

# O analizar frame actual (JSON):
curl -X POST "http://localhost:8000/api/v1/demo/table-service/analyze?source=0&table_id=table_01"
```

**En el navegador (http://localhost:8000/docs):**
- Ve a `/api/v1/demo/table-service/status`  
- Click en "Try it out"
- Verás URL del stream

---

## 📊 Endpoints API

### Status del Monitor
```
GET /api/v1/demo/table-service/status?source=0&table_id=table_01
```

**Response:**
```json
{
  "available": true,
  "stream_url": "/api/v1/demo/table-service/stream?source=0&table_id=table_01",
  "camera_source": "0",
  "table_id": "table_01",
  "detector": "Ultralytics YOLO con análisis de servicio de mesa",
  "inference_stride": 3
}
```

### Stream MJPEG (en vivo)
```
GET /api/v1/demo/table-service/stream?source=0&table_id=table_01&inference_stride=3
```

**Devuelve:** Stream de video MJPEG con análisis dibujado  
**Media-type:** `multipart/x-mixed-replace; boundary=frame`

### Análisis JSON (snapshot)
```
POST /api/v1/demo/table-service/analyze?source=0&table_id=table_01
```

**Response:**
```json
{
  "table_id": "table_01",
  "updated_at": "2026-04-24T15:30:45.123456+00:00",
  "state": "eating",
  "people_count": 2,
  "object_counts": {
    "person": 2,
    "fork": 2,
    "knife": 2,
    "plate": 2,
    "food": 1
  },
  "missing_items": {},
  "service_flags": {
    "plates_complete": true,
    "cutlery_complete": true,
    "food_served": true,
    "customer_needs_attention": false
  },
  "active_alerts": [],
  "timeline_events": [
    {
      "event_id": "table_01_food_served_1234567890",
      "ts": "2026-04-24T15:30:45.123456+00:00",
      "event_type": "food_served",
      "message": "Comida detectada en mesa",
      "payload": {"food_like_objects": 1}
    }
  ],
  "seat_duration_seconds": 245,
  "away_duration_seconds": null
}
```

---

## 🎯 Estados de la Mesa

| Estado | Significado |
|--------|------------|
| `empty` | Sin personas, sin platos, sin comida |
| `waiting_for_video` | Esperando primer frame |
| `observing` | Sin análisis claro |
| `seated` | Personas sentadas, sin comida |
| `needs_setup` | Personas sentadas pero falta servicio |
| `eating` | Personas y comida detectadas |
| `away` | Cliente se levantó (ausencia temporal) |

---

## 🚩 Alertas Generadas

### Missing Table Setup (Servicio Incompleto)
- **Severity:** medium
- **Cuándo:** Hay personas pero faltan cubiertos/platos
- **Ejemplo:** "Falta completar servicio de mesa — fork: 1, knife: 1"

### Customer Attention Requested (Cliente pide atención)
- **Severity:** high  
- **Cuándo:** Se detecta gesto de mano levantada o llamada
- **Ejemplo:** "Posible cliente solicitando atención"

---

## 📋 Eventos de Línea de Tiempo

| Evento | Descripción |
|--------|------------|
| `table_session_started` | Cliente llega a la mesa |
| `plate_served` | Plato/recipiente detectado |
| `food_served` | Comida detectada en la mesa |
| `plate_removed` | Plato retirado |
| `customer_left_table` | Cliente se levanta |
| `customer_returned` | Cliente vuelve (con duración de ausencia) |
| `customer_attention_requested` | Gesto de llamada detectado |
| `missing_table_setup` | Falta completar servicio |

---

## ⚙️ Configuración

Edit `TableServiceMonitorConfig` en [services/vision/table_service_monitor.py](services/vision/table_service_monitor.py):

```python
config = TableServiceMonitorConfig(
    table_id="table_01",
    require_plate=True,         # Exigir plato
    require_fork=True,          # Exigir tenedor
    require_knife=True,         # Exigir cuchillo
    require_spoon=False,        # No exigir cuchara
    min_people_for_service_check=1,  # Mínimo de personas para validar
    alert_cooldown_seconds=5,   # No repetir alerta en 5s
    max_timeline_events=30,     # Máximo eventos guardados
)
```

---

## 🔍 Etiquetas YOLO Detectadas

**Cubiertos:** fork, knife, spoon  
**Platos:** plate, bowl  
**Comida:** pizza, sandwich, hot dog, cake, donut, banana, apple, orange, broccoli, carrot  
**Atención:** hand_raised, raised_hand, finger_raised, call_waiter  
**Base:** person, chair, dining table, cup, bottle, wine glass  

---

## 💡 Casos de Uso

### Caso 1: Monitoreo en tiempo real de cena
```bash
python test_table_service_webcam.py
# Mira la consola para eventos en vivo
```

### Caso 2: Integración con dashboard
```javascript
// En el dashboard, conecta:
fetch("/api/v1/demo/table-service/status")
  .then(r => r.json())
  .then(data => {
    const streamUrl = data.stream_url;
    // Mostrar en <img> o <video>
    document.getElementById("stream").src = streamUrl;
  });
```

### Caso 3: Alertas via WebSocket (futuro)
```python
# En development, usar SSE o WebSocket para alertas en tiempo real
# @app.websocket("/ws/table-service/{table_id}")
```

---

## 🛠️ Troubleshooting

### ❌ "YOLO no disponible"
```bash
pip install ultralytics torch torchvision
```

### ❌ "OpenCV no disponible"
```bash
pip install opencv-python
```

### ❌ "No puedo acceder a la cámara"
- Verificar que no hay otro programa usando la cámara
- En Linux: `chmod 666 /dev/video0`
- En Windows: Revisar permisos de cámara en Configuración

### ❌ "Stream muy lento"
- Incrementar `inference_stride` (menos frames = más rápido)
- Reducir `image_size` en YoloDetectorConfig
- Usar `yolo11n.pt` en lugar de modelos más grandes

---

## 📝 Próximos pasos

- [ ] Integración con WebSocket para alertas en tiempo real
- [ ] Guardado de eventos en PostgreSQL
- [ ] Dashboard interactivo con timeline de eventos
- [ ] Notificaciones tipo WhatsApp para alertas críticas
- [ ] Tracking de individuos entre frames (persona con ID)
- [ ] Predicción de ocupación de mesa (ETA para desocupar)

---

## 📚 Referencias

- [TableServiceMonitor](services/vision/table_service_monitor.py)
- [YOLO Detector](services/vision/yolo_detector.py)  
- [API Main](apps/api/main.py)
- [Documentación Arquitectura](docs/02_arquitectura/)
