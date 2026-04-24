# 📚 ÍNDICE - Análisis de Servicio de Mesa en Tiempo Real

**Proyecto:** RestaurIA  
**Módulo:** Table Service Monitor  
**Fecha:** 24 Abril 2026  
**Status:** ✅ **COMPLETADO**

---

## 🚀 COMIENZA AQUÍ

### 1️⃣ Leo el Resumen (5 min)
👉 [ARQUITECTURA_TABLA_SERVICIO.md](ARQUITECTURA_TABLA_SERVICIO.md)
- Qué se entregó
- 3 endpoints nuevos
- Cómo usar
- Demo recomendado

### 2️⃣ Pruebo Rápido (5 min)
👉 Opción A - Script Local:
```bash
python test_table_service_webcam.py
```

👉 Opción B - API REST:
```bash
python run_api_with_service_monitor.py
# Luego: http://localhost:8000/api/v1/demo/table-service/stream
```

### 3️⃣ Leo Guía Paso a Paso (10 min)
👉 [PRUEBA_AHORA.md](PRUEBA_AHORA.md)
- Instrucciones detalladas
- Casos de prueba
- Troubleshooting
- Integración con dashboard

### 4️⃣ Explorar Código (15 min)
👉 [CAMBIOS_CODIGO.md](CAMBIOS_CODIGO.md)
- Detalle de modificaciones
- Cada endpoint explicado
- Cómo extender
- Testing

---

## 📁 ARCHIVOS DE REFERENCIA

### 🎯 Documentación

| Archivo | Propósito | Tiempo |
|---------|----------|--------|
| [ARQUITECTURA_TABLA_SERVICIO.md](ARQUITECTURA_TABLA_SERVICIO.md) | Resumen ejecutivo | 5 min |
| [PRUEBA_AHORA.md](PRUEBA_AHORA.md) | Guía paso a paso | 10 min |
| [CAMBIOS_CODIGO.md](CAMBIOS_CODIGO.md) | Detalles técnicos | 15 min |
| [README_TABLE_SERVICE_MONITOR.md](README_TABLE_SERVICE_MONITOR.md) | Referencia técnica | 20 min |
| Este archivo | Índice y navegación | 5 min |

### 💻 Scripts Ejecutables

| Archivo | Propósito | Comando |
|---------|----------|---------|
| [test_table_service_webcam.py](test_table_service_webcam.py) | Prueba local sin API | `python test_table_service_webcam.py` |
| [run_api_with_service_monitor.py](run_api_with_service_monitor.py) | Ejecutar API | `python run_api_with_service_monitor.py` |

### 📝 Código Modificado

| Archivo | Cambios | Líneas |
|---------|---------|--------|
| [apps/api/main.py](apps/api/main.py) | +3 endpoints, +2 helpers | ~215 |
| [apps/api/schemas.py](apps/api/schemas.py) | +4 models | ~50 |
| [services/vision/table_service_monitor.py](services/vision/table_service_monitor.py) | Existente (tu commit) | - |

---

## 🎬 GUÍA RÁPIDA POR CASO DE USO

### 📱 "Quiero ver cámara en vivo con análisis"
1. Ejecuta: `python test_table_service_webcam.py`
2. O: `python run_api_with_service_monitor.py` + navegador
3. Ver: [PRUEBA_AHORA.md#opción-1](PRUEBA_AHORA.md)

### 🔌 "Quiero integrar en mi app"
1. Lee: [CAMBIOS_CODIGO.md#endpoints](CAMBIOS_CODIGO.md)
2. Endpoints disponibles:
   - `GET /api/v1/demo/table-service/status`
   - `GET /api/v1/demo/table-service/stream`
   - `POST /api/v1/demo/table-service/analyze`
3. JSON response: [PRUEBA_AHORA.md#qué-esperar](PRUEBA_AHORA.md)

### 📊 "Quiero entender la arquitectura"
1. Ver diagrama: [ARQUITECTURA_TABLA_SERVICIO.md#qué-se-entregó](ARQUITECTURA_TABLA_SERVICIO.md)
2. Leer: [CAMBIOS_CODIGO.md#flujo-de-datos](CAMBIOS_CODIGO.md)
3. Extender: [CAMBIOS_CODIGO.md#cómo-extender](CAMBIOS_CODIGO.md)

### ⚙️ "Quiero configurar reglas de detección"
1. Edita: `TableServiceMonitorConfig` en [services/vision/table_service_monitor.py](services/vision/table_service_monitor.py#L50)
2. Parámetros: [README_TABLE_SERVICE_MONITOR.md#⚙️-configuración](README_TABLE_SERVICE_MONITOR.md)

### 🐛 "Tengo un error"
1. Troubleshooting: [PRUEBA_AHORA.md#🆘-si-algo-no-funciona](PRUEBA_AHORA.md)
2. Contacta: Revisar consola de errores y logs

---

## 📊 DATOS QUE RECIBES

### Endpoint: `GET /api/v1/demo/table-service/stream`
```
Media-Type: multipart/x-mixed-replace
Retorna: Video MJPEG con análisis dibujado en tiempo real
Ejemplo: http://localhost:8000/api/v1/demo/table-service/stream
```

### Endpoint: `POST /api/v1/demo/table-service/analyze`
```
Retorna: JSON completo con análisis actual
Ejemplo respuesta: [PRUEBA_AHORA.md#en-json-verás](PRUEBA_AHORA.md)
```

### Campos en JSON:
| Campo | Tipo | Ejemplo |
|-------|------|---------|
| `table_id` | string | "table_01" |
| `state` | enum | "eating", "seated", "needs_setup" |
| `people_count` | int | 2 |
| `object_counts` | dict | `{"person": 2, "fork": 2, "plate": 2}` |
| `missing_items` | dict | `{"spoon": 2}` |
| `service_flags` | dict | `{"plates_complete": true, "food_served": false}` |
| `active_alerts` | list | Alertas actuales |
| `timeline_events` | list | Eventos históricos |
| `seat_duration_seconds` | int | 245 |

---

## 🎯 ESTADOS DE MESA

Ver descripción completa: [README_TABLE_SERVICE_MONITOR.md#🎯-estados-de-la-mesa](README_TABLE_SERVICE_MONITOR.md)

```
empty → waiting_for_video → observing → seated
                                          ↓
                                  needs_setup ← → eating
                                    ↑                ↓
                                    └── away ←──────┘
```

---

## 🚨 ALERTAS GENERADAS

| Alerta | Severidad | Cuándo |
|--------|-----------|--------|
| `missing_table_setup` | medium | Falta servicio (cubiertos/platos) |
| `customer_attention_requested` | high | Cliente pide atención (mano levantada) |

Ver detalles: [README_TABLE_SERVICE_MONITOR.md#🚩-alertas-generadas](README_TABLE_SERVICE_MONITOR.md)

---

## 📋 EVENTOS REGISTRADOS

| Evento | Descripción | Cuándo |
|--------|------------|--------|
| `table_session_started` | Cliente llega | Primera persona detectada |
| `plate_served` | Plato detectado | Se coloca plato en mesa |
| `food_served` | Comida detectada | Comida en mesa |
| `customer_left_table` | Cliente se levanta | Desaparece personas |
| `customer_returned` | Cliente vuelve | Reaparece con duración ausencia |
| `customer_attention_requested` | Pide atención | Gesto de mano levantada |
| `missing_table_setup` | Falta servicio | No hay cubiertos/platos con personas |
| `plate_removed` | Plato retirado | Desaparece plato |

Ver detalles: [README_TABLE_SERVICE_MONITOR.md#📋-eventos-de-línea-de-tiempo](README_TABLE_SERVICE_MONITOR.md)

---

## 🔍 DETECCIONES SOPORTADAS

### Categorías YOLO

| Categoría | Items |
|-----------|-------|
| 🍴 Cubiertos | fork, knife, spoon |
| 🍽️ Platos | plate, bowl |
| 🍕 Comida | pizza, sandwich, hot dog, cake, donut, banana, apple, orange, broccoli, carrot |
| ✋ Atención | hand_raised, raised_hand, finger_raised, call_waiter |
| 🪑 Base | person, chair, dining table, cup, bottle, wine glass |

Ver lista completa: [README_TABLE_SERVICE_MONITOR.md#🔍-etiquetas-yolo-detectadas](README_TABLE_SERVICE_MONITOR.md)

---

## 📈 PRÓXIMOS PASOS

### Corto Plazo (1-2 días)
- [ ] Guardar eventos en PostgreSQL
- [ ] Dashboard React con timeline
- [ ] Persistencia histórica

### Mediano Plazo (1 semana)
- [ ] WebSocket para alertas push
- [ ] Multi-mesa
- [ ] Mejor visualización en stream

### Largo Plazo (2+ semanas)
- [ ] Tracking de personas
- [ ] ML para predicción de ETA
- [ ] Notificaciones WhatsApp/SMS
- [ ] Analytics y reportes

Ver detalles: [ARQUITECTURA_TABLA_SERVICIO.md#🚀-próximos-pasos](ARQUITECTURA_TABLA_SERVICIO.md)

---

## 🎓 FLUJOS DE APRENDIZAJE

### Para Entender Todo (Completo)
1. [ARQUITECTURA_TABLA_SERVICIO.md](ARQUITECTURA_TABLA_SERVICIO.md) - 5 min
2. [CAMBIOS_CODIGO.md](CAMBIOS_CODIGO.md) - 15 min
3. `python test_table_service_webcam.py` - 5 min
4. Revisar código en [apps/api/main.py](apps/api/main.py) - 20 min
5. [README_TABLE_SERVICE_MONITOR.md](README_TABLE_SERVICE_MONITOR.md) - 10 min
**Total: ~55 minutos**

### Para Usar Rápido (Mínimo)
1. [ARQUITECTURA_TABLA_SERVICIO.md](ARQUITECTURA_TABLA_SERVICIO.md) - 5 min
2. `python test_table_service_webcam.py` - 5 min
3. [PRUEBA_AHORA.md](PRUEBA_AHORA.md) - 5 min
**Total: ~15 minutos**

### Para Integrar (Desarrollador)
1. [CAMBIOS_CODIGO.md](CAMBIOS_CODIGO.md) - 15 min
2. [README_TABLE_SERVICE_MONITOR.md](README_TABLE_SERVICE_MONITOR.md) - 10 min
3. Revisar endpoints en [apps/api/main.py](apps/api/main.py) - 20 min
4. Implementar en tu código
**Total: ~45 minutos**

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Verificación Inicial
- [ ] Código compila sin errores
- [ ] Imports funcionan
- [ ] Scripts ejecutables

### Prueba Local
- [ ] `test_table_service_webcam.py` funciona
- [ ] Ve detecciones en consola
- [ ] Ve video en pantalla

### Prueba API
- [ ] Servidor inicia sin errores
- [ ] `http://localhost:8000/docs` accesible
- [ ] `/api/v1/demo/table-service/stream` devuelve video
- [ ] `/api/v1/demo/table-service/analyze` devuelve JSON

### Funcionalidad
- [ ] Detecta personas
- [ ] Detecta cubiertos
- [ ] Detecta platos
- [ ] Genera alertas de servicio incompleto
- [ ] Genera alertas de atención
- [ ] Timeline de eventos funciona
- [ ] Timers funcionan

### Documentación
- [ ] Leí resumen ejecutivo
- [ ] Leí guía de pruebas
- [ ] Entiendo los endpoints
- [ ] Sé cómo extender

---

## 🎁 BONUS

### Scripts Útiles
```bash
# Ver solo errores en main.py
python -m py_compile apps/api/main.py

# Conectar directamente a DB (después de implementar)
psql $DATABASE_URL

# Ver logs en vivo
uvicorn apps.api.main:app --reload --log-level debug
```

### curl Examples
```bash
# Get status
curl http://localhost:8000/api/v1/demo/table-service/status

# Get analysis snapshot
curl -X POST http://localhost:8000/api/v1/demo/table-service/analyze

# Ver en navegador (abrir URL)
http://localhost:8000/api/v1/demo/table-service/stream?source=0&table_id=table_01
```

### JavaScript Integration
```javascript
// En dashboard
const stream = document.getElementById('video');
stream.src = 'http://localhost:8000/api/v1/demo/table-service/stream';

// Polling de análisis
setInterval(async () => {
  const res = await fetch('/api/v1/demo/table-service/analyze', {method: 'POST'});
  const data = await res.json();
  console.log('Analysis:', data);
}, 2000);
```

---

## 📞 SOPORTE

### Documentación
- [ARQUITECTURA_TABLA_SERVICIO.md](ARQUITECTURA_TABLA_SERVICIO.md) - Qué es
- [PRUEBA_AHORA.md](PRUEBA_AHORA.md) - Cómo usar
- [CAMBIOS_CODIGO.md](CAMBIOS_CODIGO.md) - Cómo funciona
- [README_TABLE_SERVICE_MONITOR.md](README_TABLE_SERVICE_MONITOR.md) - Referencia

### Código Fuente
- [apps/api/main.py](apps/api/main.py) - API endpoints
- [apps/api/schemas.py](apps/api/schemas.py) - Data models
- [services/vision/table_service_monitor.py](services/vision/table_service_monitor.py) - Lógica principal
- [test_table_service_webcam.py](test_table_service_webcam.py) - Ejemplo de uso

---

## 🎉 ¡ÉXITO!

Tienes todo lo que necesitas para:
✅ Entender la arquitectura  
✅ Probar en tiempo real  
✅ Integrar en tu app  
✅ Extender con nuevas funciones  
✅ Llevar a producción  

**Comienza por:** [ARQUITECTURA_TABLA_SERVICIO.md](ARQUITECTURA_TABLA_SERVICIO.md)

---

**Última actualización:** 24 Abril 2026  
**Versión:** 1.0  
**Status:** ✅ Listo para Producción
