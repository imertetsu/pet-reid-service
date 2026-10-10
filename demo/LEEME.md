# Archivos para la demo

Fotos listas para subir en la interfaz (http://127.0.0.1:9100). Todas son del **conjunto de prueba** de DogFaceNet: el modelo nunca las vio al entrenar. Resultados verificados con el método por defecto (ResNet50 + PCA + LDA, umbral 0,936).

Para subir una foto: pestaña **Buscar** → recuadro **"Arrastra una imagen o haz clic para elegir"** → elegir el archivo → **Buscar coincidencia**.

## 1. Buscar (`1-buscar/`)

| Archivo | Qué es | Resultado esperado |
|---|---|---|
| `a-registrado-mia.jpg` | Perro registrado | Posible coincidencia: **Mia** (distancia 0,329, coincidencia muy clara) |
| `b-no-registrado.jpg` | Perro que no está en la galería | **Sin coincidencia** (más cercano: Tango, 1,140) |
| `c-error-acepta-otro-perro.jpg` | Perro no registrado, muy parecido a otro | **Error:** acepta a **Pancho** (0,822). Falsa aceptación |
| `d-error-no-lo-reconoce.jpg` | Perro registrado (Simba) | **Error:** Simba sale primero, pero 1,047 supera el umbral. Falso rechazo |

## 2. Registrar una mascota nueva (`2-registrar/`)

1. En **Buscar**, subir `buscar-antes-y-despues.jpg` → **Sin coincidencia** (el perro aún no existe en la galería).
2. En **Registrar mascota**: nombre `Max`, dueño cualquiera, fotos `registrar-foto-1.jpg` y `registrar-foto-2.jpg` → **Registrar**.
3. Volver a **Buscar** y subir otra vez `buscar-antes-y-despues.jpg` → **Posible coincidencia: Max** (distancia 0,516).
4. Al terminar, en **Registrar mascota**, pulsar **Eliminar** para dejar la galería como estaba.

## 3. Entradas inválidas (`3-entradas-invalidas/`)

| Archivo | Resultado esperado |
|---|---|
| `texto-con-extension.jpg` | Error: "El archivo no es una imagen PNG o JPEG válida." |
| `imagen-muy-pequena.png` | Error: "La imagen es muy pequeña: mínimo 96 píxeles por lado." |

## Fotos de ejemplo de la interfaz

Las miniaturas de la pestaña **Buscar** también son fijas (`data/demo_examples.json`):

| Etiqueta | Resultado |
|---|---|
| registrado (1.ª) | Bella (0,896) |
| registrado (2.ª) | Lucas (0,313) |
| no registrado (3.ª y 4.ª) | Sin coincidencia |
| error: otro perro | Acepta a Pancho por error (0,822) |
| error: no lo reconoce | Rechaza a Simba aunque está registrado (1,047) |

Si se registran mascotas nuevas y no se eliminan, los resultados pueden cambiar.
