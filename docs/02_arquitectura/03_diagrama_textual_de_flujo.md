# Diagrama textual de flujo

```text
[Cámara]
   ↓
[Captura de frames]
   ↓
[Detección + tracking]
   ↓
[Asignación a zonas / mesas]
   ↓
[Extracción de eventos]
   ↓
[Máquina de estados de mesa]
   ↓
[Persistencia de eventos y sesiones]
   ↓
[Predicción / scoring]
   ↓
[Motor de reglas]
   ↓
[Dashboard + alertas]
```

## Ejemplo de secuencia
1. Se detectan 3 personas entrando en zona de mesa 4.
2. Se confirma ocupación.
3. Se crea sesión de mesa.
4. Se acumula tiempo.
5. Uno se levanta y sale de zona.
6. El sistema marca “finalizando” si el patrón encaja.
7. Se actualiza ETA.
8. Dashboard resalta la mesa si hay decisión operativa asociada.
