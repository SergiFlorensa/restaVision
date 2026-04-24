# Riesgos y mitigaciones

## Riesgo técnico
### Falsos positivos
Mitigación:
- thresholds prudentes,
- alertas graduales,
- validación humana.

### Oclusiones y mala cámara
Mitigación:
- buena ubicación,
- iluminación,
- zonas bien definidas,
- pruebas por escenario.

### Latencia
Mitigación:
- edge processing,
- optimización,
- reducción de resolución cuando proceda.

## Riesgo de producto
### Saturación de alertas
Mitigación:
- priorización,
- severidades,
- diseño UX minimalista.

### Baja utilidad operativa
Mitigación:
- construir junto a escenarios reales de decisión.

## Riesgo legal / reputacional
### Uso excesivo de vídeo
Mitigación:
- privacidad por diseño,
- documentación,
- finalidad delimitada.

### Acusaciones erróneas de impago
Mitigación:
- hablar siempre de “riesgo” o “anomalía”, nunca de certeza automática.
- en el MVP solo se implementan alertas operativas como `long_session_attention`,
- no se automatiza la etiqueta "impago" ni se infiere intencion de clientes.
