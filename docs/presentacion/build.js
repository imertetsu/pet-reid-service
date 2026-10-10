// Builds the 6-slide presentation of the final project (plus 2 hidden backup slides).
// Usage: npm install && node build.js  ->  presentacion-ml.pptx
const path = require("path");
const pptxgen = require("pptxgenjs");
const NOTES = require("./notes");

const ROOT = path.resolve(__dirname, "..", "..");
const img = (p) => path.join(ROOT, "data", p);
const OUT = path.join(__dirname, "presentacion-ml.pptx");

// Replace with the GitHub URL once the repository is published
const REPO_URL = "github.com/imertetsu/pet-reid-service";

// Palette: deep pine (dominant), mint-gray surfaces and an amber accent
const THEME = {
  name: "Pets Location",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2A2F", lt1: "FFFFFF", dk2: "1F4E4A", lt2: "EEF4F2",
    accent1: "E8963B", accent2: "2F7A6F", accent3: "9AA5A3",
    accent4: "C8553D", accent5: "4C9A8A", accent6: "5F6E6C",
    hlink: "2F7A6F", folHlink: "5F6E6C",
  },
};

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
  pres.title = "Encontré una mascota";
  pres.author = "Imer Vladimir Coaguila Patiño";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const COL = THEME.colors;

  // ---- layouts ----------------------------------------------------------
  pres.defineSlideMaster({
    title: "TITLE_DARK",
    background: { color: COL.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.9, w: 6.9, h: 1.7, fontSize: 44, bold: true, color: COL.lt1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "subtitle", type: "body", x: 0.7, y: 3.75, w: 6.9, h: 1.0, fontSize: 20, color: COL.accent1, align: "left", valign: "top", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "meta", type: "body", x: 0.7, y: 5.55, w: 6.9, h: 1.1, fontSize: 14, color: COL.lt2, align: "left", valign: "top", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: COL.lt1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 32, bold: true, color: COL.dk2, valign: "middle", margin: 0 }, text: "" } },
      { text: { text: "Encontré una mascota · Proyecto final de Machine Learning", options: { x: 0.6, y: 6.95, w: 9, h: 0.35, fontSize: 10, color: COL.accent6, margin: 0 } } },
    ],
    slideNumber: { x: 12.2, y: 6.95, w: 0.5, h: 0.35, fontSize: 10, color: COL.accent6, align: "right" },
  });

  // ---- 1. title -----------------------------------------------------------
  pres.addSection({ title: "Introducción" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Introducción" });
  s.addText("Encontré una mascota", { placeholder: "title" });
  s.addText(
    [
      { text: "Reidentificación de perros por foto", options: { breakLine: true } },
      { text: "con ResNet50 y PCA + LDA" },
    ],
    { placeholder: "subtitle" }
  );
  s.addText(
    [
      { text: "Imer Vladimir Coaguila Patiño", options: { bold: true, breakLine: true } },
      { text: "Maestría en Ingeniería de Software · Módulo de Machine Learning", options: { breakLine: true } },
      { text: "Microservicio para la plataforma Pets Location" },
    ],
    { placeholder: "meta" }
  );
  const covers = ["images/test/dfn_0912/01.jpg", "images/test/dfn_0234/00.jpg", "images/test/dfn_1086/01.jpg", "images/test/dfn_0521/00.jpg"];
  covers.forEach((p, i) => {
    const x = 8.35 + (i % 2) * 2.35;
    const y = 1.25 + Math.floor(i / 2) * 2.35;
    s.addShape(pres.shapes.OVAL, { x: x - 0.06, y: y - 0.06, w: 2.17, h: 2.17, fill: { color: COL.accent1 }, line: { type: "none" }, objectName: `cover-ring-${i + 1}` });
    s.addImage({ path: img(p), x, y, w: 2.05, h: 2.05, rounding: true, altText: "Foto de perro del dataset DogFaceNet", objectName: `cover-dog-${i + 1}` });
  });
  s.addText("Fotos: DogFaceNet (CC BY 4.0)", { x: 8.3, y: 6.15, w: 4.5, h: 0.3, fontSize: 10, color: COL.lt2, margin: 0, isTextBox: true });
  s.addNotes(NOTES[0]);

  // ---- 2. how it works ------------------------------------------------------
  pres.addSection({ title: "Solución" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Solución" });
  s.addText("Una foto basta para sugerir al dueño y ubicar el collar", { placeholder: "title" });
  const steps = [
    ["Foto", "Quien encuentra al perro sube una foto de su cara"],
    ["ResNet50", "Red ya entrenada con más de 1 millón de fotos: convierte la foto en 2.048 números"],
    ["PCA + LDA", "Lo que se entrenó: aprende qué distingue a cada perro y deja 128 números"],
    ["Galería", "Mide la distancia a los 85 perros registrados y muestra los 3 más parecidos"],
    ["Decisión", "Si el más parecido está bajo el umbral, sugiere al dueño y ubica el collar"],
  ];
  const cardW = 2.26, gap = 0.2, cardY = 1.45, cardH = 2.85;
  steps.forEach(([head, desc], i) => {
    const x = 0.6 + i * (cardW + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cardY, w: cardW, h: cardH, rectRadius: 0.12, fill: { color: COL.lt2 }, line: { type: "none" }, objectName: `step-card-${i + 1}` });
    s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: cardY + 0.2, w: 0.6, h: 0.6, fill: { color: i === 2 ? COL.accent1 : COL.dk2 }, line: { type: "none" }, objectName: `step-circle-${i + 1}` });
    s.addText(String(i + 1), { x: x + 0.2, y: cardY + 0.2, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: COL.lt1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `step-number-${i + 1}` });
    s.addText(head, { x: x + 0.2, y: cardY + 0.95, w: cardW - 0.4, h: 0.45, fontSize: 18, bold: true, color: COL.dk2, margin: 0, isTextBox: true, objectName: `step-head-${i + 1}` });
    s.addText(desc, { x: x + 0.2, y: cardY + 1.45, w: cardW - 0.4, h: 1.25, fontSize: 14, color: COL.dk1, valign: "top", margin: 0, isTextBox: true, objectName: `step-desc-${i + 1}` });
  });
  // Real example from the test split
  const exY = 4.65, d = 1.95;
  s.addImage({ path: img("images/test/dfn_0098/02.jpg"), x: 0.6, y: exY, w: d, h: d, rounding: true, altText: "Foto de consulta", objectName: "example-query" });
  s.addImage({ path: img("images/test/dfn_0098/00.jpg"), x: 10.75, y: exY, w: d, h: d, rounding: true, altText: "Foto registrada en la galería", objectName: "example-match" });
  s.addText(
    [
      { text: "Ejemplo real del conjunto de prueba", options: { fontSize: 12, color: COL.accent6, breakLine: true } },
      { text: "distancia 0,74  <  umbral 0,94", options: { fontSize: 28, bold: true, color: COL.dk2, breakLine: true } },
      { text: "Posible coincidencia: Rufo · collar GPS-003-RUFO", options: { fontSize: 16, color: COL.dk1, breakLine: true } },
      { text: " ", options: { fontSize: 6, breakLine: true } },
      { text: "Distancia: qué tan distintas son dos fotos (menor = más parecidas; no es un porcentaje).", options: { fontSize: 12, color: COL.accent6, breakLine: true } },
      { text: "Umbral: distancia máxima para aceptar la coincidencia, calculada con validación.", options: { fontSize: 12, color: COL.accent6 } },
    ],
    { x: 2.85, y: exY, w: 7.6, h: d, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "example-text" }
  );
  s.addNotes(NOTES[1]);

  // ---- 3. architecture: training and use ------------------------------------
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Solución" });
  s.addText("Se entrena una vez y se usa en cada búsqueda", { placeholder: "title" });
  // Two lanes: offline training (top) and online use (bottom). Colors tell what is trained.
  const boxW = 2.14, boxGap = 0.35, boxH = 1.4;
  const colX = (i) => 0.6 + i * (boxW + boxGap);
  const AMBER_SOFT = "FBE7CF";
  const box = (x, y, w, kind, head, desc, name) => {
    const style = {
      data: { fill: COL.lt2, line: { type: "none" }, head: COL.dk2, desc: COL.dk1 },
      reused: { fill: COL.dk2, line: { type: "none" }, head: COL.lt1, desc: COL.lt2 },
      trained: { fill: AMBER_SOFT, line: { color: COL.accent1, width: 1.5 }, head: COL.dk2, desc: COL.dk1 },
    }[kind];
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: boxH, rectRadius: 0.1, fill: { color: style.fill }, line: style.line, objectName: `${name}-box` });
    s.addText(
      [
        { text: head, options: { fontSize: 15, bold: true, color: style.head, breakLine: true } },
        { text: desc, options: { fontSize: 12, color: style.desc } },
      ],
      { x: x + 0.12, y: y + 0.1, w: w - 0.24, h: boxH - 0.2, valign: "top", margin: 0, paraSpaceAfter: 3, isTextBox: true, objectName: `${name}-text` }
    );
  };
  const arrowRight = (x, y, name) =>
    s.addShape(pres.shapes.LINE, { x, y, w: boxGap - 0.08, h: 0, line: { color: COL.accent6, width: 1.5, endArrowType: "triangle" }, objectName: name });
  const arrowDown = (x, y1, y2, name) =>
    s.addShape(pres.shapes.LINE, { x, y: y1, w: 0, h: y2 - y1, line: { color: COL.accent1, width: 1.5, dashType: "dash", endArrowType: "triangle" }, objectName: name });

  const laneTrainY = 1.75, laneUseY = 4.1;
  s.addText("1. Entrenamiento (una sola vez)", { x: 0.6, y: 1.3, w: 6, h: 0.38, fontSize: 15, bold: true, color: COL.dk2, margin: 0, isTextBox: true, objectName: "lane-train-label" });
  const train = [
    ["data", "Fotos", "338 perros, 2.517 fotos de DogFaceNet"],
    ["reused", "ResNet50", "Ya entrenada con ImageNet: foto → 2.048 números"],
    ["trained", "PCA", "Resume 2.048 → 512 números, quitando lo repetido"],
    ["trained", "LDA", "Usa las etiquetas: aprende qué distingue a cada perro → 128"],
    ["data", "Umbral", "Calibrado con los 113 perros de validación"],
  ];
  train.forEach(([kind, head, desc], i) => {
    box(colX(i), laneTrainY, boxW, kind, head, desc, `train-${i + 1}`);
    if (i < train.length - 1) arrowRight(colX(i) + boxW + 0.04, laneTrainY + boxH / 2, `train-arrow-${i + 1}`);
  });

  s.addText("2. Uso (cada vez que se sube una foto)", { x: 0.6, y: 3.65, w: 4.8, h: 0.38, fontSize: 15, bold: true, color: COL.dk2, margin: 0, isTextBox: true, objectName: "lane-use-label" });
  const wideW = 2 * boxW + boxGap;
  box(colX(0), laneUseY, boxW, "data", "Foto encontrada", "Cara del perro (PNG o JPEG)", "use-1");
  box(colX(1), laneUseY, boxW, "reused", "ResNet50", "La misma red: 2.048 números", "use-2");
  box(colX(2), laneUseY, wideW, "trained", "PCA + LDA aprendidos", "Aplica lo aprendido en el entrenamiento → 128 números", "use-3");
  box(colX(4), laneUseY, boxW, "data", "Búsqueda y decisión", "Compara con 85 perros → top-3. Si distancia ≤ umbral: dueño y collar", "use-4");
  arrowRight(colX(0) + boxW + 0.04, laneUseY + boxH / 2, "use-arrow-1");
  arrowRight(colX(1) + boxW + 0.04, laneUseY + boxH / 2, "use-arrow-2");
  arrowRight(colX(3) + boxW + 0.04, laneUseY + boxH / 2, "use-arrow-3");
  // What was learned on top is reused below
  [2, 3, 4].forEach((i) => arrowDown(colX(i) + boxW / 2, laneTrainY + boxH + 0.05, laneUseY - 0.05, `learned-arrow-${i}`));
  s.addText("se aplica lo aprendido", { x: colX(2) + boxW / 2 + 0.15, y: 3.4, w: 2.3, h: 0.3, fontSize: 11, italic: true, color: COL.accent6, margin: 0, isTextBox: true, objectName: "learned-label" });

  // Legend and plain-language definitions
  const legendY = 5.78;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: legendY + 0.05, w: 0.3, h: 0.22, rectRadius: 0.04, fill: { color: AMBER_SOFT }, line: { color: COL.accent1, width: 1.5 }, objectName: "legend-trained" });
  s.addText("Se entrena (PCA + LDA)", { x: 1.0, y: legendY, w: 2.6, h: 0.32, fontSize: 12, color: COL.dk1, margin: 0, isTextBox: true, objectName: "legend-trained-text" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.7, y: legendY + 0.05, w: 0.3, h: 0.22, rectRadius: 0.04, fill: { color: COL.dk2 }, line: { type: "none" }, objectName: "legend-reused" });
  s.addText("Se reutiliza sin entrenar (ResNet50)", { x: 4.1, y: legendY, w: 3.6, h: 0.32, fontSize: 12, color: COL.dk1, margin: 0, isTextBox: true, objectName: "legend-reused-text" });
  s.addText(
    [
      { text: "Distancia: ", options: { bold: true, color: COL.dk2 } },
      { text: "qué tan distintas son dos fotos (menor = más parecidas; no es un porcentaje).   ", options: {} },
      { text: "Umbral: ", options: { bold: true, color: COL.dk2 } },
      { text: "distancia máxima para aceptar una coincidencia.", options: {} },
    ],
    { x: 0.6, y: 6.25, w: 12.1, h: 0.45, fontSize: 12, color: COL.accent6, valign: "middle", margin: 0, isTextBox: true, objectName: "definitions" }
  );
  s.addNotes(NOTES[2]);

  // ---- 3. results ----------------------------------------------------------
  pres.addSection({ title: "Resultados" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Resultados" });
  s.addText("PCA + LDA supera a la línea base en 10 puntos de Top-1", { placeholder: "title" });
  s.addChart(
    pres.charts.BAR,
    [{ name: "Top-1 en prueba", labels: ["Línea base: ResNet50", "ResNet50 + siamesa", "ResNet50 + PCA + LDA"], values: [73.2, 76.0, 83.2] }],
    {
      x: 0.6, y: 1.4, w: 7.6, h: 5.3, barDir: "col", barGapWidthPct: 60,
      chartColors: ["9AA5A3", "4C9A8A", "E8963B"],
      showTitle: true, title: "Top-1 en prueba: % de veces que el perro correcto sale primero", titleFontSize: 14, titleColor: "1B2A2F", titleFontFace: "+mn-lt",
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: '0.0"%"', dataLabelFontSize: 16, dataLabelFontBold: true, dataLabelColor: "1B2A2F", dataLabelFontFace: "+mn-lt",
      valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25, valAxisLabelFormatCode: '0"%"',
      valAxisLabelColor: "5F6E6C", catAxisLabelColor: "1B2A2F", valAxisLabelFontSize: 12, catAxisLabelFontSize: 13,
      valAxisLabelFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt",
      valGridLine: { color: "E1E7E5", size: 1 }, catGridLine: { style: "none" },
      showLegend: false, objectName: "top1-chart",
    }
  );
  const stats = [
    ["+10 pts", "más aciertos en primer lugar (Top-1) que la línea base sin entrenar"],
    ["93 %", "Recall@3: el perro correcto está entre los 3 candidatos que se muestran"],
  ];
  stats.forEach(([big, label], i) => {
    const y = 1.45 + i * 1.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.6, y, w: 4.1, h: 1.75, rectRadius: 0.12, fill: { color: COL.lt2 }, line: { type: "none" }, objectName: `stat-card-${i + 1}` });
    s.addText(big, { x: 8.85, y: y + 0.12, w: 3.6, h: 0.85, fontSize: 44, bold: true, color: i === 0 ? COL.accent1 : COL.dk2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true, objectName: `stat-number-${i + 1}` });
    s.addText(label, { x: 8.85, y: y + 0.95, w: 3.6, h: 0.7, fontSize: 14, color: COL.dk1, valign: "top", margin: 0, isTextBox: true, objectName: `stat-label-${i + 1}` });
  });
  s.addText(
    [
      { text: "Datos: ", options: { bold: true, color: COL.dk2 } },
      { text: "DogFaceNet, 4.168 fotos reales de 564 perros, separados por perro: 338 entrenamiento, 113 validación y 113 prueba (nunca vistos, 674 consultas). Método y umbral elegidos solo con validación." },
    ],
    {
    x: 8.6, y: 5.4, w: 4.1, h: 1.35, fontSize: 13, color: COL.accent6, valign: "top", margin: 0, isTextBox: true, objectName: "results-caption",
  });
  s.addNotes(NOTES[3]);

  // ---- 4. conclusions and limitations ---------------------------------------
  pres.addSection({ title: "Cierre" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Cierre" });
  s.addText("Conclusiones y limitaciones", { placeholder: "title" });
  const panels = [
    {
      x: 0.6, head: "Conclusiones", mark: "✓", markColor: COL.dk2,
      items: [
        "Un método clásico (LDA) supera a la línea base en 10 puntos de Top-1",
        "Con 338 perros, LDA rinde más que la cabeza siamesa entrenada por gradiente",
        "Comparación confiable: partición por perro, umbral de validación y prueba única",
      ],
    },
    {
      x: 6.75, head: "Limitaciones", mark: "!", markColor: COL.accent4,
      items: [
        "El umbral aceptó 8,8 % de perros sin registro; el objetivo era 5 %",
        "Necesita la cara centrada: no detecta ni alinea rostros",
        "Confunde perros casi idénticos (error real):",
      ],
    },
  ];
  const panelW = 5.95, panelY = 1.45, panelH = 5.25;
  panels.forEach((panel, p) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: panel.x, y: panelY, w: panelW, h: panelH, rectRadius: 0.12, fill: { color: COL.lt2 }, line: { type: "none" }, objectName: `panel-${p + 1}` });
    s.addText(panel.head, { x: panel.x + 0.3, y: panelY + 0.25, w: panelW - 0.6, h: 0.5, fontSize: 22, bold: true, color: COL.dk2, fontFace: THEME.headFontFace, margin: 0, isTextBox: true, objectName: `panel-head-${p + 1}` });
    panel.items.forEach((item, i) => {
      const y = panelY + 1.0 + i * 0.95;
      s.addShape(pres.shapes.OVAL, { x: panel.x + 0.3, y: y + 0.05, w: 0.5, h: 0.5, fill: { color: panel.markColor }, line: { type: "none" }, objectName: `panel-${p + 1}-mark-${i + 1}` });
      s.addText(panel.mark, { x: panel.x + 0.3, y: y + 0.05, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: COL.lt1, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `panel-${p + 1}-mark-text-${i + 1}` });
      s.addText(item, { x: panel.x + 0.95, y, w: panelW - 1.25, h: 0.8, fontSize: 15, color: COL.dk1, valign: "middle", margin: 0, isTextBox: true, objectName: `panel-${p + 1}-item-${i + 1}` });
    });
  });
  // Left panel: headline numbers
  s.addText(
    [
      { text: "83,2 %", options: { fontSize: 36, bold: true, color: COL.accent1, fontFace: THEME.headFontFace } },
      { text: "  Top-1     ", options: { fontSize: 15, color: COL.dk1 } },
      { text: "93,0 %", options: { fontSize: 36, bold: true, color: COL.dk2, fontFace: THEME.headFontFace } },
      { text: "  Recall@3", options: { fontSize: 15, color: COL.dk1 } },
    ],
    { x: 0.9, y: 5.25, w: panelW - 0.6, h: 0.9, valign: "middle", margin: 0, isTextBox: true, objectName: "conclusion-numbers" }
  );
  // Right panel: real error pair (query vs. suggested dog)
  const pairY = 5.0, pairD = 1.4;
  s.addImage({ path: img("images/test/dfn_0396/02.jpg"), x: 7.75, y: pairY, w: pairD, h: pairD, rounding: true, altText: "Foto de consulta de un perro registrado", objectName: "error-query" });
  s.addImage({ path: img("images/test/dfn_0429/00.jpg"), x: 9.75, y: pairY, w: pairD, h: pairD, rounding: true, altText: "Perro distinto sugerido por error", objectName: "error-suggested" });
  s.addText("→", { x: 9.2, y: pairY, w: 0.55, h: pairD, fontSize: 24, bold: true, color: COL.accent4, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "error-arrow" });
  s.addText(
    [
      { text: "Otro perro", options: { bold: true, breakLine: true } },
      { text: "distancia 0,76" },
    ],
    { x: 11.3, y: pairY, w: 1.25, h: pairD, fontSize: 12, color: COL.accent6, valign: "middle", margin: 0, isTextBox: true, objectName: "error-caption" }
  );
  s.addNotes(NOTES[4]);

  // ---- 5. repository and how to run -----------------------------------------
  s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Cierre" });
  s.addText("Repositorio y ejecución", { x: 0.7, y: 0.6, w: 11.9, h: 0.9, fontSize: 36, bold: true, color: COL.lt1, fontFace: THEME.headFontFace, margin: 0, isTextBox: true, objectName: "closing-title" });
  s.addText(
    [
      { text: REPO_URL, options: { fontSize: 24, bold: true, color: COL.accent1, breakLine: true } },
      { text: "Versión final: tag v1.0 · README con instalación, entrenamiento, evaluación y ejecución", options: { fontSize: 14, color: COL.lt2 } },
    ],
    { x: 0.7, y: 1.65, w: 11.9, h: 1.1, valign: "top", margin: 0, isTextBox: true, objectName: "closing-repo" }
  );
  const commands = [
    ["python run.py", "abre http://127.0.0.1:9100 (API en /docs)"],
    ["docker compose up -d --build", "mismo servicio en un contenedor"],
    ["python -m pytest -q", "28 pruebas: válido, difícil, inválido y flujo completo"],
  ];
  commands.forEach(([cmd, desc], i) => {
    const y = 2.95 + i * 1.0;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.7, y, w: 5.4, h: 0.7, rectRadius: 0.08, fill: { color: "173B38" }, line: { type: "none" }, objectName: `command-box-${i + 1}` });
    s.addText(cmd, { x: 0.95, y, w: 5.0, h: 0.7, fontSize: 16, color: COL.lt1, fontFace: "Courier New", valign: "middle", margin: 0, isTextBox: true, objectName: `command-${i + 1}` });
    s.addText(desc, { x: 6.4, y, w: 6.2, h: 0.7, fontSize: 15, color: COL.lt2, valign: "middle", margin: 0, isTextBox: true, objectName: `command-desc-${i + 1}` });
  });
  s.addText(
    [
      { text: "¡Gracias!", options: { fontSize: 22, bold: true, color: COL.lt1, fontFace: THEME.headFontFace, breakLine: true } },
      { text: "Imer Vladimir Coaguila Patiño · Maestría en Ingeniería de Software", options: { fontSize: 13, color: COL.lt2 } },
    ],
    { x: 0.7, y: 6.25, w: 11.9, h: 0.9, valign: "top", margin: 0, isTextBox: true, objectName: "closing-thanks" }
  );
  s.addNotes(NOTES[5]);

  // ---- backup slides (hidden: only shown if someone asks) ---------------------
  pres.addSection({ title: "Respaldo" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Respaldo" });
  s.hidden = true;
  s.addText("Respaldo: glosario", { placeholder: "title" });
  const glossary = [
    ["ResNet50", "Red neuronal ya entrenada con más de 1 millón de fotos (ImageNet). Aquí no se entrena: convierte cada foto en 2.048 números."],
    ["Transfer learning", "Reutilizar un modelo entrenado por otros en lugar de entrenar uno desde cero."],
    ["PCA", "Resume muchos números en menos (2.048 → 512) sin usar etiquetas: quita lo redundante."],
    ["LDA", "Usa las etiquetas: aprende qué distingue a cada perro (512 → 128). Junta las fotos del mismo perro y separa las de perros distintos."],
    ["Red siamesa", "Red de deep learning que aprende con pares de fotos: acerca las del mismo perro y aleja las de perros distintos."],
    ["Línea base", "Método simple sin entrenamiento, para saber si el modelo aporta algo."],
    ["Distancia", "Qué tan distintas son dos fotos: menor = más parecidas. No es un porcentaje."],
    ["Umbral", "Distancia máxima para aceptar una coincidencia; se calculó con validación."],
    ["Top-1", "% de veces que el perro correcto sale en primer lugar."],
    ["Recall@3", "% de veces que el perro correcto está entre los 3 candidatos mostrados."],
    ["FAR", "% de perros no registrados a los que se les sugiere un dueño por error."],
    ["Validación / prueba", "Validación: elegir método y umbral. Prueba: examen final, usado una sola vez."],
  ];
  const tableCell = (text, isTerm) => ({
    text,
    options: { bold: isTerm, color: isTerm ? COL.dk2 : COL.dk1, fill: { color: isTerm ? COL.lt2 : COL.lt1 } },
  });
  [glossary.slice(0, 6), glossary.slice(6)].forEach((rows, t) => {
    s.addTable(rows.map(([term, meaning]) => [tableCell(term, true), tableCell(meaning, false)]), {
      x: 0.6 + t * 6.15, y: 1.45, w: 5.95, colW: [1.55, 4.4], fontSize: 13, valign: "middle",
      border: { type: "solid", pt: 0.75, color: "D7E2DF" }, margin: 0.06, objectName: `glossary-table-${t + 1}`,
    });
  });
  s.addNotes("Diapositiva oculta de respaldo: no aparece al presentar. Si preguntan por un término, ir aquí (en la vista del moderador, escribir el número 7 y Enter).");

  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Respaldo" });
  s.hidden = true;
  s.addText("Respaldo: preguntas frecuentes", { placeholder: "title" });
  const faq = [
    ["¿Por qué PCA + LDA?", "La red siamesa apenas superaba a la línea base en validación: con 338 perros se sobreajusta. LDA, método clásico de reconocimiento de individuos, calcula la solución con una fórmula y ganó en validación."],
    ["¿Por qué ResNet50?", "Extractor estándar con buen equilibrio entre precisión y costo, disponible en Keras y en CPU. Se fijó para comparar métodos sobre el mismo extractor."],
    ["¿Cómo evitaste hacer trampa?", "Cada perro está en una sola partición. Método y umbral se eligieron con validación; la prueba se usó una sola vez."],
    ["¿Por qué el FAR fue 8,8 % y no 5 %?", "El umbral se calibró con otros perros; con perros nuevos varía. No se corrigió con la prueba para no sesgar el resultado."],
    ["¿Funciona con cualquier foto?", "Solo con la cara del perro centrada: no hay detector de rostros. No sirve para gatos."],
    ["¿Qué mejorarías?", "Más perros (+2 puntos cada vez que se duplican), un detector de rostros y extractores más modernos."],
  ];
  faq.forEach(([question, answer], i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 6.15, y = 1.45 + row * 1.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 5.95, h: 1.6, rectRadius: 0.1, fill: { color: COL.lt2 }, line: { type: "none" }, objectName: `faq-card-${i + 1}` });
    s.addText(
      [
        { text: question, options: { bold: true, color: COL.dk2, fontSize: 15, breakLine: true } },
        { text: answer, options: { color: COL.dk1, fontSize: 13 } },
      ],
      { x: x + 0.25, y: y + 0.12, w: 5.45, h: 1.36, valign: "top", margin: 0, paraSpaceAfter: 4, isTextBox: true, objectName: `faq-text-${i + 1}` }
    );
  });
  s.addNotes("Diapositiva oculta de respaldo con las preguntas más probables. Hay más preguntas y respuestas en las notas de la diapositiva 6.");

  await pres.writeFile({ fileName: OUT });
  console.log("OK " + OUT);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
