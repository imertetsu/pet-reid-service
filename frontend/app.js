// Frontend for the pet re-identification microservice (vanilla JS).

const $ = (selector) => document.querySelector(selector);
const state = { file: null, sampleUrl: null, model: null };

const METRIC_ROWS = [
  ["top1", "Top-1", "pct"],
  ["recall_at_3", "Recall@3", "pct"],
  ["identification_rate", "Tasa de identificación (con umbral)", "pct"],
  ["unknown_far", "Desconocidos aceptados (FAR)", "pct"],
  ["known_wrong_accepted", "Registrados aceptados con otro perro", "int"],
  ["roc_auc", "ROC-AUC (verificación)", "num"],
  ["eer", "EER (verificación)", "pct"],
  ["threshold", "Umbral (de validación)", "num"],
];

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function showError(message) {
  const banner = $("#error-banner");
  banner.textContent = message;
  banner.hidden = !message;
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("No se pudo conectar con el servidor. ¿Está ejecutándose python run.py?");
  }
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(body.detail) ? "Faltan datos obligatorios en la solicitud." : body.detail;
    throw new Error(detail || `Error ${response.status}`);
  }
  return body;
}

// ---- tabs ---------------------------------------------------------------
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${tab.dataset.tab}`));
    if (tab.dataset.tab === "gallery" || tab.dataset.tab === "register") loadGallery();
  });
});

// ---- search -------------------------------------------------------------
function selectInput({ file = null, sampleUrl = null, label }) {
  state.file = file;
  state.sampleUrl = sampleUrl;
  $("#preview").hidden = false;
  $("#preview-img").src = file ? URL.createObjectURL(file) : sampleUrl;
  $("#preview-label").textContent = label;
  $("#search-btn").disabled = false;
}

async function loadSamples() {
  const samples = await api("/api/samples");
  $("#samples").innerHTML = samples
    .map((s, i) => `<button class="sample" data-i="${i}" title="${escapeHtml(s.kind)}">
        <img src="${s.url}" alt="Ejemplo ${escapeHtml(s.kind)}" loading="lazy"><span>${escapeHtml(s.kind)}</span></button>`)
    .join("");
  document.querySelectorAll(".sample").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".sample").forEach((b) => b.classList.remove("selected"));
      button.classList.add("selected");
      const s = samples[button.dataset.i];
      selectInput({ sampleUrl: s.url, label: `Ejemplo: ${s.kind}` });
    });
  });
}

const fileInput = $("#file-input");
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) pickFile(fileInput.files[0]);
});
const dropzone = $("#dropzone");
["dragenter", "dragover"].forEach((e) => dropzone.addEventListener(e, (ev) => { ev.preventDefault(); dropzone.classList.add("drag"); }));
["dragleave", "drop"].forEach((e) => dropzone.addEventListener(e, (ev) => { ev.preventDefault(); dropzone.classList.remove("drag"); }));
dropzone.addEventListener("drop", (ev) => {
  if (ev.dataTransfer.files[0]) pickFile(ev.dataTransfer.files[0]);
});

function pickFile(file) {
  document.querySelectorAll(".sample").forEach((b) => b.classList.remove("selected"));
  selectInput({ file, label: `${file.name} (${(file.size / 1024).toFixed(0)} KB)` });
}

$("#search-btn").addEventListener("click", async () => {
  showError("");
  const button = $("#search-btn");
  button.disabled = true;
  $("#result-empty").hidden = true;
  $("#result").hidden = true;
  $("#result-loading").hidden = false;
  try {
    let blob = state.file;
    if (!blob) blob = await (await fetch(state.sampleUrl)).blob();
    const form = new FormData();
    form.append("image", blob, state.file ? state.file.name : "sample.jpg");
    form.append("method", $("#method").value);
    renderResult(await api("/api/identify", { method: "POST", body: form }));
  } catch (error) {
    $("#result-empty").hidden = false;
    $("#result-empty").textContent = "No se pudo analizar la imagen.";
    showError(error.message);
  } finally {
    $("#result-loading").hidden = true;
    button.disabled = false;
  }
});

function renderResult(result) {
  const decision = $("#decision");
  const best = result.candidates[0];
  if (result.accepted) {
    decision.className = "decision ok";
    decision.innerHTML = `<strong>Posible coincidencia: ${escapeHtml(best.alias)}</strong>
      <small>Dueño: ${escapeHtml(best.owner)} · distancia ${best.distance.toFixed(3)} ≤ umbral ${result.threshold.toFixed(3)} · ${escapeHtml(result.method_label)} · ${result.elapsed_ms} ms</small>`;
    renderLocation(result.match);
  } else {
    decision.className = "decision none";
    decision.innerHTML = `<strong>Sin coincidencia en la galería</strong>
      <small>El candidato más cercano (${escapeHtml(best.alias)}) está a ${best.distance.toFixed(3)} &gt; umbral ${result.threshold.toFixed(3)}. Puede ser un perro no registrado. · ${result.elapsed_ms} ms</small>`;
    $("#location").hidden = true;
  }
  const maxDistance = Math.max(result.threshold * 1.6, ...result.candidates.map((c) => c.distance));
  $("#candidates").innerHTML = result.candidates
    .map((c, i) => `<div class="candidate ${i === 0 && result.accepted ? "best" : ""}">
        <img src="${c.photo}" alt="Foto registrada de ${escapeHtml(c.alias)}">
        <div class="meta"><b>${i + 1}. ${escapeHtml(c.alias)}</b> · ${escapeHtml(c.owner)}<br>
          <small>${escapeHtml(c.source)} · distancia ${c.distance.toFixed(3)} ${c.below_threshold ? "(bajo el umbral)" : "(sobre el umbral)"}</small>
          <div class="bar" title="Distancia frente al umbral">
            <div class="fill ${c.below_threshold ? "" : "over"}" style="width:${(100 * c.distance) / maxDistance}%"></div>
            <div class="threshold" style="left:${(100 * result.threshold) / maxDistance}%"></div>
          </div></div></div>`)
    .join("");
  $("#result").hidden = false;
}

function renderLocation(pet) {
  const box = $("#location");
  const loc = pet.location;
  if (!loc) { box.hidden = true; return; }
  const when = new Date(loc.timestamp).toLocaleString("es");
  const osm = `https://www.openstreetmap.org/?mlat=${loc.latitude}&mlon=${loc.longitude}#map=17/${loc.latitude}/${loc.longitude}`;
  box.innerHTML = `<b>Última ubicación del collar ${escapeHtml(loc.device_id)}</b> <span class="tag">simulada</span>
    <dl><dt>Coordenadas</dt><dd>${loc.latitude}, ${loc.longitude}</dd>
      <dt>Fecha</dt><dd>${when}</dd>
      <dt>Batería</dt><dd>${loc.battery} %</dd>
      <dt>Red</dt><dd>${loc.network}</dd></dl>
    <div class="actions"><a href="${osm}" target="_blank" rel="noopener">Ver en OpenStreetMap</a>
      <button class="secondary" id="ping-btn">Simular nueva señal</button></div>`;
  box.hidden = false;
  $("#ping-btn").addEventListener("click", async () => {
    try {
      const location = await api(`/api/pets/${encodeURIComponent(pet.id)}/ping`, { method: "POST" });
      renderLocation({ ...pet, location });
    } catch (error) {
      showError(error.message);
    }
  });
}

// ---- register -----------------------------------------------------------
$("#photos").addEventListener("change", () => {
  $("#register-previews").innerHTML = [...$("#photos").files]
    .map((f) => `<img src="${URL.createObjectURL(f)}" alt="${escapeHtml(f.name)}">`).join("");
});

$("#register-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const msg = $("#register-msg");
  const button = $("#register-btn");
  const files = [...$("#photos").files];
  msg.hidden = true;
  if (files.length < 2 || files.length > 4) {
    msg.className = "msg error";
    msg.textContent = "Selecciona entre 2 y 4 fotos.";
    msg.hidden = false;
    return;
  }
  const form = new FormData();
  form.append("alias", $("#alias").value);
  form.append("owner", $("#owner").value);
  files.forEach((f) => form.append("photos", f, f.name));
  button.disabled = true;
  button.textContent = "Registrando…";
  try {
    const pet = await api("/api/pets", { method: "POST", body: form });
    msg.className = "msg ok";
    msg.textContent = `${pet.alias} quedó registrado con el collar ${pet.device_id}. Ahora búscalo con otra foto.`;
    ev.target.reset();
    $("#register-previews").innerHTML = "";
    loadGallery();
  } catch (error) {
    msg.className = "msg error";
    msg.textContent = error.message;
  } finally {
    msg.hidden = false;
    button.disabled = false;
    button.textContent = "Registrar";
  }
});

async function loadGallery() {
  try {
    const pets = await api("/api/gallery");
    $("#gallery").innerHTML = pets
      .map((p) => `<div class="pet"><img src="${p.photos[0]}" alt="${escapeHtml(p.alias)}" loading="lazy">
        <div><b>${escapeHtml(p.alias)}</b><small>${escapeHtml(p.owner)}</small><small>${escapeHtml(p.device_id)}</small><small>${escapeHtml(p.source)}</small></div></div>`)
      .join("");
    const registered = pets.filter((p) => p.registered_in_demo);
    $("#registered-list").innerHTML = registered.length
      ? registered.map((p) => `<div class="item"><img src="${p.photos[0]}" alt="${escapeHtml(p.alias)}">
          <div><b>${escapeHtml(p.alias)}</b> · ${escapeHtml(p.owner)}<br><small>${escapeHtml(p.device_id)} · ${p.photos.length} fotos</small></div>
          <button class="secondary" data-id="${escapeHtml(p.id)}">Eliminar</button></div>`).join("")
      : '<p class="empty">Aún no hay mascotas registradas.</p>';
    document.querySelectorAll("#registered-list button").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await api(`/api/pets/${encodeURIComponent(button.dataset.id)}`, { method: "DELETE" });
          loadGallery();
        } catch (error) {
          showError(error.message);
        }
      });
    });
  } catch (error) {
    showError(error.message);
  }
}

// ---- model --------------------------------------------------------------
function format(value, kind) {
  if (value === undefined || value === null) return "—";
  if (kind === "pct") return `${(100 * value).toFixed(1)} %`;
  if (kind === "num") return value.toFixed(3);
  return String(value);
}

function metricsTable(byMethod, selected) {
  const methods = Object.keys(byMethod);
  const header = methods.map((m) => `<th>${escapeHtml(state.model.methods[m])}${m === selected ? " ★" : ""}</th>`).join("");
  const rows = METRIC_ROWS.map(([key, label, kind]) => {
    const cells = methods.map((m) => {
      const r = byMethod[m];
      // Without unknown queries the false acceptance rate is undefined
      const value = key === "unknown_far" && r.retrieval.unknown_queries === 0
        ? null
        : key in r.retrieval ? r.retrieval[key] : r.verification[key];
      return `<td>${format(value, kind)}</td>`;
    }).join("");
    return `<tr><td>${label}</td>${cells}</tr>`;
  }).join("");
  return `<div class="table-wrap"><table><thead><tr><th>Métrica</th>${header}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

async function loadModel() {
  const model = await api("/api/model");
  state.model = model;
  $("#method").innerHTML = Object.entries(model.methods)
    .map(([key, label]) => `<option value="${key}" ${key === model.selected_method ? "selected" : ""}>${escapeHtml(label)}${key === model.selected_method ? " (elegido en validación)" : ""}</option>`)
    .join("");

  const d = model.dataset;
  const t = model.training;
  const splits = d.splits || {};
  $("#model-summary").innerHTML = `
    <p><b>Problema:</b> dada la foto de un perro encontrado, buscar en la galería de mascotas registradas y sugerir la identidad o responder "sin coincidencia".</p>
    <p><b>Dataset:</b> ${escapeHtml(d.source?.name)} (${escapeHtml(d.source?.authors)}, ${escapeHtml(d.source?.license)}).
      ${d.filtering?.eligible_identities} identidades tras filtrar duplicados; partición por identidad:
      entrenamiento ${splits.train?.identities}, validación ${splits.val?.identities}, prueba ${splits.test?.identities} perros.</p>
    <p><b>Línea base:</b> ResNet50 (ImageNet, congelada) + distancia entre vectores normalizados. <b>Nada entrenado.</b></p>
    <p><b>PCA + LDA (ML clásico):</b> ${escapeHtml(t.pca_lda?.pipeline)}; ${t.pca_lda?.selected_config?.lda_components} componentes LDA, entrenado con los perros de entrenamiento (scikit-learn ${escapeHtml(t.versions?.["scikit-learn"])}).</p>
    <p><b>Cabeza siamesa:</b> ${escapeHtml(t.siamese?.head)} con pérdida contrastiva (dimensión ${t.siamese?.selected_config?.embedding_dim}, activación ${t.siamese?.selected_config?.activation ?? "lineal"}, ${escapeHtml(t.siamese?.optimizer?.name)} lr ${t.siamese?.optimizer?.learning_rate}); TensorFlow ${escapeHtml(t.versions?.tensorflow)}.</p>
    <p><b>Método por defecto:</b> ${escapeHtml(model.methods[model.selected_method])} — regla: ${escapeHtml(model.selection_rule)}.</p>`;

  const test = model.test.methods || {};
  const pick = (split) => Object.fromEntries(Object.entries(test).filter(([, v]) => v[split]).map(([m, v]) => [m, v[split]]));
  $("#metrics-test").innerHTML = metricsTable(pick("test"), model.selected_method);
  $("#metrics-val").innerHTML = metricsTable(model.validation, model.selected_method);
}

// ---- init ---------------------------------------------------------------
async function init() {
  try {
    const health = await api("/api/health");
    $("#server-status").textContent = `En línea · ${health.gallery_size} mascotas`;
    $("#server-status").className = "pill ok";
    await Promise.all([loadModel(), loadSamples()]);
  } catch (error) {
    $("#server-status").textContent = "Servidor no disponible";
    $("#server-status").className = "pill down";
    showError(error.message);
  }
}

init();
