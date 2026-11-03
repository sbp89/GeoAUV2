/* ============================================================================
   GeoAUV2 — Lógica Interactiva Frontend (GeoMineral AI v2 Web Platform)
   Orquesta los 9 pasos geocientíficos, visor Leaflet, firma espectral en vivo,
   clasificación DZetsaka, magnetometría 3D y persistencia en Supabase.
   ============================================================================ */

const state = {
  catalog: null,
  analysis: null,
  magResult: null,
  lang: "es",
  sampleCaptureMode: false,
  measureMode: false,
  measurePts: [],
  userSamples: [],
  magRotYaw: -0.68,
  magRotPitch: 0.58,
  isDragging3d: false,
  dragLastX: 0,
  dragLastY: 0,
};

const I18N = {
  es: {
    subtitle: "GeoMineral AI · Exploración Multisensor, ML & Magnetometría",
    district: "Distrito:",
    run_btn: "Analizar Cuadrante (Ctrl+R)",
    s1: "Sensores", s2: "Índices", s3: "Stack ML", s4: "IA / ML",
    s5: "Favorab.", s6: "Integrada", s7: "Targets", s8: "Validación", s9: "Reportes",
  },
  en: {
    subtitle: "GeoMineral AI · Multisensor Exploration, ML & Magnetometry",
    district: "District:",
    run_btn: "Run 9-Step Pipeline (Ctrl+R)",
    s1: "Sensors", s2: "Indices", s3: "ML Stack", s4: "AI / ML",
    s5: "Favorab.", s6: "Integrated", s7: "Targets", s8: "Validation", s9: "Reports",
  },
};

let map;
let roiLayer = null;
let rasterOverlay = null;
let targetsLayerGroup;
let fallasLayerGroup;
let depositosLayerGroup;
let anmLayerGroup;
let samplesLayerGroup;
let magLayerGroup;
let measureLayerGroup;

document.addEventListener("DOMContentLoaded", async () => {
  initMap();
  bindUIEvents();
  await Promise.all([checkHealth(), loadCatalog()]);
  await runPipeline();
  await runMagnetometry(true);
});

function initMap() {
  const esriSat = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, attribution: "Tiles &copy; Esri — Sentinel/WorldView" }
  );
  const openTopo = L.tileLayer(
    "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    { maxZoom: 17, attribution: "&copy; OpenTopoMap (SRTM)" }
  );
  const cartoDark = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    { maxZoom: 19, attribution: "&copy; CARTO" }
  );
  const osm = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, attribution: "&copy; OpenStreetMap" }
  );

  map = L.map("map", {
    center: [7.0792, -74.6988],
    zoom: 13,
    layers: [esriSat],
    zoomControl: true,
  });

  L.control.layers(
    {
      "🛰 Satélite Alta Resolución (Esri)": esriSat,
      "⛰ Topográfico Curvas Nivel": openTopo,
      "🌑 Base Cartográfica Oscura": cartoDark,
      "🗺 OpenStreetMap": osm,
    },
    null,
    { position: "topleft" }
  ).addTo(map);

  targetsLayerGroup = L.layerGroup().addTo(map);
  fallasLayerGroup = L.layerGroup().addTo(map);
  depositosLayerGroup = L.layerGroup().addTo(map);
  anmLayerGroup = L.layerGroup().addTo(map);
  samplesLayerGroup = L.layerGroup().addTo(map);
  magLayerGroup = L.layerGroup().addTo(map);
  measureLayerGroup = L.layerGroup().addTo(map);

  map.on("click", onMapClick);
  map.on("mousemove", onMapMouseMove);
}

function bindUIEvents() {
  // Navegación de 9 pasos
  document.querySelectorAll(".step-btn").forEach((btn) => {
    btn.addEventListener("click", () => activateStep(btn.dataset.step));
  });

  // Cambio rápido de capa ráster según el paso activo
  document.getElementById("selRasterLayer").addEventListener("change", updateActiveRasterOverlay);
  document.getElementById("rngOpacity").addEventListener("input", () => {
    if (rasterOverlay) {
      rasterOverlay.setOpacity(Number(document.getElementById("rngOpacity").value) / 100);
    }
  });

  // Toggles vectoriales
  document.getElementById("chkVecTargets").addEventListener("change", (e) => toggleGroup(targetsLayerGroup, e.target.checked));
  document.getElementById("chkVecFallas").addEventListener("change", (e) => toggleGroup(fallasLayerGroup, e.target.checked));
  document.getElementById("chkVecDepositos").addEventListener("change", (e) => toggleGroup(depositosLayerGroup, e.target.checked));
  document.getElementById("chkVecAnm").addEventListener("change", (e) => toggleGroup(anmLayerGroup, e.target.checked));

  // Selector de distrito
  document.getElementById("presetSelect").addEventListener("change", (e) => {
    const p = (state.catalog?.presets || []).find((x) => x.id === e.target.value);
    if (!p) return;
    document.getElementById("inpLat").value = p.lat;
    document.getElementById("inpLon").value = p.lon;
    document.getElementById("inpRoiKm").value = p.roi_size_km;
    document.getElementById("inpDepositModel").value = p.deposit_model;
    document.getElementById("inpSensorMode").value = p.sensor_mode;
    updateDepositDescription();
    runPipeline();
    runMagnetometry(true);
  });

  document.getElementById("inpDepositModel").addEventListener("change", updateDepositDescription);
  document.getElementById("selIndexInspect").addEventListener("change", renderSelectedIndexStats);
  document.getElementById("btnRunPipeline").addEventListener("click", runPipeline);

  // Atajo de teclado Ctrl+R (ejecutar análisis sin recargar el navegador)
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "r") {
      e.preventDefault();
      runPipeline();
    }
  });

  // Tema, Compacto, Idioma
  document.getElementById("btnTheme").addEventListener("click", () => {
    const html = document.documentElement;
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    document.getElementById("btnTheme").textContent = next === "dark" ? "☀" : "🌙";
    if (state.magResult) drawMagnetometry3D();
    if (state.analysis) renderSelectedIndexStats();
  });

  document.getElementById("btnCompact").addEventListener("click", () => {
    document.body.classList.toggle("compact");
    setTimeout(() => map.invalidateSize(), 200);
  });

  document.getElementById("btnLang").addEventListener("click", () => {
    state.lang = state.lang === "es" ? "en" : "es";
    document.getElementById("btnLang").textContent = state.lang.toUpperCase();
    const dict = I18N[state.lang];
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const k = el.getAttribute("data-i18n");
      if (dict[k]) el.textContent = dict[k];
    });
  });

  // Captura interactiva de muestras DZetsaka
  document.getElementById("btnToggleSampleMode").addEventListener("click", () => {
    state.sampleCaptureMode = !state.sampleCaptureMode;
    const btn = document.getElementById("btnToggleSampleMode");
    btn.textContent = state.sampleCaptureMode ? "🎯 Capturar en Mapa: ON" : "🎯 Capturar en Mapa: OFF";
    btn.classList.toggle("btn-primary-outline", state.sampleCaptureMode);
  });

  document.getElementById("btnClearSamples").addEventListener("click", () => {
    state.userSamples = [];
    samplesLayerGroup.clearLayers();
    document.getElementById("sampleCount").textContent = "0";
  });

  // Herramienta medir distancia
  document.getElementById("btnMeasureDist").addEventListener("click", () => {
    state.measureMode = !state.measureMode;
    state.measurePts = [];
    measureLayerGroup.clearLayers();
    const btn = document.getElementById("btnMeasureDist");
    btn.classList.toggle("btn-primary-outline", state.measureMode);
    btn.textContent = state.measureMode ? "📏 Midiendo (Clic 2 pts)" : "📏 Medir";
  });

  // Magnetometría 3D interactiva
  document.getElementById("btnRunMag").addEventListener("click", () => runMagnetometry(false));
  const magCanvas = document.getElementById("mag3dCanvas");
  magCanvas.addEventListener("mousedown", (e) => {
    state.isDragging3d = true;
    state.dragLastX = e.clientX;
    state.dragLastY = e.clientY;
  });
  window.addEventListener("mouseup", () => { state.isDragging3d = false; });
  window.addEventListener("mousemove", (e) => {
    if (!state.isDragging3d || !state.magResult) return;
    const dx = e.clientX - state.dragLastX;
    const dy = e.clientY - state.dragLastY;
    state.dragLastX = e.clientX;
    state.dragLastY = e.clientY;
    state.magRotYaw += dx * 0.012;
    state.magRotPitch = Math.max(0.2, Math.min(1.25, state.magRotPitch + dy * 0.01));
    drawMagnetometry3D();
  });

  // Exportaciones Targets, Reportes y GEE
  document.getElementById("btnExportGeojson").addEventListener("click", () => {
    if (!state.analysis) return;
    downloadTextFile(
      JSON.stringify(state.analysis.targets_geojson, null, 2),
      "targets_geoauv2.geojson",
      "application/geo+json"
    );
  });

  document.getElementById("btnExportCsv").addEventListener("click", () => {
    if (!state.analysis) return;
    downloadTextFile(state.analysis.targets_csv, "targets_geoauv2.csv", "text/csv;charset=utf-8");
  });

  document.getElementById("btnOpenHtmlReport").addEventListener("click", () => {
    if (!state.analysis?.standalone_report_html) return;
    const w = window.open("", "_blank");
    if (w) {
      w.document.open();
      w.document.write(state.analysis.standalone_report_html);
      w.document.close();
    }
  });

  document.getElementById("btnExportGeominer").addEventListener("click", () => {
    const cfg = buildAnalysisPayload();
    downloadTextFile(JSON.stringify(cfg, null, 2), "proyecto_geoauv2.geominer.json", "application/json");
  });

  document.getElementById("btnSaveCloudProject").addEventListener("click", saveProjectToSupabase);
  document.getElementById("selGeeTemplate").addEventListener("change", fetchGeeTemplate);
  document.getElementById("btnCopyGee").addEventListener("click", async () => {
    const code = document.getElementById("geeCodeBox").textContent;
    await navigator.clipboard.writeText(code);
    const btn = document.getElementById("btnCopyGee");
    btn.textContent = "✓ Copiado";
    setTimeout(() => { btn.textContent = "📋 Copiar"; }, 1500);
  });
  document.getElementById("btnDownloadGee").addEventListener("click", () => {
    const code = document.getElementById("geeCodeBox").textContent;
    const tpl = document.getElementById("selGeeTemplate").value;
    downloadTextFile(code, `geoauv2_${tpl}.js`, "application/javascript");
  });

  // Modal Cloud Supabase
  document.getElementById("btnCloudHistory").addEventListener("click", openCloudModal);
  document.getElementById("btnCloseModal").addEventListener("click", () => {
    document.getElementById("cloudModal").classList.add("hidden");
  });
}

function activateStep(stepNum) {
  document.querySelectorAll(".step-btn").forEach((b) => b.classList.toggle("active", b.dataset.step === String(stepNum)));
  document.querySelectorAll(".step-pane").forEach((p) => p.classList.toggle("active", p.id === `step-${stepNum}`));

  // Sincronizar capa ráster sugerida al cambiar de paso
  const sel = document.getElementById("selRasterLayer");
  if (stepNum === "2") sel.value = "idx_arcilla";
  else if (stepNum === "4") sel.value = "ml_clusters";
  else if (stepNum === "5") sel.value = "favorability";
  else if (stepNum === "6" || stepNum === "7") sel.value = "prospectivity";
  updateActiveRasterOverlay();
}

function toggleGroup(group, visible) {
  if (visible) {
    if (!map.hasLayer(group)) map.addLayer(group);
  } else {
    if (map.hasLayer(group)) map.removeLayer(group);
  }
}

async function checkHealth() {
  try {
    const r = await fetch("/api/health");
    const data = await r.json();
    const dot = document.getElementById("cloudStatusDot");
    if (data.supabase?.connected) {
      dot.classList.remove("offline");
      dot.classList.add("online");
    }
  } catch (err) {
    console.warn("Error verificando salud API:", err);
  }
}

async function loadCatalog() {
  const r = await fetch("/api/catalog");
  state.catalog = await r.json();

  const presetSel = document.getElementById("presetSelect");
  presetSel.innerHTML = (state.catalog.presets || [])
    .map((p) => `<option value="${p.id}">${p.name}</option>`)
    .join("");

  const depSel = document.getElementById("inpDepositModel");
  depSel.innerHTML = Object.entries(state.catalog.deposit_models || {})
    .map(([k, v]) => `<option value="${k}">${v.label}</option>`)
    .join("");
  depSel.value = "orogenico_vetas";
  updateDepositDescription();

  // Catálogo YOLO
  const yoloEl = document.getElementById("yoloCatalogList");
  yoloEl.innerHTML = (state.catalog.yolo_models || [])
    .map(
      (y) => `<div class="cluster-card">
        <div class="row-between"><strong>${y.model}</strong><span class="pill">mAP ${y.precision_map}</span></div>
        <div style="margin-top:3px;color:var(--text-muted);">${y.use_case}</div>
      </div>`
    )
    .join("");
}

function updateDepositDescription() {
  const k = document.getElementById("inpDepositModel").value;
  const cfg = state.catalog?.deposit_models?.[k];
  document.getElementById("depositModelDesc").textContent = cfg ? cfg.description : "";
}

function getSelectedStackKeys() {
  const checked = Array.from(document.querySelectorAll(".chk-stack-band:checked")).map((c) => c.value);
  return checked.length >= 2 ? checked : null;
}

function buildAnalysisPayload() {
  const presetId = document.getElementById("presetSelect").value;
  const presetObj = (state.catalog?.presets || []).find((p) => p.id === presetId);
  const lat = Number(document.getElementById("inpLat").value);
  const lon = Number(document.getElementById("inpLon").value);
  const sameAsPreset = presetObj && Math.abs(presetObj.lat - lat) < 0.01 && Math.abs(presetObj.lon - lon) < 0.01;

  return {
    preset_id: sameAsPreset ? presetId : null,
    lat,
    lon,
    roi_size_km: Number(document.getElementById("inpRoiKm").value),
    sensor_mode: document.getElementById("inpSensorMode").value,
    start_date: document.getElementById("inpStartDate").value,
    end_date: document.getElementById("inpEndDate").value,
    cloud_cover_max: Number(document.getElementById("inpCloudMax").value),
    mask_vegetation: document.getElementById("chkMaskVeg").checked,
    ndvi_threshold: Number(document.getElementById("inpNdviThr").value),
    mask_water: document.getElementById("chkMaskWater").checked,
    mask_shadows: document.getElementById("chkMaskShadow").checked,
    norm_method: document.getElementById("inpNormMethod").value,
    selected_stack_keys: getSelectedStackKeys(),
    ml_method: document.getElementById("inpMlMethod").value,
    n_clusters: Number(document.getElementById("inpClusters").value),
    apply_majority_filter: document.getElementById("chkMajority").checked,
    majority_window: Number(document.getElementById("inpMajorityWin").value),
    apply_sieve_filter: document.getElementById("chkSieve").checked,
    sieve_min_pixels: Number(document.getElementById("inpSievePx").value),
    training_samples: state.userSamples,
    deposit_model: document.getElementById("inpDepositModel").value,
    strict_nan: document.getElementById("chkStrictNan").checked,
    target_threshold: Number(document.getElementById("inpTargetThr").value),
    min_target_area_ha: Number(document.getElementById("inpMinAreaHa").value),
    validation_buffer_m: Number(document.getElementById("inpValBuffer").value),
    save_to_cloud: true,
  };
}

async function runPipeline() {
  const loader = document.getElementById("loadingOverlay");
  loader.classList.remove("hidden");
  try {
    const payload = buildAnalysisPayload();
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    state.analysis = data;
    renderAllAnalysisViews(data);
  } catch (err) {
    console.error("Error ejecutando pipeline GeoAUV2:", err);
    alert("Error procesando el cuadrante: " + err.message);
  } finally {
    loader.classList.add("hidden");
  }
}

function renderAllAnalysisViews(data) {
  const prosp = data.prospectivity_summary;
  const val = data.validation;
  const diag = data.diagnostics;
  const targets = data.targets || [];
  const p1Count = targets.filter((t) => t.priority_code === "P1").length;

  // KPIs Superiores
  const kpiMpi = document.getElementById("kpiMpi");
  kpiMpi.textContent = `${prosp.mpi} (${prosp.classification_code})`;
  kpiMpi.style.color = prosp.classification_color;
  document.getElementById("kpiClass").textContent = prosp.classification_label;
  document.getElementById("kpiTargets").textContent = `${targets.length} (${p1Count} P1)`;
  document.getElementById("kpiAreaPct").textContent = `${val.target_area_pct_of_roi}% del ROI`;
  document.getElementById("kpiKappa").textContent = `κ ${val.kappa}`;
  document.getElementById("kpiGain").textContent = `Ganancia ${val.spatial_gain}×`;

  // Paso 1: Cascada y Máscaras
  const ms = diag.mask_stats || {};
  document.getElementById("cascadeBadges").innerHTML = `
    <span class="pill">Nivel Cascada: ${diag.cascade_level}</span>
    <span class="pill">ASTER SWIR: ${diag.aster_swir_available ? "ACTIVO" : "REDISTRIBUIDO"}</span>
    <span class="pill">Roca/Suelo Válido: ${ms.valid_rock_soil_pct || 0}%</span>
  `;
  document.getElementById("cascadeLogs").innerHTML = (diag.cascade_logs || [])
    .map((l) => `<li>${l}</li>`)
    .join("");

  // Paso 2: Selector de Índices e Histograma
  const idxSel = document.getElementById("selIndexInspect");
  const prevVal = idxSel.value;
  const idxKeys = Object.keys(data.indices_stats || {});
  idxSel.innerHTML = idxKeys
    .map((k) => `<option value="${k}">${data.indices_stats[k].name} (${k})</option>`)
    .join("");
  if (idxKeys.includes(prevVal)) idxSel.value = prevVal;
  renderSelectedIndexStats();

  // Paso 3: Stack Multibanda ML
  const stInfo = data.stack_info;
  document.getElementById("stackMetaBox").textContent =
    `Stack activo: ${stInfo.dimensions.join(" × ")} (${stInfo.bands_count} bandas · ${stInfo.memory_kb} KB en RAM)`;
  const stackWrap = document.getElementById("stackCheckList");
  stackWrap.innerHTML = idxKeys
    .filter((k) => k !== "ndwi")
    .map((k) => {
      const checked = stInfo.selected_keys.includes(k) ? "checked" : "";
      const st = data.indices_stats[k];
      return `<label class="stack-item">
        <span><input type="checkbox" class="chk-stack-band" value="${k}" ${checked}/> <strong>${st.name}</strong></span>
        <span class="pill">${st.sensor}</span>
      </label>`;
    })
    .join("");

  // Paso 4: IA / Machine Learning
  const ml = data.ml_summary;
  const ae = ml.alpha_earth_similarity || {};
  document.getElementById("alphaEarthBox").innerHTML =
    `<strong>Similitud Coseno AlphaEarth:</strong> Coherencia LOO <code>${ae.loo_coherence ?? "--"}</code> · Δ Fondo <code>${ae.discrimination_delta ?? "--"}</code><br><small>${ae.verdict || ""}</small>`;

  const accBox = document.getElementById("mlAccuracyBox");
  if (ml.accuracy_metrics) {
    const am = ml.accuracy_metrics;
    accBox.innerHTML = `<div class="mini-stats-grid" style="margin-top:6px;">
      <div class="mini-stat"><span>Precisión OA</span><strong>${(am.overall_accuracy * 100).toFixed(1)}%</strong></div>
      <div class="mini-stat"><span>Kappa Superv.</span><strong>${am.kappa}</strong></div>
      <div class="mini-stat"><span>Muestras Entr.</span><strong>${am.training_samples} px</strong></div>
    </div>`;
  } else {
    accBox.innerHTML = "";
  }

  document.getElementById("mlClustersList").innerHTML = (ml.clusters || [])
    .map(
      (c) => `<div class="cluster-card" style="border-left:4px solid ${c.color};">
        <div class="row-between">
          <strong>#${c.cluster_id} · ${c.geological_zone}</strong>
          <span>${c.area_pct}%</span>
        </div>
        <div style="color:var(--text-muted);margin-top:2px;">Confianza: ${c.confidence} · ${c.pixel_count} píxeles</div>
      </div>`
    )
    .join("");

  // Paso 5: Favorabilidad Mineral
  document.getElementById("weightSourceLbl").textContent = data.favorability_info.weight_source;
  document.getElementById("activeWeightsBars").innerHTML = Object.entries(data.favorability_info.weights_normalized || {})
    .map(([k, w]) => {
      const pct = Math.round(w * 100);
      const nm = data.indices_stats[k]?.name || k;
      return `<div class="bar-row">
        <div class="row-between"><span>${nm}</span><strong>${pct}%</strong></div>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
      </div>`;
    })
    .join("");

  // Paso 6: Prospectividad Integrada + SGC/ANM
  const cs = prosp.component_scores || {};
  const compMap = [
    ["Alteración Espectral Multisensor", cs.spectral || 0],
    ["Control Estructural & Lineamientos DEM", cs.structural || 0],
    ["Evidencia Metalogénica SGC / Control", cs.geological_sgc || 0],
    ["Respuesta Geofísica Regional", cs.geophysical || 0],
  ];
  document.getElementById("componentScoresBars").innerHTML = compMap
    .map(
      ([lbl, valNum]) => `<div class="bar-row">
        <div class="row-between"><span>${lbl}</span><strong>${valNum}/100</strong></div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, valNum)}%"></div></div>
      </div>`
    )
    .join("");

  const stStats = prosp.structural_stats || {};
  document.getElementById("structuralSummaryBox").innerHTML = `
    <div class="mini-stat"><span>Elevación</span><strong>${stStats.elevation_min_m}–${stStats.elevation_max_m} m</strong></div>
    <div class="mini-stat"><span>Pendiente Media</span><strong>${stStats.slope_mean_deg}°</strong></div>
    <div class="mini-stat"><span>Dens. Sobel</span><strong>${stStats.lineament_density_mean}</strong></div>
  `;

  const sgc = data.sgc_metrics || {};
  const leg = data.legal_status || {};
  document.getElementById("sgcAnmSummary").innerHTML = `
    <p class="muted-note"><strong>Fallas SGC:</strong> ${sgc.fault_count} trazas (más cercana: ${sgc.nearest_fault_km} km · densidad ${sgc.fault_density_km_km2} km/km²)</p>
    <p class="muted-note"><strong>Yacimiento Cercano:</strong> ${sgc.nearest_deposit_name || "No registrado"} ${sgc.known_gold_grade_gt ? `(${sgc.known_gold_grade_gt} g/t Au)` : ""}</p>
    <p class="muted-note"><strong>Tipología Detectada:</strong> ${sgc.deposit_type_detected}</p>
    <p class="muted-note"><strong>Estado Jurídico ANM:</strong> <span style="color:var(--accent);">${leg.status_summary}</span></p>
  `;

  // Paso 7: Targets Priorizados
  const tgtWrap = document.getElementById("targetsList");
  if (targets.length === 0) {
    tgtWrap.innerHTML = `<div class="info-banner">0 targets superan el umbral actual (${payloadThresholdText()}). Comportamiento esperado en controles negativos o zonas estériles.</div>`;
  } else {
    tgtWrap.innerHTML = targets
      .map(
        (t) => `<div class="target-card" style="border-left-color:${t.color}" onclick="zoomToTarget(${t.lat}, ${t.lon})">
          <div class="row-between">
            <strong>#${t.rank} · ${t.priority}</strong>
            <span class="pill">${t.area_ha} ha</span>
          </div>
          <div style="margin-top:3px;">Score máx: <b>${t.score_max}</b> · Medio: <b>${t.score_mean}</b></div>
          <div style="color:var(--text-muted);">${t.dominant_alteration} · (${t.lat.toFixed(4)}, ${t.lon.toFixed(4)})</div>
        </div>`
      )
      .join("");
  }

  // Paso 8: Validación Estadística
  document.getElementById("valLandisBadge").innerHTML =
    `<strong>Concordancia Kappa = ${val.kappa}:</strong> ${val.kappa_interpretation}<br><small>Proyección métrica: EPSG:${val.utm_epsg} · Modo: ${val.validation_mode}</small>`;
  document.getElementById("valMetricsGrid").innerHTML = `
    <div class="mini-stat"><span>Precisión OA</span><strong>${(val.overall_accuracy * 100).toFixed(1)}%</strong></div>
    <div class="mini-stat"><span>F1-Score</span><strong>${val.f1_score}</strong></div>
    <div class="mini-stat"><span>Ganancia Espacial</span><strong>${val.spatial_gain}×</strong></div>
    <div class="mini-stat"><span>Tasa Captura</span><strong>${val.capture_rate_pct}%</strong></div>
    <div class="mini-stat"><span>Precisión Pos.</span><strong>${(val.precision * 100).toFixed(1)}%</strong></div>
    <div class="mini-stat"><span>Área Target</span><strong>${val.target_area_pct_of_roi}%</strong></div>
  `;
  const cm = val.confusion_matrix || {};
  document.getElementById("valConfusionTable").innerHTML = `
    <table class="data-table">
      <thead><tr><th>Real \\ Predicho</th><th>Dentro Buffer Target</th><th>Fondo Estéril</th></tr></thead>
      <tbody>
        <tr><td><strong>Ocurrencia (+ )</strong></td><td>TP = <b>${cm.tp}</b></td><td>FN = ${cm.fn}</td></tr>
        <tr><td><strong>Control Fondo ( - )</strong></td><td>FP = ${cm.fp}</td><td>TN = <b>${cm.tn}</b></td></tr>
      </tbody>
    </table>
  `;
  document.getElementById("valControlPoints").innerHTML = (val.control_points || [])
    .map(
      (cp) => `<div class="cluster-card">
        <div class="row-between">
          <strong>${cp.name}</strong>
          <span style="color:${cp.captured ? "var(--success)" : "#e74c3c"};font-weight:700;">
            ${cp.captured ? "✓ Capturado" : "✕ Fuera"} (${cp.distance_to_target_m} m)
          </span>
        </div>
        <small style="color:var(--text-muted);">${cp.source} · (${cp.lat}, ${cp.lon})</small>
      </div>`
    )
    .join("");

  // Paso 9: Plan GeoAI & GEE
  document.getElementById("geoaiPlanBox").innerHTML = (data.geoai_plan?.phases || [])
    .map(
      (ph) => `<div class="cluster-card">
        <strong style="color:var(--accent);">${ph.phase}</strong>
        <ul class="diag-list">${ph.actions.map((a) => `<li>${a}</li>`).join("")}</ul>
      </div>`
    )
    .join("");
  if (data.gee_script_default?.code) {
    document.getElementById("geeCodeBox").textContent = data.gee_script_default.code;
  }

  // Renderizar Geometrías y Capas Ráster en el Mapa
  renderMapLayers(data);
}

function payloadThresholdText() {
  return document.getElementById("inpTargetThr").value;
}

window.zoomToTarget = function (lat, lon) {
  map.flyTo([lat, lon], 15, { duration: 0.8 });
};

function renderMapLayers(data) {
  const [minLon, minLat, maxLon, maxLat] = data.metadata.bbox;
  const bounds = [[minLat, minLon], [maxLat, maxLon]];

  if (roiLayer) map.removeLayer(roiLayer);
  roiLayer = L.rectangle(bounds, {
    color: "#ffd700",
    weight: 2,
    fillOpacity: 0.0,
    dashArray: "6,4",
  }).addTo(map);

  map.fitBounds(bounds, { padding: [35, 35] });
  updateActiveRasterOverlay();

  // Targets vectoriales
  targetsLayerGroup.clearLayers();
  if (data.targets_geojson?.features?.length) {
    L.geoJSON(data.targets_geojson, {
      style: (feat) => ({
        color: feat.properties.color || "#ff3b30",
        weight: 2.4,
        fillColor: feat.properties.color || "#ff3b30",
        fillOpacity: 0.24,
      }),
      onEachFeature: (feat, layer) => {
        const p = feat.properties;
        layer.bindPopup(
          `<strong>Target #${p.rank} (${p.priority_code})</strong><br>` +
          `Área: ${p.area_ha} ha<br>Score Máx: ${p.score_max} · Medio: ${p.score_mean}<br>` +
          `Dominio: ${p.dominant_alteration}`
        );
      },
    }).addTo(targetsLayerGroup);
  }

  // Fallas SGC
  fallasLayerGroup.clearLayers();
  if (data.vector_layers?.fallas?.features?.length) {
    L.geoJSON(data.vector_layers.fallas, {
      style: { color: "#00e5ff", weight: 2.2, dashArray: "5,5" },
      onEachFeature: (f, l) => l.bindPopup(`<strong>Falla / Estructura SGC</strong>`),
    }).addTo(fallasLayerGroup);
  }

  // Depósitos y puntos de control
  depositosLayerGroup.clearLayers();
  (data.validation?.control_points || []).forEach((cp) => {
    L.circleMarker([cp.lat, cp.lon], {
      radius: 6,
      color: "#111",
      weight: 1.5,
      fillColor: "#ffd700",
      fillOpacity: 0.95,
    })
      .bindPopup(`<strong>★ ${cp.name}</strong><br>Fuente: ${cp.source}<br>Distancia a Target: ${cp.distance_to_target_m} m`)
      .addTo(depositosLayerGroup);
  });

  // Catastro ANM
  anmLayerGroup.clearLayers();
  if (data.vector_layers?.titulos_vigentes?.features?.length) {
    L.geoJSON(data.vector_layers.titulos_vigentes, {
      style: { color: "#a855f7", weight: 1.6, fillOpacity: 0.08 },
      onEachFeature: (f, l) => {
        const pr = f.properties || {};
        l.bindPopup(`<strong>Título Minero ANM</strong><br>Exp: ${pr.CODIGO_EXPEDIENTE || pr.NUMERO_EXPEDIENTE || "Vigente"}`);
      },
    }).addTo(anmLayerGroup);
  }
}

function updateActiveRasterOverlay() {
  if (rasterOverlay) {
    map.removeLayer(rasterOverlay);
    rasterOverlay = null;
  }
  if (!state.analysis) return;
  const key = document.getElementById("selRasterLayer").value;
  if (key === "none") return;

  const uri = state.analysis.raster_overlays?.[key];
  if (!uri) return;
  const [minLon, minLat, maxLon, maxLat] = state.analysis.metadata.bbox;
  const op = Number(document.getElementById("rngOpacity").value) / 100;
  rasterOverlay = L.imageOverlay(uri, [[minLat, minLon], [maxLat, maxLon]], {
    opacity: op,
    interactive: false,
  }).addTo(map);
}

function renderSelectedIndexStats() {
  if (!state.analysis) return;
  const k = document.getElementById("selIndexInspect").value;
  const st = state.analysis.indices_stats?.[k];
  if (!st) return;

  document.getElementById("idxTitle").textContent = st.name;
  document.getElementById("idxFormula").textContent = st.formula;
  document.getElementById("idxMetricsGrid").innerHTML = `
    <div class="mini-stat"><span>Mínimo</span><strong>${st.min}</strong></div>
    <div class="mini-stat"><span>Percentil P2</span><strong>${st.p2}</strong></div>
    <div class="mini-stat"><span>Mediana</span><strong>${st.median}</strong></div>
    <div class="mini-stat"><span>Percentil P98</span><strong>${st.p98}</strong></div>
    <div class="mini-stat"><span>Máximo</span><strong>${st.max}</strong></div>
    <div class="mini-stat"><span>NoData Mask</span><strong>${st.nodata_pct}%</strong></div>
  `;

  // Dibujar histograma de 24 barras
  const canvas = document.getElementById("histCanvas");
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const counts = st.histogram?.counts || [];
  if (!counts.length) return;
  const maxC = Math.max(...counts, 1);
  const pad = 16;
  const barW = (w - pad * 2) / counts.length;

  counts.forEach((c, i) => {
    const bh = ((h - 28) * c) / maxC;
    const x = pad + i * barW;
    const y = h - 18 - bh;
    ctx.fillStyle = i >= 18 ? "#ff5722" : "#f39c12";
    ctx.fillRect(x + 1, y, Math.max(barW - 2, 2), bh);
  });

  ctx.fillStyle = "#94a3b8";
  ctx.font = "10px Inter";
  ctx.fillText("0.0 (Fondo)", pad, h - 4);
  ctx.fillText("0.5", w / 2 - 8, h - 4);
  ctx.fillText("1.0 (Anomalía P98)", w - 102, h - 4);
}

function onMapClick(e) {
  const { lat, lng } = e.latlng;

  if (state.measureMode) {
    state.measurePts.push([lat, lng]);
    L.circleMarker([lat, lng], { radius: 4, color: "#00e5ff" }).addTo(measureLayerGroup);
    if (state.measurePts.length >= 2) {
      const p1 = state.measurePts[state.measurePts.length - 2];
      const p2 = state.measurePts[state.measurePts.length - 1];
      const distM = map.distance(p1, p2);
      const label = distM >= 1000 ? `${(distM / 1000).toFixed(2)} km` : `${Math.round(distM)} m`;
      L.polyline([p1, p2], { color: "#00e5ff", weight: 2.5 })
        .bindTooltip(label, { permanent: true })
        .addTo(measureLayerGroup);
    }
    return;
  }

  if (state.sampleCaptureMode) {
    const [cidStr, cname, ccol] = document.getElementById("selSampleClass").value.split("|");
    const smp = {
      class_id: Number(cidStr),
      class_name: cname,
      class_color: ccol,
      lat: Number(lat.toFixed(6)),
      lon: Number(lng.toFixed(6)),
    };
    state.userSamples.push(smp);
    document.getElementById("sampleCount").textContent = String(state.userSamples.length);
    L.circleMarker([lat, lng], {
      radius: 6,
      color: "#fff",
      weight: 1.5,
      fillColor: ccol,
      fillOpacity: 0.95,
    })
      .bindPopup(`Muestra DZetsaka: <b>${cname}</b>`)
      .addTo(samplesLayerGroup);
    return;
  }

  // Por defecto: actualizar centroide de exploración con clic en mapa
  document.getElementById("inpLat").value = lat.toFixed(5);
  document.getElementById("inpLon").value = lng.toFixed(5);
}

function onMapMouseMove(e) {
  if (!state.analysis?.pixel_inspector) return;
  const [minLon, minLat, maxLon, maxLat] = state.analysis.metadata.bbox;
  const { lat, lng } = e.latlng;
  if (lng < minLon || lng > maxLon || lat < minLat || lat > maxLat) return;

  const pi = state.analysis.pixel_inspector;
  const g = pi.grid_size;
  const col = Math.min(g - 1, Math.max(0, Math.floor(((lng - minLon) / (maxLon - minLon)) * g)));
  const row = Math.min(g - 1, Math.max(0, Math.floor(((maxLat - lat) / (maxLat - minLat)) * g)));

  document.getElementById("hudCoords").textContent = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

  const pVal = pi.prospectivity?.[row]?.[col] ?? -1;
  const cVal = pi.clay_index?.[row]?.[col] ?? -1;
  const fVal = pi.feox_index?.[row]?.[col] ?? -1;
  const nVal = pi.ndvi?.[row]?.[col] ?? -1;

  document.getElementById("hudReadout").innerHTML = `
    <span>Prosp: <b>${pVal >= 0 ? pVal.toFixed(2) : "Mask"}</b></span>
    <span>Arcilla: <b>${cVal >= 0 ? cVal.toFixed(2) : "Mask"}</b></span>
    <span>FeOx: <b>${fVal >= 0 ? fVal.toFixed(2) : "Mask"}</b></span>
    <span>NDVI: <b>${nVal > -1 ? nVal.toFixed(2) : "--"}</b></span>
  `;

  drawSpectralCurve(pi, row, col);
}

function drawSpectralCurve(pi, row, col) {
  const canvas = document.getElementById("specCurveCanvas");
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const waves = pi.wavelengths || [];
  const pts = [];
  waves.forEach((wObj, i) => {
    const grid = pi.bands?.[wObj.band];
    if (!grid) return;
    const v = grid[row]?.[col];
    if (v !== undefined && v >= 0) {
      pts.push({ idx: i, label: wObj.band.replace("AST_", "A").replace("S2_", ""), val: v });
    }
  });
  if (pts.length < 2) return;

  const padL = 26, padR = 10, padT = 10, padB = 18;
  // Guías verticales de absorción diagnóstica (Alunita B5 / Sericita B6)
  ctx.strokeStyle = "rgba(243, 156, 18, 0.22)";
  ctx.beginPath();
  pts.forEach((p, k) => {
    const x = padL + (k / (pts.length - 1)) * (w - padL - padR);
    ctx.moveTo(x, padT);
    ctx.lineTo(x, h - padB);
  });
  ctx.stroke();

  // Curva espectral
  ctx.strokeStyle = "#ffd700";
  ctx.lineWidth = 2;
  ctx.beginPath();
  pts.forEach((p, k) => {
    const x = padL + (k / (pts.length - 1)) * (w - padL - padR);
    const normV = Math.min(1, Math.max(0, p.val));
    const y = h - padB - normV * (h - padT - padB);
    if (k === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  pts.forEach((p, k) => {
    const x = padL + (k / (pts.length - 1)) * (w - padL - padR);
    const normV = Math.min(1, Math.max(0, p.val));
    const y = h - padB - normV * (h - padT - padB);
    ctx.fillStyle = "#f39c12";
    ctx.beginPath();
    ctx.arc(x, y, 2.6, 0, Math.PI * 2);
    ctx.fill();

    if (k % 2 === 0 || k === pts.length - 1) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "9px JetBrains Mono";
      ctx.fillText(p.label, x - 10, h - 4);
    }
  });
}

async function runMagnetometry(forceDemo = false) {
  const lat = Number(document.getElementById("inpLat").value);
  const lon = Number(document.getElementById("inpLon").value);
  const csvTxt = document.getElementById("txtMagCsv").value.trim();

  let customPts = null;
  if (!forceDemo && csvTxt.length > 10) {
    customPts = [];
    csvTxt.split(/\r?\n/).forEach((line, idx) => {
      const parts = line.split(",").map((s) => s.trim());
      if (parts.length >= 5 && !isNaN(Number(parts[0]))) {
        customPts.push({
          station_id: `CSV-${idx + 1}`,
          lat: Number(parts[0]),
          lon: Number(parts[1]),
          bx: Number(parts[2]),
          by: Number(parts[3]),
          bz: Number(parts[4]),
        });
      }
    });
  }

  try {
    const resp = await fetch("/api/magnetometry/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        survey_name: `Magnetometría ${document.getElementById("presetSelect").value}`,
        center_lat: lat,
        center_lon: lon,
        use_demo_dataset: !customPts || customPts.length < 4,
        points: customPts,
        save_to_cloud: !forceDemo,
      }),
    });
    const res = await resp.json();
    state.magResult = res;

    document.getElementById("magMetricsBar").innerHTML = `
      <div class="mini-stat"><span>Base Regional</span><strong>${res.regional_baseline_ut} µT</strong></div>
      <div class="mini-stat"><span>Rango B Total</span><strong>${res.min_b_ut}–${res.max_b_ut} µT</strong></div>
      <div class="mini-stat"><span>Vacíos Hidro.</span><strong style="color:#38bdf8;">${res.void_zones_count} zona(s)</strong></div>
    `;
    document.getElementById("magInterpText").textContent = res.interpretation;
    drawMagnetometry3D();

    // Dibujar estaciones magnéticas cuando el usuario ejecute explícitamente el laboratorio
    magLayerGroup.clearLayers();
    if (!forceDemo) {
      (res.points || []).forEach((pt) => {
        const isVoid = pt.zone_class.includes("Vacío");
        L.circleMarker([pt.lat, pt.lon], {
          radius: isVoid ? 5.5 : 3.5,
          color: isVoid ? "#0284c7" : "#f97316",
          fillColor: isVoid ? "#38bdf8" : "#fb923c",
          fillOpacity: 0.85,
        })
          .bindPopup(`<strong>${pt.station_id}</strong>: ${pt.b_total_ut} µT (${pt.residual_nt} nT)<br>${pt.zone_class}`)
          .addTo(magLayerGroup);
      });
    }
  } catch (err) {
    console.warn("Error en magnetometría:", err);
  }
}

function drawMagnetometry3D() {
  const res = state.magResult;
  if (!res?.grid_3d) return;
  const canvas = document.getElementById("mag3dCanvas");
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const zGrid = res.grid_3d.b_total_ut;
  const N = zGrid.length;
  const zMin = res.min_b_ut;
  const zMax = Math.max(res.max_b_ut, zMin + 0.5);
  const voidThr = res.void_threshold_ut;

  const cosY = Math.cos(state.magRotYaw);
  const sinY = Math.sin(state.magRotYaw);
  const cosP = Math.cos(state.magRotPitch);
  const sinP = Math.sin(state.magRotPitch);
  const scale = Math.min(W, H) * 0.56;

  function project(r, c, bVal) {
    const nx = (c / (N - 1)) - 0.5;
    const ny = (r / (N - 1)) - 0.5;
    const nz = ((bVal - zMin) / (zMax - zMin) - 0.5) * 0.68;

    const rx = nx * cosY - ny * sinY;
    const ry = nx * sinY + ny * cosY;
    const py = ry * cosP - nz * sinP;
    return {
      x: W * 0.5 + rx * scale,
      y: H * 0.54 + py * scale,
      depth: ry * sinP + nz * cosP,
    };
  }

  // Renderizado pintor de quads ordenados por profundidad
  const quads = [];
  for (let r = 0; r < N - 1; r++) {
    for (let c = 0; c < N - 1; c++) {
      const z00 = zGrid[r][c];
      const z01 = zGrid[r][c + 1];
      const z11 = zGrid[r + 1][c + 1];
      const z10 = zGrid[r + 1][c];
      const zAvg = 0.25 * (z00 + z01 + z11 + z10);
      const p0 = project(r, c, z00);
      const p1 = project(r, c + 1, z01);
      const p2 = project(r + 1, c + 1, z11);
      const p3 = project(r + 1, c, z10);
      quads.push({
        pts: [p0, p1, p2, p3],
        depth: 0.25 * (p0.depth + p1.depth + p2.depth + p3.depth),
        zAvg,
      });
    }
  }
  quads.sort((a, b) => a.depth - b.depth);

  quads.forEach((q) => {
    const t = (q.zAvg - zMin) / (zMax - zMin);
    let fill;
    if (q.zAvg <= voidThr) {
      // Valle Azul: Vacío Magnético Hidrotermal
      fill = `rgba(14, 165, 233, 0.88)`;
    } else if (t > 0.72) {
      fill = `rgba(239, 68, 68, 0.85)`;
    } else if (t > 0.48) {
      fill = `rgba(245, 158, 11, 0.80)`;
    } else {
      fill = `rgba(52, 211, 153, 0.76)`;
    }
    ctx.beginPath();
    ctx.moveTo(q.pts[0].x, q.pts[0].y);
    ctx.lineTo(q.pts[1].x, q.pts[1].y);
    ctx.lineTo(q.pts[2].x, q.pts[2].y);
    ctx.lineTo(q.pts[3].x, q.pts[3].y);
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.strokeStyle = "rgba(15, 23, 42, 0.28)";
    ctx.lineWidth = 0.6;
    ctx.stroke();
  });

  ctx.fillStyle = "#38bdf8";
  ctx.font = "600 10px Inter";
  ctx.fillText("■ Azul: Vacío Magnético Hidrotermal (Magnetita destruida)", 8, 14);
}

async function fetchGeeTemplate() {
  if (!state.analysis) return;
  const tpl = document.getElementById("selGeeTemplate").value;
  const resp = await fetch("/api/gee-script", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      template_type: tpl,
      roi_name: state.analysis.metadata.roi_name,
      bbox: state.analysis.metadata.bbox,
      start_date: document.getElementById("inpStartDate").value,
      end_date: document.getElementById("inpEndDate").value,
      cloud_cover_max: Number(document.getElementById("inpCloudMax").value),
      ndvi_threshold: Number(document.getElementById("inpNdviThr").value),
      deposit_model: document.getElementById("inpDepositModel").value,
    }),
  });
  const data = await resp.json();
  document.getElementById("geeCodeBox").textContent = data.code || "";
}

async function saveProjectToSupabase() {
  if (!state.analysis) return;
  const name = prompt("Nombre del proyecto exploratorio para guardar en Supabase:", state.analysis.metadata.roi_name);
  if (!name) return;
  const cfg = buildAnalysisPayload();
  const resp = await fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      district_code: document.getElementById("presetSelect").value,
      sensor_mode: cfg.sensor_mode,
      deposit_model: cfg.deposit_model,
      center_lat: cfg.lat,
      center_lon: cfg.lon,
      roi_size_km: cfg.roi_size_km,
      bbox: state.analysis.metadata.bbox,
      config_json: cfg,
    }),
  });
  const out = await resp.json();
  if (out.saved) {
    alert("Proyecto guardado exitosamente en Supabase (tabla geoauv2_projects).");
  } else {
    alert("Aviso guardando proyecto: " + JSON.stringify(out));
  }
}

async function openCloudModal() {
  const modal = document.getElementById("cloudModal");
  const wrap = document.getElementById("cloudRunsTableWrap");
  modal.classList.remove("hidden");
  wrap.innerHTML = "<p>Consultando corridas en Supabase...</p>";

  try {
    const [rRuns, rProjs] = await Promise.all([fetch("/api/runs?limit=15"), fetch("/api/projects?limit=10")]);
    const runsData = await rRuns.json();
    const projsData = await rProjs.json();

    const rowsHtml = (runsData.runs || [])
      .map(
        (r) => `<tr>
          <td>${(r.created_at || "").slice(0, 16).replace("T", " ")}</td>
          <td><strong>${r.district_name || r.quadrant_key}</strong></td>
          <td>${r.sensor_mode}</td>
          <td>${r.ml_method}</td>
          <td><b>${r.mpi_score}</b> (${r.classification_code})</td>
          <td>${r.targets_count} (${r.p1_targets_count} P1)</td>
          <td>${r.validation_kappa ?? "--"}</td>
        </tr>`
      )
      .join("");

    wrap.innerHTML = `
      <h3 style="margin:6px 0;">Últimas Corridas Analíticas (<code>geoauv2_analysis_runs</code>: ${runsData.count})</h3>
      <table class="data-table">
        <thead>
          <tr><th>Fecha UTC</th><th>Región / ROI</th><th>Sensor</th><th>IA</th><th>MPI</th><th>Targets</th><th>Kappa</th></tr>
        </thead>
        <tbody>${rowsHtml || "<tr><td colspan='7'>Sin registros aún</td></tr>"}</tbody>
      </table>
      <p class="muted-note" style="margin-top:10px;">Proyectos configurados en <code>geoauv2_projects</code>: <strong>${projsData.count}</strong></p>
    `;
  } catch (err) {
    wrap.innerHTML = `<p>Error consultando Supabase: ${err.message}</p>`;
  }
}

function downloadTextFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
