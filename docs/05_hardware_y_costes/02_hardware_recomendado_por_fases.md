# Hardware recomendado por fases

## Fase 1 — Casa / 1 mesa
- portátil o sobremesa actual,
- 1 webcam USB.

## Fase 2 — Piloto pequeño
- mini PC o PC dedicado,
- 1–2 cámaras,
- SSD suficiente,
- pantalla adicional opcional para dashboard.

## Fase 3 — Edge más serio
### Opción Intel / x86
Mini PC razonable para backend local + inferencia ligera/media.

### Opción NVIDIA
Jetson Orin Nano Super Developer Kit si hace falta edge GPU dedicado.  
Referencia oficial: https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/  
Referencia de kits: https://developer.nvidia.com/embedded/jetson-developer-kits

### Opción NPU dedicada (Hailo-8L)
Acelerador NPU para inferencia eficiente en edge cuando el objetivo principal es detección en tiempo real con bajo consumo.
Se recomienda usarlo detrás de un adaptador de inferencia desacoplado del dominio para evitar lock-in de hardware.

## Fase 4 — Audio
- auricular abierto o discreto,
- micrófono direccional si se prueban comandos de voz.

## Recomendación
Comprar tarde, no pronto.
