# 🎬 GUÍA DE PRUEBA - Análisis de Servicio de Mesa en Tiempo Real

## ✨ Resumen de lo que ahora tienes

He integrado **TableServiceMonitor** (tu nuevo commit) en la API con:

✅ **3 nuevos endpoints:**
1. `GET /api/v1/demo/table-service/status` - Info del monitor
2. `GET /api/v1/demo/table-service/stream` - **MJPEG en vivo con análisis dibujado**
3. `POST /api/v1/demo/table-service/analyze` - JSON con análisis actual

✅ **1 script de prueba local:**
- `test_table_service_webcam.py` - Prueba completa sin API

✅ **Detección integrada:**
- Cubiertos ✓ Platos ✓ Comida ✓ Personas ✓ Gestos de atención
- Alertas automáticas de servicio incompleto
- Timeline de eventos (llegada, comida servida, cliente pide, se levanta, vuelve)
- Timers de duración (cuánto tiempo sentado, cuánto tiempo ausente)

---

## 🚀 OPCIÓN 1: Prueba Rápida (5 minutos)

### Paso 1: Terminal 1 - Ejecuta el script de prueba local

```bash
cd "c:\Users\SERGI\Desktop\Sergi\restaurIA_documentacion_master\restaurIA_docs"

# Activar venv
.venv\Scripts\activate

# Ejecutar prueba
python test_table_service_webcam.py
```

**✅ Qué pasa:**
- Se abre una ventana con tu webcam en vivo
- Verás:
  - Frame con detecciones YOLO (cuadros de colores)
  - En pantalla: Mesa, Estado, Personas, Tiempo sentado
  - En consola: Eventos detallados cada ~1 segundo
- Si levantas la mano → alerta de "cliente pide atención"
- Si te sientas → evento "cliente sentado"
- Si hay cubiertos/platos → "✅ Servicio completo"
- Si falta algo → "❌ Falta: fork:1"

**🎯 Prueba esto:**
1. Siéntate enfrente de la cámara
2. Levanta la mano (debería detectar gesto de atención)
3. Espera 5 segundos y ponte de pie (debería registrar "customer_left_table")
4. Vuelve a sentarte (debería registrar "customer_returned" con tiempo ausente)
5. Coloca un objeto en la mesa (plato, tenedor si tienes)

---

## 🚀 OPCIÓN 2: Prueba con API REST (10 minutos)

### Paso 1: Terminal 1 - Inicia el servidor API

```bash
cd "c:\Users\SERGI\Desktop\Sergi\restaurIA_documentacion_master\restaurIA_docs"
.venv\Scripts\activate

# Opción A: Con el script especial
python run_api_with_service_monitor.py

# O Opción B: Comando directo
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

**✅ Cuando veas:**
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Paso 2: Abre el navegador

#### Opción A: Ver documentación interactiva
```
http://localhost:8000/docs
```

Busca `/api/v1/demo/table-service/status` y haz click en "Try it out"

#### Opción B: Ver stream MJPEG en vivo
```
http://localhost:8000/api/v1/demo/table-service/stream?source=0&table_id=table_01
```

El navegador mostrará streaming de video en tiempo real con análisis dibujado

#### Opción C: Consultar análisis JSON actual (snapshot)
```
http://localhost:8000/api/v1/demo/table-service/analyze?source=0&table_id=table_01
```

Verás JSON completo con:
- Estado actual de la mesa
- Objetos detectados
- Items faltantes
- Alerts activas
- Timeline de eventos

---

## 📊 QUÉ ESPERAR

### En el stream MJPEG verás:

```
Mesa: table_01
Estado: eating
Personas: 2
Tiempo: 245s

✅ Servicio completo
```

Con cuadros dibujados alrededor de:
- 👥 Personas (verde)
- 🍴 Cubiertos (azul)
- 🍽️ Platos (rojo)
- 🍕 Comida (amarillo)

### En la consola verás eventos como:

```
======================================================================
⏱️  Frame: 30
📅 Timestamp: 2026-04-24T15:30:45.123456
🪑 Estado: seated
👥 Personas: 1
⏳ Tiempo sentado: 5s

🔍 Objetos detectados:
   - person: 1
   - fork: 1
   - knife: 1
   - plate: 1

✅ Servicio de mesa completo

🚩 Banderas de servicio:
   ✅ plates_complete
   ✅ cutlery_complete
   ❌ food_served
   ❌ customer_needs_attention
======================================================================
```

### En JSON verás:

```json
{
  "table_id": "table_01",
  "state": "seated",
  "people_count": 1,
  "object_counts": {
    "person": 1,
    "fork": 1,
    "knife": 1,
    "plate": 1
  },
  "missing_items": {},
  "service_flags": {
    "plates_complete": true,
    "cutlery_complete": true,
    "food_served": false,
    "customer_needs_attention": false
  },
  "active_alerts": [],
  "timeline_events": [
    {
      "event_id": "table_01_table_session_started_1234567890",
      "ts": "2026-04-24T15:30:45.123456",
      "event_type": "table_session_started",
      "message": "Cliente detectado en la mesa",
      "payload": {"people_count": 1}
    }
  ],
  "seat_duration_seconds": 5,
  "away_duration_seconds": null
}
```

---

## 🎯 CASOS DE PRUEBA RECOMENDADOS

### Test 1: Cliente llega y se sienta
1. Empieza sin personas frente a la cámara
2. Siéntate lentamente
3. **Esperado:** Ver eventos `table_session_started`, estado pasa a `seated`

### Test 2: Comida es servida
1. Ya sentado, muestra un objeto (plato, comida)
2. **Esperado:** Evento `plate_served` o `food_served`

### Test 3: Servicio incompleto
1. Muestra una persona pero sin cubiertos/platos
2. **Esperado:** Estado `needs_setup`, alerta `missing_table_setup`

### Test 4: Cliente pide atención
1. Levanta la mano o un brazo
2. **Esperado:** Evento `customer_attention_requested`, alerta `customer_attention_requested`

### Test 5: Cliente se levanta y vuelve
1. De pie (ausencia) por 3+ segundos
2. Vuelve a sentarte
3. **Esperado:** 
   - Evento `customer_left_table`
   - Evento `customer_returned` con duración de ausencia
   - `away_duration_seconds` en JSON

---

## 🔧 CONFIGURAR PARÁMETROS

### Reducir CPU (si es lento):

En `test_table_service_webcam.py` o en URL:

```python
# Aumentar inference_stride (menos frames = menos cálculos)
inference_stride = 5  # En lugar de 3

# O en URL:
# .../table-service/stream?...&inference_stride=5
```

### Cambiar confianza de detección:

```
?confidence=0.30  # Más sensible (detecta más)
?confidence=0.15  # Menos cosas falsas
```

### Cambiar tabla:

```
?table_id=table_02
?table_id=comedor_01
```

---

## 🆘 SI ALGO NO FUNCIONA

### Error: "YOLO not available"
```bash
pip install ultralytics torch torchvision
```

### Error: "OpenCV not found"
```bash
pip install opencv-python
```

### Error: "Cannot open video device"
- Verifica que otra app no usa la cámara
- Intenta `?source=1` en lugar de `?source=0`

### Stream muy lento
```
- Aumenta inference_stride a 5 o 10
- Reduce resolution: ?width=320&height=240
- Cierra otras apps
```

### No detecta objetos
```
- Verifica iluminación (buena luz natural)
- Acerca objetos a la cámara
- Baja confianza: ?confidence=0.20
```

---

## 📱 INTEGRACIÓN CON DASHBOARD

En `apps/dashboard/src/...` puedes:

```javascript
// Obtener status
fetch("/api/v1/demo/table-service/status")
  .then(r => r.json())
  .then(data => console.log("Stream URL:", data.stream_url));

// Mostrar stream en img/video
<img src="http://localhost:8000/api/v1/demo/table-service/stream?source=0" />

// Polling de análisis cada 2 segundos
setInterval(async () => {
  const res = await fetch("/api/v1/demo/table-service/analyze");
  const analysis = await res.json();
  
  // Mostrar alertas
  if (analysis.active_alerts.length > 0) {
    console.log("⚠️ ALERTA:", analysis.active_alerts[0].message);
  }
  
  // Actualizar estado visual
  updateTableUI(analysis);
}, 2000);
```

---

## ✅ CHECKLIST DE ÉXITO

- [ ] `test_table_service_webcam.py` corre sin errores
- [ ] Detección YOLO funciona (ve objetos en consola)
- [ ] Monitor procesa frames (ve "Estado:", "Personas:", etc)
- [ ] Eventos se registran en timeline
- [ ] Alertas funcionan cuando falta servicio
- [ ] API sirve `/api/v1/demo/table-service/stream` 
- [ ] Stream MJPEG visible en navegador
- [ ] JSON response tiene structure correcta

---

## 📝 PRÓXIMOS PASOS

1. **Guardar eventos en BD:** Integrar con `RestaurantMVPService`
2. **WebSocket:** Alertas en tiempo real al dashboard
3. **Multi-mesa:** Monitor independiente por cada `table_id`
4. **Predicción:** ETA para desocupación de mesa
5. **Tracking:** Asociar gestos con misma persona entre frames

---

## 📞 REFERENCIA RÁPIDA

| Tarea | Comando |
|-------|---------|
| Prueba local | `python test_table_service_webcam.py` |
| API servidor | `python run_api_with_service_monitor.py` |
| Docs interactivos | `http://localhost:8000/docs` |
| Stream en vivo | `http://localhost:8000/api/v1/demo/table-service/stream` |
| Análisis JSON | `POST http://localhost:8000/api/v1/demo/table-service/analyze` |
| Ver config | [services/vision/table_service_monitor.py](services/vision/table_service_monitor.py#L50) |

¡Éxito! 🚀
