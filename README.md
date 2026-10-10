# Encontré una mascota · Reidentificación de perros por foto

Proyecto final del módulo de **Machine Learning** — Maestría en Ingeniería de Software.
**Estudiante:** Imer Vladimir Coaguila Patiño.

Microservicio independiente que forma parte de la visión de *Pets Location* (proyecto de tesis). Quien encuentra un perro sube una foto de su rostro. El servicio la compara con la galería de mascotas registradas y devuelve los **3 candidatos más parecidos**. Si el primero pasa el umbral, sugiere la identidad y muestra la **última ubicación del collar**. Si no, responde **"sin coincidencia"**.

> Las fotos son reales (DogFaceNet). Los nombres de las mascotas, dueños, collares y ubicaciones son **ficticios**. Es un prototipo académico, no validado para uso real.

## Entregables

| Entregable | Ubicación |
|---|---|
| Informe técnico (PDF) | [`docs/informe/informe-tecnico.pdf`](docs/informe/informe-tecnico.pdf) |
| Presentación (PPTX, con notas del orador) | [`docs/presentacion/presentacion-ml.pptx`](docs/presentacion/presentacion-ml.pptx) |
| Resultados de evaluación | [`artifacts/metrics.json`](artifacts/metrics.json) y [`figures/`](figures/) |
| Modelo entrenado | [`artifacts/pca_lda.npz`](artifacts/pca_lda.npz), [`artifacts/siamese_head.weights.h5`](artifacts/siamese_head.weights.h5), [`artifacts/calibration.json`](artifacts/calibration.json) |
| Dataset seleccionado | [`data/`](data/) (fotos, `manifest.json`, `dataset_info.json`) |
| Versión final | tag `v1.0` |

## Resultados principales (prueba: 113 perros nunca vistos, 674 consultas)

| Método | Qué se entrena | Top-1 | Recall@3 | Identificación con umbral | Desconocidos aceptados | ROC-AUC |
|---|---|---|---|---|---|---|
| ResNet50 + distancia (**línea base**) | nada | 73,2 % | 86,5 % | 42,3 % | 5,6 % | 0,969 |
| ResNet50 + cabeza siamesa (contrastiva) | capa densa 2048→256 | 76,0 % | 90,4 % | 49,9 % | 6,5 % | 0,987 |
| **ResNet50 + PCA + LDA** ★ | PCA 512 + LDA 128 | **83,2 %** | **93,0 %** | **55,3 %** | 8,8 % | **0,992** |

★ Método elegido **en validación** (mayor Top-1) antes de ejecutar la prueba. La prueba se evaluó una sola vez.

- La métrica principal es **Top-1**: si el perro correcto es el primer candidato, el que la interfaz destaca.
- **PCA + LDA mejora 10 puntos de Top-1 sobre la línea base** usando las mismas características de ResNet50.
- El umbral se calibró en validación para aceptar ≤ 5 % de perros sin registro. En prueba la tasa subió a 8,8 % (19 de 215 consultas): el umbral no se transfiere perfectamente a perros nuevos. Es una limitación reportada, no corregida con la prueba.
- **Casos difíciles:** el 16,8 % de los perros registrados no sale primero ni siquiera con PCA + LDA. En los errores aceptados predominan perros de pelaje y raza casi idénticos (p. ej. negro con fuego) y fotos rotadas por la alineación del dataset; 14 de ellos se aceptan con la identidad equivocada. Muchos perros registrados quedan sobre el umbral y se rechazan: la identificación con umbral es 55,3 %, frente a 83,2 % de Top-1. `figures/errors_test.png` muestra ejemplos.

El detalle completo está en `artifacts/metrics.json` y en las figuras de `figures/`.

## Iniciar el sistema (sin reentrenar)

El repositorio incluye las fotos seleccionadas, los modelos entrenados, la galería y los resultados. Requiere **Python 3.11**.

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Abrir **http://127.0.0.1:9100**. La API interactiva está en **/docs**. Otro puerto: `python run.py --port 9200`.

El primer arranque descarga los pesos de ResNet50 de Keras (unos 94 MB), así que necesita Internet. Después funciona sin conexión.

**Problemas frecuentes en Windows**

- *TensorFlow falla al instalarse por rutas largas:* cree el venv en una ruta corta, por ejemplo `python -m venv D:\venvs\petreid`, o habilite *Long Paths* en Windows.
- *`CERTIFICATE_VERIFY_FAILED` con antivirus que inspecciona HTTPS (p. ej. Avast):* `pip install --use-feature=truststore -r requirements.txt`.

### Con Docker

```bash
docker compose up -d --build
```

Mismo puerto (9100). La imagen descarga los pesos de ResNet50 durante la construcción.

Si un antivirus o proxy inspecciona HTTPS y la construcción falla con `CERTIFICATE_VERIFY_FAILED`, copie su certificado raíz en `certs/` con extensión `.crt`. En Avast es `C:\ProgramData\Avast Software\Avast\wscert.pem`. Esos archivos no se suben al repositorio.

## Probar la interfaz

1. **Buscar:** elige una foto de ejemplo y pulsa **Buscar coincidencia**. Los ejemplos se agrupan en registrado, sin registro y error del modelo.
2. Revisa el candidato sugerido, su distancia frente al umbral y la **última ubicación simulada** del collar. **Simular nueva señal** mueve el collar.
3. Cambia el **método** (línea base, siamesa, PCA + LDA) para comparar con la misma foto.
4. **Registrar mascota:** sube 2–4 fotos de un perro y luego búscalo con otra foto.
5. **Modelo y resultados:** tablas de prueba y validación, y figuras.
6. **Límites:** qué no hace el sistema.

Subidas aceptadas: PNG o JPEG, máximo 5 MB y 6 megapíxeles, mínimo 96 px por lado. El servicio **no detecta ni alinea rostros**: recorta el centro de la imagen.

## Reproducir datos, entrenamiento y evaluación

Con el servidor detenido:

```bash
python -m app.prepare_data --archive ruta/DogFaceNet_224resized.zip
python -m app.features      # características de ResNet50 en caché (~7 min en CPU)
python -m app.train         # entrena siamesa y PCA+LDA, calibra umbrales en validación
python -m app.evaluate      # evaluación única en prueba + figuras
python -m app.gallery       # galería de la demo
python -m pytest -q
python run.py
```

`--download` reemplaza a `--archive` y descarga el ZIP de Zenodo.

## Dataset

- **Fuente:** *DogFaceNet_224resized* (Mougeot, Li y Jia, 2019). Zenodo, DOI [10.5281/zenodo.12578449](https://doi.org/10.5281/zenodo.12578449), licencia **CC BY 4.0**. Contiene 1.393 perros y 8.363 caras alineadas de 224×224. Se verifica su MD5.
- **Preparación** (semilla 42, `app/prepare_data.py`):
  - Se eliminan 4 identidades que compartían una foto con otra etiqueta y 99 duplicados exactos o casi exactos dentro de cada perro.
  - Se conservan los perros con ≥ 6 fotos (564) y como máximo 10 fotos por perro.
- **Partición por identidad** (ningún perro aparece en dos particiones; `tests/test_protocol.py` lo verifica):

| Partición | Perros | Uso |
|---|---|---|
| Entrenamiento | 338 (2.517 fotos) | ajustar PCA + LDA y la cabeza siamesa |
| Validación | 113: 85 registrados + 28 sin registro | elegir hiperparámetros, método y umbral |
| Prueba | 113: 85 registrados + 28 sin registro | evaluación final única |

En validación y prueba, cada perro registrado aporta 2 fotos a la galería; el resto son consultas. Los perros sin registro solo aportan consultas, que el sistema debería rechazar.

## Modelo y línea base

- **Reutilizado sin ajuste:** ResNet50 de `keras.applications` con pesos `imagenet`, sin la capa de clasificación y con *average pooling*, que produce vectores de 2.048 dimensiones. Está congelada en todos los métodos; sus características se calculan una vez y se guardan en caché.
- **Línea base:** las características normalizadas (L2) se comparan por distancia euclídea, equivalente al coseno. No se entrena nada.
- **PCA + LDA** (entrenado, ML clásico): PCA a 512 dimensiones y después análisis discriminante lineal a 128 dimensiones, con *shrinkage*. Aprende la proyección que separa mejor a los 338 perros de entrenamiento.
  - Se probaron 6 configuraciones en validación.
  - Se guarda como una matriz afín (`artifacts/pca_lda.npz`).
- **Cabeza siamesa** (entrenada; enfoque de deep learning por pares, incluido para comparar con el método clásico): capa densa más normalización L2, con pérdida contrastiva sobre pares positivos y negativos. Usa Adam con lr 1e-4 y *early stopping* por Top-1 de validación.
  - Se probaron 4 configuraciones (dimensión 128/256, ReLU o lineal); ganó 256 lineal.
  - Se sobreajusta en pocas épocas: con 338 perros, aprender una proyección completa por gradiente rinde menos que la solución cerrada de LDA.
- **Umbral:** por método, el que maximiza la identificación en validación con ≤ 5 % de perros desconocidos aceptados.

## Estructura

```
app/
  settings.py      configuración, límites de subida
  prepare_data.py  datos -> manifest + particiones
  images.py        validación y preprocesamiento (compartido)
  model.py         ResNet50, cabeza siamesa, embed() de los 3 métodos
  features.py      caché de características
  train.py         entrenamiento + selección + calibración (solo train/val)
  metrics.py       Top-k, identificación, FAR, ROC-AUC, EER, calibración
  protocol.py      vistas galería/consulta
  evaluate.py      evaluación en prueba y figuras
  gallery.py       galería de la demo
  telemetry.py     collar simulado (GNSS, batería, LTE-M/NB-IoT)
  service.py       inferencia y registro
  main.py          API FastAPI
frontend/          HTML, CSS y JS
tests/             protocolo, imágenes, API (válido, difícil, inválido, flujo completo)
data/ artifacts/ figures/
```

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | estado y método por defecto |
| GET | `/api/model` | métodos, umbrales, métricas, dataset |
| GET | `/api/samples` | fotos de ejemplo |
| GET | `/api/gallery` | mascotas registradas con su última ubicación |
| POST | `/api/identify` | `image` (archivo) y `method` opcional → top-3, decisión y ubicación |
| POST | `/api/pets` | `alias`, `owner`, `photos` (2–4) → registra una mascota |
| DELETE | `/api/pets/{id}` | elimina una mascota registrada en la demo |
| POST | `/api/pets/{id}/ping` | simula una nueva señal del collar |

Errores: 413 (más de 5 MB), 415 (no es PNG/JPEG), 422 (imagen pequeña, dañada, método inválido o faltan datos), 404 y 403.

## Pruebas

```bash
python -m pytest -q      # 28 pruebas
```

- **Caso válido:** un perro registrado se identifica, y el top-1 y la distancia de la API coinciden con la evaluación offline para los tres métodos.
- **Casos difíciles:** un perro sin registro, un perro registrado que el modelo confunde y una imagen sin perro.
- **Entradas inválidas:** texto disfrazado de JPEG, imagen de 40 px, archivo mayor de 5 MB, método inexistente, archivo ausente y registro con una sola foto.
- **Flujo completo:** registrar → identificar con otra foto → simular señal → eliminar.

## Limitaciones

- Necesita el **rostro** del perro centrado; no hay detector ni alineación. El modelo se entrenó con caras alineadas: una foto de celular de cuerpo completo cambia de dominio y puede fallar.
- El umbral calibrado en validación aceptó 8,8 % de desconocidos en prueba frente al objetivo de 5 %. En uso real, una coincidencia es solo una sugerencia que debe confirmarse con el dueño.
- 564 perros y 6–10 fotos por perro: un dataset pequeño para aprendizaje métrico.
- La galería de la demo y las ubicaciones son simuladas; la integración con el backend de *Pets Location* (Spring Boot) queda como trabajo futuro.

## Referencias

- Mougeot, G., Li, D. & Jia, S. (2019). *A Deep Learning Approach for Dog Face Verification and Recognition*. PRICAI 2019, LNCS 11672.
- He, K., Zhang, X., Ren, S. & Sun, J. (2016). *Deep Residual Learning for Image Recognition*. CVPR.
- Hadsell, R., Chopra, S. & LeCun, Y. (2006). *Dimensionality Reduction by Learning an Invariant Mapping*. CVPR.
- Belhumeur, P., Hespanha, J. & Kriegman, D. (1997). *Eigenfaces vs. Fisherfaces*. IEEE TPAMI.
