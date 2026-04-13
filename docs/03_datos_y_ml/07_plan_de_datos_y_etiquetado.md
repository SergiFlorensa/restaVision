# Plan de datos y etiquetado

## Estrategia
Empezar con datos propios, pequeños y controlados:
- una mesa,
- varios escenarios en casa,
- vídeos cortos,
- guión de acciones.

## Escenarios a grabar
- 1 persona se sienta,
- 2 personas comen y se van,
- 1 sale antes y vuelve,
- salida escalonada,
- simulación de pago,
- simulación sin pago,
- limpieza de mesa.

## Anotación
### Herramientas open source
- CVAT: https://docs.cvat.ai/
- Label Studio OSS: https://labelstud.io/label-studio-oss/
- FiftyOne para inspección: https://docs.voxel51.com/

## Etiquetas mínimas
### Objetos
- person
- waiter
- handheld_payment_terminal (si se llega a etiquetar)
- plate / tray (solo si aporta)

### Eventos
- seated
- standing
- enters_zone
- exits_zone
- table_occupied
- table_released

### Estados
- free
- occupied
- dining
- finishing
- cleaning
- ready

## Política
No etiquetar atributos sensibles ni biometría innecesaria.
