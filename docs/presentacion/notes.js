// Speaker notes (Spanish): script, timing, demo steps and key concepts per slide.
// Total time: about 2 min of slides, 2 min of demo and 1 min of closing.

const slide1 = `TIEMPO: ~20 segundos

QUÉ DECIR:
"Buenos días. Soy Imer Coaguila. Mi proyecto se llama 'Encontré una mascota'. Es un microservicio de Machine Learning para Pets Location, la plataforma de mi tesis, que identifica a un perro perdido a partir de una foto de su cara y muestra dónde está su collar."

CONCEPTOS:
- Microservicio: aplicación independiente que se ejecuta sola y ofrece su función a través de una API (aquí, en el puerto 9100).
- Reidentificación: reconocer al mismo individuo (no la raza) en fotos distintas.
- DogFaceNet: dataset público de fotos reales de caras de perros (CC BY 4.0); las fotos de la portada son de ahí.`;

const slide2 = `TIEMPO: ~50 segundos

QUÉ DECIR:
"El problema: alguien encuentra un perro y no sabe si está registrado ni quién es su dueño.
El sistema tiene dos partes. Arriba, el entrenamiento, que se hace una sola vez: tomé 2.517 fotos de 338 perros de DogFaceNet. ResNet50, una red ya entrenada con ImageNet, convierte cada foto en 2.048 números; esa red no la entreno, la reutilizo (en azul oscuro). Lo que sí entreno está en naranja: PCA resume esos números a 512, y LDA, usando a qué perro pertenece cada foto, aprende qué distingue a un perro de otro y deja 128 números. Al final, con otros 113 perros de validación, calculo el umbral.
Abajo, el uso, que ocurre en cada búsqueda: la foto encontrada pasa por la misma ResNet50 y por el PCA + LDA ya aprendidos, se compara con los 85 perros registrados, se muestran los 3 más parecidos, y si la distancia del primero está bajo el umbral se sugiere al dueño y la ubicación del collar.
En total usé 4.168 fotos de 564 perros, separados por perro en entrenamiento (338), validación (113) y prueba (113). Así, ningún perro de la prueba se vio antes."

CONCEPTOS:
- ResNet50: red neuronal convolucional de 50 capas, entrenada por otros con ImageNet (más de 1 millón de fotos). Aquí NO se entrena: se usa para convertir cada foto en 2.048 números.
- Transfer learning: reutilizar un modelo ya entrenado en lugar de entrenarlo desde cero.
- Vector de características: la "huella numérica" de una foto; fotos parecidas dan vectores cercanos.
- PCA: técnica NO supervisada (no usa etiquetas). Resume 2.048 números en 512, quitando información redundante.
- LDA: técnica SUPERVISADA (usa a qué perro pertenece cada foto). Aprende a juntar las fotos del mismo perro y separar las de perros distintos. Deja 128 números.
- Distancia: qué tan distintas son dos fotos. Pequeña = se parecen. NO es una probabilidad.
- Umbral: distancia máxima para decir "es este perro". Se eligió con validación.
- Partición por perro: evita la fuga de datos (que el mismo perro esté en entrenamiento y en prueba).`;

const slide3 = `TIEMPO: ~50 segundos + DEMO 2 minutos

QUÉ DECIR:
"Comparé tres métodos con el mismo conjunto de prueba.
La línea base, ResNet50 sin entrenar nada, identifica al perro correcto en primer lugar el 73,2 % de las veces.
La red siamesa, un modelo de aprendizaje profundo que aprende comparando pares de fotos, llega a 76 %.
PCA + LDA llega a 83,2 %: 10 puntos más que la línea base. Y el perro correcto está entre los 3 candidatos el 93 % de las veces.
El método y el umbral se eligieron solo con validación; la prueba se evaluó una sola vez, como un examen final.
Ahora lo muestro funcionando."

DEMO (antes de presentar: tener abierto http://127.0.0.1:9100 con "python run.py" o "docker compose up -d"):
1. CASO VÁLIDO: primera foto de la fila 1 ("registrado") y pulsar "Buscar coincidencia".
   Resultado: reconoce a Bella (distancia 0,896 bajo el umbral 0,936).
   Decir: "Encontró a la mascota: la distancia está bajo el umbral. Aquí está su dueño y la última ubicación del collar." Pulsar "Simular nueva señal".
2. PERRO DESCONOCIDO: PRIMERA foto de la fila 2 ("sin registro") y buscar.
   Resultado: "Sin coincidencia" (0,969 sobre el umbral).
   Decir: "Este perro no está registrado. El sistema no inventa un dueño: responde 'sin coincidencia'."
3. LÍMITE (el error relevante que pide el enunciado): SEGUNDA foto de la fila 2 ("sin registro") y buscar.
   Resultado: acepta por error a Pancho (0,822 bajo el umbral).
   Decir: "Aquí falla: este perro no está registrado, pero se parece muchísimo a Pancho, mismo pelaje gris y rizado, y el sistema lo acepta. Es una falsa aceptación, el 8,8 % que mencioné. Por eso la coincidencia es solo una sugerencia que se confirma con el dueño, y se muestran 3 candidatos."
4. (Si hay tiempo) Las fotos "error del modelo" de la fila 3 son perros registrados que el sistema NO reconoce: responde "sin coincidencia" aunque sí están en la galería (falso rechazo).
NO usar como "caso desconocido" la segunda foto de la fila 2: es justamente la que falla.
PLAN B si algo falla: mostrar las capturas del informe (figuras 2, 3 y 4).

CONCEPTOS:
- Línea base: método sencillo sin entrenamiento para comparar; responde "¿mi modelo aporta algo?".
- Top-1 (métrica principal): % de veces que el perro correcto sale PRIMERO.
- Recall@3: % de veces que el perro correcto está entre los 3 candidatos que se muestran.
- Validación: los "exámenes de práctica" para elegir método y umbral.
- Prueba: el "examen final"; se usa una sola vez y no se ajusta nada después.
- Red siamesa: modelo de aprendizaje profundo que recibe DOS fotos, las procesa con la misma red (pesos compartidos) y aprende con pares: "mismo perro: acerca sus vectores; perros distintos: aléjalos". La regla de aprendizaje se llama pérdida contrastiva.
- Por qué se incluyó la siamesa: es el enfoque más usado para verificar si dos fotos son del mismo individuo (rostros, firmas). Sirve para comparar un método clásico (LDA) contra uno de deep learning con las mismas características de ResNet50.`;

const slide4 = `TIEMPO: ~40 segundos

QUÉ DECIR:
"Conclusiones: un método clásico de Machine Learning, LDA, superó a la línea base en 10 puntos. Con solo 338 perros para aprender, LDA calcula la solución directamente con una fórmula, mientras que la red siamesa se sobreajusta en pocas épocas. Y la comparación es confiable porque separé los datos por perro y no ajusté nada con la prueba.
Limitaciones: el umbral aceptó 8,8 % de perros sin registro cuando el objetivo era 5 %, porque no se transfiere perfecto a perros nuevos. El sistema necesita la cara centrada, porque no detecta rostros. Y confunde perros casi idénticos, como estos dos cachorros.
Con más datos mejora: con 100 perros llega a 84 % y con 338 a casi 88 % en validación; son unos 2 puntos cada vez que se duplica la cantidad de perros."

CONCEPTOS:
- FAR (tasa de falsa aceptación): % de perros NO registrados a los que el sistema les sugiere un dueño por error. Es el error más grave.
- Sobreajuste: el modelo memoriza los datos de entrenamiento y le va mal con perros nuevos.
- Shrinkage: ajuste que estabiliza LDA cuando hay pocas fotos para muchas variables.
- Cambio de dominio: el modelo aprendió con caras recortadas y alineadas; una foto de celular de cuerpo completo es distinta y falla más.`;

const slide5 = `TIEMPO: ~20 segundos

QUÉ DECIR:
"Todo el código está en el repositorio con el tag v1.0. Con 'python run.py' o con Docker se levanta el sistema completo, y hay 28 pruebas automatizadas que cubren un caso válido, casos difíciles, entradas inválidas y el flujo completo. Muchas gracias, quedo atento a sus preguntas."

DIAPOSITIVAS DE RESPALDO (ocultas, no se muestran al presentar): 6 = glosario, 7 = preguntas frecuentes. Para ir a una durante la presentación: escribir su número y Enter.

POSIBLES PREGUNTAS (respuestas cortas):

Sobre las decisiones
- ¿Por qué PCA + LDA? ¿Cómo surgió? Primero probé una red siamesa y en validación apenas superaba a la línea base: con 338 perros se sobreajustaba. Busqué un método que aprovechara mejor pocos datos: LDA es el método clásico para reconocer individuos (Fisherfaces, reconocimiento facial). Lo comparé en validación y ganó.
- ¿Por qué PCA antes de LDA? LDA necesita estimar una matriz de 2.048 × 2.048 con solo 2.517 fotos de entrenamiento (5.034 contando la versión volteada de cada una), y eso es inestable. PCA primero reduce a 512 y quita redundancia.
- ¿Por qué ResNet50? Es el extractor estándar más usado: buen equilibrio entre precisión y costo, disponible directamente en Keras y corre en CPU. Con pocos datos conviene reutilizar una red que ya aprendió a ver formas y texturas. No comparé extractores: el objetivo era comparar métodos (línea base, siamesa, LDA) sobre el mismo extractor, para que la diferencia se deba solo al método.
- ¿Probaste otras redes (MobileNet, EfficientNet, ViT)? No: comparé métodos sobre el mismo extractor. Probar otras queda como trabajo futuro; modelos recientes como DINOv2 o CLIP probablemente mejorarían, pero son más pesados.
- ¿Por qué no reentrenaste (fine-tuning) ResNet50? Con 338 perros, reentrenar millones de parámetros se sobreajusta y en CPU tarda mucho. Congelada, sus características se calculan una vez y se entrena en segundos.
- ¿Por qué incluiste la red siamesa? Es el enfoque más usado para verificar si dos fotos son del mismo individuo; sirve para comparar un método clásico contra uno de deep learning.
- ¿Qué se entrenó y qué se reutilizó? Se reutilizó ResNet50 sin cambios; se entrenaron PCA + LDA (modelo final) y la red siamesa (comparación).

Sobre la evaluación
- ¿Cómo evitaste la fuga de datos? Cada perro está en una sola partición; una prueba automática lo verifica. Método y umbral se eligieron con validación; la prueba se usó una sola vez.
- ¿Por qué Top-1 como métrica principal? Porque es lo que ve el usuario: el primer candidato es el que se sugiere.
- ¿Qué es Recall@3? El % de veces que el perro correcto está entre los 3 candidatos mostrados (93 %). La interfaz siempre muestra 3.
- ¿Qué significa la distancia? Qué tan distintas son dos fotos. No es una probabilidad: 0,74 no significa 74 %.
- ¿Qué es el umbral y cómo se calculó? La distancia máxima para aceptar. Se probaron todos los valores en validación y se eligió el que más perros reconoce sin aceptar más de 5 % de perros no registrados.
- ¿Por qué el FAR subió de 5 % a 8,8 %? El umbral se calibró con otros perros (validación); con perros nuevos varía. No se corrigió con la prueba para no hacer trampa.
- ¿Qué es la curva ROC y el AUC? La ROC muestra aciertos frente a falsas alarmas probando todos los umbrales; el AUC es el área bajo la curva (1 = perfecto, 0,5 = azar). PCA + LDA tiene 0,992.

Sobre el sistema
- ¿Funciona con gatos o fotos de cuerpo completo? No: se entrenó con caras de perro recortadas y alineadas. Haría falta un detector de rostros.
- ¿Qué pasa si el perro no está registrado? Si la distancia del más parecido supera el umbral, responde "sin coincidencia" en vez de inventar un dueño.
- ¿Cómo se integraría con Pets Location? Es un microservicio con API REST: el backend solo llama a /api/identify y muestra el resultado en la app.
- ¿Mejora con más datos? Sí: unos 2 puntos de Top-1 cada vez que se duplica la cantidad de perros, cada vez con menos ganancia.
- ¿Qué mejorarías? Más perros, un detector de rostros y probar extractores más modernos.`;

module.exports = [slide1, slide2, slide3, slide4, slide5];
