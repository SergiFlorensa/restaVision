# Mejoras alcanzables para un TFG sin hardware caro

## Criterio rector
RestaurIA debe evolucionar como un producto avanzado, pero ejecutable con:
- portatil personal,
- camara del movil para pruebas,
- posible webcam/camara externa economica,
- software libre o gratuito,
- datos sinteticos o datos propios anonimizados.

No se consideran validas para el MVP:
- GPU dedicada obligatoria,
- servicios cloud de pago,
- APIs de pago,
- hardware edge especializado,
- dependencias cerradas que bloqueen una futura venta.

## Conclusion de investigacion
La via mas potente no es intentar competir con grandes sistemas de IA por fuerza bruta. La via alcanzable es combinar:
- vision artificial ligera,
- simulacion de servicio,
- teoria de colas,
- process mining sobre eventos,
- aprendizaje online con feedback,
- explicabilidad de recomendaciones,
- UI tipo consola operativa.

Esto permite construir un producto sofisticado con pocos recursos porque el valor aparece en la traduccion:

```text
observacion -> evento -> estado operativo -> decision -> feedback -> aprendizaje
```

## Mejoras priorizadas

### 1. Simulador de servicio de sala
Objetivo: probar noches de servicio sin depender de una camara perfecta.

Implementacion alcanzable:
- motor propio con `random`, `dataclasses` y reloj simulado, o `SimPy` si se acepta nueva dependencia MIT,
- escenarios: dia normal, viernes noche, falta de personal, cola alta, muchas limpiezas,
- salida: eventos compatibles con la API actual.

Valor para TFG:
- permite demostrar el copiloto en condiciones repetibles,
- genera datasets sinteticos,
- mide si el motor recomienda bien antes de tener vision perfecta.

Referencia:
- SimPy, simulacion de eventos discretos en Python, licencia MIT: https://simpy.readthedocs.io/

### 2. Motor de explicabilidad operativa
Objetivo: que cada recomendacion diga por que existe y que impacto espera.

Implementacion alcanzable:
- razones estructuradas,
- puntuacion por factores,
- contrafactual simple:

```text
Si limpias Mesa 3 ahora, Grupo 2 podria sentarse en 4-6 min.
Si no actuas, espera estimada 12-15 min.
```

Valor para TFG:
- mejora confianza del encargado,
- evita caja negra,
- permite medir recomendaciones utiles frente a no utiles.

Referencia:
- Interpretable Machine Learning, Christoph Molnar: https://christophm.github.io/interpretable-ml-book/

### 3. Process mining post-servicio
Objetivo: convertir el historial de eventos en analisis de proceso.

Implementacion alcanzable:
- exportar eventos como log: `case_id`, `activity`, `timestamp`, `resource`,
- detectar cuellos de botella:
  - mesa pendiente de limpieza demasiado tiempo,
  - grupos esperando sin promesa actualizada,
  - fase de cuenta lenta,
  - atencion tardia.

Sin dependencia externa al principio:
- agrupar eventos con SQL/Python,
- calcular tiempos entre eventos,
- generar resumen despues del servicio.

Valor para empresa:
- no solo ayuda durante el servicio,
- tambien explica donde se pierde dinero/tiempo.

Referencia:
- Process Mining Handbook, open access: https://link.springer.com/book/10.1007/978-3-031-08848-3

### 4. Aprendizaje online con feedback
Objetivo: que el sistema mejore con el uso del encargado.

Implementacion alcanzable:
- usar feedback ya existente: `hecho`, `ignorado`, `no util`,
- ajustar pesos del motor de decision con reglas online:
  - si recomendaciones de limpieza se aceptan, subir peso,
  - si avisos de atencion se ignoran, bajar sensibilidad,
  - si ETA falla, corregir estimador.

Dependencia opcional:
- `river` para aprendizaje online y drift, licencia BSD-3.

Valor para TFG:
- demuestra aprendizaje sin entrenar redes grandes,
- encaja con datos de flujo continuo.

Referencia:
- River, online ML en Python: https://github.com/online-ml/river

### 5. Teoria de colas aplicada a espera prometida
Objetivo: mejorar el Promise Engine con formulas simples y defendibles.

Implementacion alcanzable:
- llegada de grupos por minuto,
- tiempo medio de mesa,
- tasa de liberacion estimada,
- Little's Law como baseline conceptual,
- ajuste por capacidad de mesa y limpieza pendiente.

Valor para producto:
- promesas de espera mas realistas,
- menos frustracion del cliente,
- mejor defensa academica.

Referencias:
- From theORy to application, operaciones e investigacion operativa, CC BY: https://open.umn.edu/opentextbooks/textbooks/from-theory-to-application-learning-to-optimize-with-operations-research-in-an-interactive-way
- Curso Python de forecasting en OR, open access: https://link.springer.com/article/10.1007/s43069-022-00179-z

### 6. Vision ligera por evidencias, no por deteccion perfecta
Objetivo: extraer senales utiles con CPU.

Implementacion alcanzable:
- ROIs manuales por mesa,
- sustraccion de fondo,
- movimiento por zona,
- conteo aproximado de personas,
- deteccion de mesa vacia/ocupada,
- estabilidad temporal para evitar parpadeo de estados.

Dependencias ya alineadas:
- OpenCV,
- modelos pequenos opcionales,
- ONNX Runtime o OpenVINO solo si hace falta optimizar CPU.

Valor para TFG:
- se ve computer vision real,
- no depende de entrenar un modelo enorme,
- se puede probar con movil/webcam.

Referencias:
- OpenCV documentation: https://docs.opencv.org/
- Computer Vision: Algorithms and Applications, Richard Szeliski: https://szeliski.org/Book/
- ONNX Runtime, MIT: https://github.com/microsoft/onnxruntime
- OpenVINO, Apache-2.0: https://github.com/openvinotoolkit/openvino

### 7. Calibrador visual de sala
Objetivo: que el usuario configure mesa y ROI sin tocar codigo.

Implementacion alcanzable:
- snapshot desde camara,
- editor de poligonos o cajas,
- guardar configuracion en Postgres,
- previsualizar que mesa alimenta cada ROI.

Valor para empresa:
- evita depender del desarrollador,
- hace el producto instalable en otro local.

### 8. Modo voz local para acciones cortas
Objetivo: prototipo de pinganillo/agente de voz sin cloud.

Implementacion alcanzable:
- comandos cerrados:
  - "mesa tres lista",
  - "grupo dos sentado",
  - "revisar mesa cinco",
  - "cuenta mesa cuatro",
- reconocimiento local con Vosk o whisper.cpp,
- convertir texto a accion API.

No se plantea audio continuo comercial en MVP. Se plantea demo local y controlada.

Referencias:
- Vosk offline speech recognition: https://github.com/alphacep/vosk-api
- whisper.cpp, MIT: https://github.com/ggml-org/whisper.cpp
- voice2json, comandos offline por gramatica, MIT: https://voice2json.org/

### 9. Shadow mode
Objetivo: evaluar sin molestar al encargado.

Implementacion alcanzable:
- el sistema recomienda pero no obliga,
- se compara recomendacion frente a accion humana posterior,
- se calcula precision operativa:
  - recomendacion aceptada,
  - recomendacion ignorada,
  - recomendacion tardia,
  - recomendacion que redujo espera.

Valor para piloto real:
- bajo riesgo,
- genera evidencia de utilidad para convencer a la empresa.

### 10. Dashboard post-servicio
Objetivo: mostrar valor economico y operativo despues del turno.

Implementacion alcanzable:
- resumen de cola,
- mesas bloqueadas,
- tiempos medios por fase,
- recomendaciones utiles,
- momentos de saturacion,
- estimacion de espera evitada.

Valor para empresa:
- convierte el TFG en producto comprable,
- habla el idioma del encargado y del gerente.

## Roadmap recomendado de implementacion

### Sprint A: simulador y escenarios
1. Crear `services/simulator`.
2. Generar eventos de entrada, mesa, cuenta, limpieza y salida.
3. Endpoint para lanzar escenario demo.
4. Dashboard con boton `Simular servicio`.

### Sprint B: explicabilidad y contrafactual
1. Extender `DecisionRecommendation.metadata`.
2. Guardar `score_breakdown`.
3. Mostrar impacto esperado en UI.

### Sprint C: process mining minimo
1. Exportar eventos de un turno.
2. Calcular tiempos entre fases.
3. Generar informe post-servicio.

### Sprint D: vision ligera por ROI
1. Calibrador de ROI.
2. Movimiento/ocupacion por mesa.
3. Observaciones estables hacia el dominio.

### Sprint E: voz local
1. Grammar cerrada de comandos.
2. Adaptador texto -> accion operativa.
3. Demo local sin cloud.

## Bibliografia y recursos legales recomendados

### ML y fundamentos
- Mathematics for Machine Learning, PDF oficial: https://mml-book.github.io/book/mml-book.pdf
- An Introduction to Statistical Learning with Python, PDF oficial: https://hastie.su.domains/ISLP/ISLP_website.pdf
- Understanding Machine Learning, PDF oficial para uso personal: https://www.cs.huji.ac.il/~shais/UnderstandingMachineLearning/understanding-machine-learning-theory-algorithms.pdf
- Machine Learning Systems, open access: https://mlsysbook.ai/

### Computer vision y deep learning
- Computer Vision: Algorithms and Applications, descarga oficial: https://szeliski.org/Book/
- Dive into Deep Learning, libro abierto: https://d2l.ai/
- OpenCV docs: https://docs.opencv.org/

### Operaciones, colas y procesos
- Process Mining Handbook, open access: https://link.springer.com/book/10.1007/978-3-031-08848-3
- From theORy to application, PDF CC BY: https://open.umn.edu/opentextbooks/textbooks/from-theory-to-application-learning-to-optimize-with-operations-research-in-an-interactive-way
- Forecasting: Principles and Practice: https://otexts.com/fpp3/

### Software libre aplicable
- SimPy: https://simpy.readthedocs.io/
- River: https://github.com/online-ml/river
- Mesa: https://mesa.readthedocs.io/
- ONNX Runtime: https://github.com/microsoft/onnxruntime
- OpenVINO: https://github.com/openvinotoolkit/openvino
- Vosk: https://github.com/alphacep/vosk-api
- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- voice2json: https://voice2json.org/

## Propuesta de siguiente paso
El siguiente paso con mejor relacion impacto/esfuerzo es implementar el **simulador de servicio**.

Motivo:
- no requiere hardware,
- permite demos potentes,
- genera datos,
- valida el motor de decision,
- hace visible el valor del producto incluso si la camara falla.

Definicion de done:
- boton o endpoint para lanzar escenario,
- eventos persistidos,
- cola y mesas cambian automaticamente,
- recomendaciones se recalculan,
- informe basico de resultados.
