/* ============================================================================
   GeoAuV2 — Motor Interactivo Frontend de Prospección Aurífera
   Mapas satelitales sin nubes HD, visualización de focos de oro con isolíneas,
   buscador inteligente, radar de 4 pilares, corte transversal A–B, exportación
   directa a GPS (.GPX / .KML), magnetometría 3D y persistencia en la nube.
   ============================================================================ */

const state = {
  catalog: null,
  analysis: null,
  magResult: null,
  lang: "es",
  labelsVisible: true,
  sampleCaptureMode: false,
  measureMode: false,
  measurePts: [],
  customTransect: null, // [[latA, lonA], [latB, lonB]]
  userSamples: [],
  magRotYaw: -0.68,
  magRotPitch: 0.58,
  isDragging3d: false,
  dragLastX: 0,
  dragLastY: 0,
  loadingTimer: null,
  nominatimTimer: null,
};

const I18N = {
  es: {
    subtitle: "Prospección Aurífera Multisensor · IA & Geofísica 3D",
    district: "Distrito:",
    run_btn: "Analizar Oro (Ctrl+R)",
    s1: "Zona & Sat", s2: "Índices", s3: "Stack IA", s4: "IA Mineral",
    s5: "Modelo Au", s6: "Geofísica", s7: "Focos Au", s8: "Validación", s9: "Informes",
  },
  en: {
    subtitle: "Multisensor Gold Prospecting · AI & 3D Geophysics",
    district: "District:",
    run_btn: "Analyze Gold (Ctrl+R)",
    s1: "Zone & Sat", s2: "Indices", s3: "AI Stack", s4: "Mineral AI",
    s5: "Au Model", s6: "Geophysics", s7: "Au Hotspots", s8: "Validation", s9: "Reports",
  },
};

/* Base de conocimiento local de municipios, ríos y distritos auríferos para autocompletado instantáneo */
const MINING_PLACES_DB = [
  { name: "Segovia, Antioquia", sub: "Distrito Vetas Orogénicas Au-Ag", lat: 7.0792, lon: -74.6988, model: "orogenico_vetas" },
  { name: "Remedios, Antioquia", sub: "Cinturón Aurífero Nordeste Antioqueño", lat: 7.0275, lon: -74.6936, model: "orogenico_vetas" },
  { name: "Zaragoza, Antioquia", sub: "Placeres Aluviales y Vetas — Bajo Cauca", lat: 7.4892, lon: -74.8685, model: "aluvial_placer" },
  { name: "El Bagre (Río Nechí), Antioquia", sub: "Cuenca Aluvial Aurífera Principal", lat: 7.6042, lon: -74.8085, model: "aluvial_placer" },
  { name: "Nechí, Antioquia", sub: "Terrazas y Llanura Aluvial Río Cauca-Nechí", lat: 8.0961, lon: -74.7739, model: "aluvial_placer" },
  { name: "Caucasia, Antioquia", sub: "Distrito Aluvial Bajo Cauca", lat: 7.9865, lon: -75.1935, model: "aluvial_placer" },
  { name: "Cáceres, Antioquia", sub: "Terrazas Aluviales Río Cauca", lat: 7.5808, lon: -75.3483, model: "aluvial_placer" },
  { name: "Tarazá, Antioquia", sub: "Contacto Cauca-Romeral y Aluviones", lat: 7.5836, lon: -75.4006, model: "aluvial_placer" },
  { name: "Amalfi, Antioquia", sub: "Batolito Antioqueño — Vetas Cuarzo-Au", lat: 6.9092, lon: -75.0772, model: "orogenico_vetas" },
  { name: "Anorí, Antioquia", sub: "Vetas y Aluviones Auríferos Nordeste", lat: 7.0744, lon: -75.1481, model: "orogenico_vetas" },
  { name: "Buriticá, Antioquia", sub: "Sistema Epitermal-Porfídico de Alta Ley", lat: 6.7196, lon: -75.9082, model: "epitermal_bs" },
  { name: "Frontino, Antioquia", sub: "Cordillera Occidental — Vetas Auríferas", lat: 6.7667, lon: -76.1333, model: "orogenico_vetas" },
  { name: "Santa Rosa del Sur, Bolívar", sub: "Serranía de San Lucas — Vetas de Alta Ley", lat: 7.9644, lon: -74.0544, model: "orogenico_vetas" },
  { name: "Simití, Bolívar", sub: "Serranía de San Lucas Oriental", lat: 7.9542, lon: -73.9472, model: "orogenico_vetas" },
  { name: "Montecristo, Bolívar", sub: "Distrito Aurífero San Lucas", lat: 8.2972, lon: -74.4733, model: "orogenico_vetas" },
  { name: "Barranco de Loba / Norosí, Bolívar", sub: "Norte Serranía de San Lucas", lat: 8.5950, lon: -74.1150, model: "orogenico_vetas" },
  { name: "Marmato, Caldas", sub: "Pórfido y Vetas Epitermales Cauca Medio", lat: 5.4748, lon: -75.5986, model: "epitermal_bs" },
  { name: "Supía / Riosucio, Caldas", sub: "Corredor Metalogénico Río Cauca", lat: 5.4480, lon: -75.6500, model: "epitermal_bs" },
  { name: "Manizales / Villamaría (Gallinazo), Caldas", sub: "Epitermal Polimetálico Au-Ag", lat: 5.0250, lon: -75.4250, model: "epitermal_as" },
  { name: "California, Santander", sub: "Distrito Epitermal Alta Sulfuración Au-Ag", lat: 7.3512, lon: -72.9365, model: "epitermal_as" },
  { name: "Vetas, Santander", sub: "Filones Hidrotermales Macizo de Santander", lat: 7.3119, lon: -72.8719, model: "epitermal_as" },
  { name: "Cajamarca (La Colosa), Tolima", sub: "Pórfido Aurífero Cordillera Central", lat: 4.4552, lon: -75.4795, model: "porfido_au_cu" },
  { name: "Líbano / Santa Isabel, Tolima", sub: "Vetas Polimetálicas Au-Ag Cordillera Central", lat: 4.9217, lon: -75.0633, model: "orogenico_vetas" },
  { name: "Ataco (Río Saldaña), Tolima", sub: "Placeres Aluviales Sur del Tolima", lat: 3.5919, lon: -75.3822, model: "aluvial_placer" },
  { name: "Condoto, Chocó", sub: "Placeres Aluviales Au-Pt San Juan", lat: 5.0939, lon: -76.6497, model: "aluvial_placer" },
  { name: "Istmina, Chocó", sub: "Cuenca Aluvial Río San Juan", lat: 5.1606, lon: -76.6839, model: "aluvial_placer" },
  { name: "Río Quito (Paimadó), Chocó", sub: "Llanura Aluvial Aurífera Activa", lat: 5.5185, lon: -76.7265, model: "aluvial_placer" },
  { name: "Tadó, Chocó", sub: "Terrazas Aluviales Alto San Juan", lat: 5.2661, lon: -76.5650, model: "aluvial_placer" },
  { name: "Nóvita, Chocó", sub: "Distrito Histórico Aluvial Río Tamaná", lat: 4.9553, lon: -76.6053, model: "aluvial_placer" },
  { name: "Quibdó, Chocó", sub: "Cuenca Media del Río Atrato", lat: 5.6947, lon: -76.6611, model: "aluvial_placer" },
  { name: "Barbacoas (Río Telembí), Nariño", sub: "Distrito Aluvial Pacífico Sur", lat: 1.6717, lon: -78.1397, model: "aluvial_placer" },
  { name: "Cumbitara / Los Andes Sotomayor, Nariño", sub: "Vetas Auríferas Cordillera Occidental", lat: 1.6520, lon: -77.5810, model: "orogenico_vetas" },
  { name: "Suárez / Buenos Aires, Cauca", sub: "Distrito Aurífero Alto Cauca", lat: 2.9539, lon: -76.6964, model: "orogenico_vetas" },
  { name: "Guapi / Timbiquí, Cauca", sub: "Placeres Aluviales Llanura Pacífica", lat: 2.7710, lon: -77.6650, model: "aluvial_placer" },
  { name: "Mocoa, Putumayo", sub: "Sistema Pórfido Cu-Mo-Au Andino", lat: 1.1980, lon: -76.6650, model: "porfido_au_cu" },
  { name: "Quebradona (Jericó), Antioquia", sub: "Pórfido Cu-Au Mioceno", lat: 5.7910, lon: -75.7360, model: "porfido_au_cu" },
  { name: "Gramalote (San Roque), Antioquia", sub: "Sistema Intrusivo Orogénico Au", lat: 6.4850, lon: -74.9120, model: "orogenico_vetas" },
  { name: "Potosí (Cerro Rico), Bolivia", sub: "Domo Hidrotermal Ag-Sn-Au", lat: -19.6186, lon: -65.7497, model: "epitermal_as" },
  { name: "Yanacocha (Cajamarca), Perú", sub: "Epitermal Alta Sulfuración Au", lat: -6.9760, lon: -78.5160, model: "epitermal_as" },
  { name: "Madre de Dios (Inambari), Perú", sub: "Megaprovincia Aluvial Amazónica Au", lat: -12.8650, lon: -70.3650, model: "aluvial_placer" },
  { name: "Sabana de Bogotá (Control Negativo)", sub: "Cuenca Lacustre Estéril Q4", lat: 4.7110, lon: -74.0721, model: "epitermal_as" },
];

const LEGEND_CONFIGS = {
  gold_hotspots: {
    title: "🔥 Focos y Vetas de Oro (Fondo Limpio)",
    gradient: "linear-gradient(90deg, rgba(16,185,129,0.08) 0%, #10b981 26%, #eab308 54%, #ef4444 80%, #fde047 100%)",
    ticks: ["Estéril (Transp.)", "Halo 45%", "Veta 66%", "Núcleo >80%"],
  },
  prospectivity_thermal: {
    title: "🌈 Geofísica Térmica Aurífera",
    gradient: "linear-gradient(90deg, #0c2c6b 0%, #06b6d4 28%, #22c55e 52%, #facc15 76%, #ef4444 92%, #ffffff 100%)",
    ticks: ["Bajo (<26%)", "Moderado", "Alto 70%", "Pico >85%"],
  },
  prospectivity: {
    title: "🔮 Magma Aurífero de Alto Contraste",
    gradient: "linear-gradient(90deg, #2d113a 0%, #8e245c 34%, #e14b32 62%, #f9a822 84%, #fffccc 100%)",
    ticks: ["Fondo", "Anomalía", "Prioridad P2", "Prioridad P1"],
  },
  gold_classic: {
    title: "✨ Brillo Dorado de Vetas",
    gradient: "linear-gradient(90deg, rgba(180,95,12,0.12) 0%, #d97706 42%, #f59e0b 72%, #fef08a 100%)",
    ticks: ["Roca Caja", "Traza", "Filón", "Clavo Au"],
  },
  alluvial_placer: {
    title: "🌊 Placeres Aluviales, Gravas y Pozas",
    gradient: "linear-gradient(90deg, rgba(215,140,18,0.15) 0%, #eab308 48%, #fde047 74%, #0ed7ff 100%)",
    ticks: ["Llanura", "Terraza Q-al", "Barra Grava", "Poza Lavado"],
  },
  favorability: {
    title: "⚡ Favorabilidad Espectral Mineral",
    gradient: "linear-gradient(90deg, #2659c2 0%, #24c28e 35%, #d6db33 65%, #f5731a 85%, #a80d1e 100%)",
    ticks: ["Baja", "Media", "Alta", "Muy Alta"],
  },
  ml_clusters: {
    title: "🧠 Dominios de Alteración Clasificados (IA)",
    gradient: "linear-gradient(90deg, #5d6d7e 0%, #2ecc71 28%, #d35400 55%, #f39c12 78%, #e74c3c 100%)",
    ticks: ["Roca", "Propilítica", "Gossan", "Fílica/Argíl."],
  },
  ndvi: {
    title: "🌱 Vigor de Cobertura Vegetal (NDVI)",
    gradient: "linear-gradient(90deg, #8b5a2b 0%, #ccb86b 35%, #6bbf47 70%, #146624 100%)",
    ticks: ["Suelo/Roca", "Rastrojo", "Bosque", "Dosel Denso"],
  },
};

let map;
let baseLayersMap = {};
let activeBaseKey = "google_sat";
let cartoLabelsLayer = null;
let townLabelsGroup = null;
let roiLayer = null;
let centerCrosshair = null;
let rasterOverlay = null;
let targetsLayerGroup;
let fallasLayerGroup;
let depositosLayerGroup;
let anmLayerGroup;
let samplesLayerGroup;
let magLayerGroup;
let measureLayerGroup;
let rubberBandLine = null;

document.addEventListener("DOMContentLoaded", async () => {
  initMap();
  bindUIEvents();
  updateDmsTelemetry();
  await Promise.all([checkHealth(), loadCatalog()]);
  await runPipeline();
  await runMagnetometry(true);
});

/* ============================================================================
   1. Inicialización de Mapas Satelitales Libres de Nubes HD y Etiquetas
   ============================================================================ */
function initMap() {
  const googleSat = L.tileLayer("https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", {
    maxZoom: 20,
    maxNativeZoom: 20,
    attribution: "Imágenes Satelitales Sin Nubes HD &copy; Google Earth",
  });

  const googleHybrid = L.tileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", {
    maxZoom: 20,
    maxNativeZoom: 20,
    attribution: "Híbrido Satélite + Vías &copy; Google",
  });

  const s2Cloudless2024 = L.tileLayer(
    "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg",
    {
      maxZoom: 20,
      maxNativeZoom: 15,
      attribution: "Sentinel-2 Cloudless 2024 &copy; EOX / Copernicus ESA",
    }
  );

  const esriSat = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 20, maxNativeZoom: 19, attribution: "World Imagery &copy; Esri" }
  );

  const openTopo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    maxNativeZoom: 17,
    attribution: "Curvas de Nivel SRTM &copy; OpenTopoMap",
  });

  const darkGeo = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png", {
    maxZoom: 20,
    attribution: "&copy; CARTO Dark",
  });

  baseLayersMap = {
    google_sat: googleSat,
    google_hybrid: googleHybrid,
    s2_cloudless: s2Cloudless2024,
    esri_sat: esriSat,
    topo: openTopo,
    dark_geo: darkGeo,
  };

  map = L.map("map", {
    center: [7.0792, -74.6988],
    zoom: 13,
    maxZoom: 20,
    layers: [googleSat],
    zoomControl: true,
  });

  // Panel superior dedicado para etiquetas cartográficas nítidas sobre cualquier capa ráster
  map.createPane("labelsPane");
  map.getPane("labelsPane").style.zIndex = 635;
  map.getPane("labelsPane").style.pointerEvents = "none";

  cartoLabelsLayer = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png",
    {
      pane: "labelsPane",
      maxZoom: 20,
      opacity: 0.94,
    }
  ).addTo(map);

  townLabelsGroup = L.layerGroup().addTo(map);
  populateMiningTownLabels();

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

function populateMiningTownLabels() {
  townLabelsGroup.clearLayers();
  MINING_PLACES_DB.forEach((pl) => {
    const shortName = pl.name.split(",")[0];
    const icon = L.divIcon({
      className: "",
      html: `<div class="town-label-pill" title="Analizar ${pl.name}">📍 ${shortName}</div>`,
      iconSize: null,
      iconAnchor: [42, -10],
    });
    const m = L.marker([pl.lat, pl.lon], { icon, zIndexOffset: -120 });
    m.on("click", (ev) => {
      L.DomEvent.stopPropagation(ev);
      jumpToLocation(pl.lat, pl.lon, pl.name, pl.model, true);
    });
    m.addTo(townLabelsGroup);
  });
}

function switchBaseMap(key) {
  if (!baseLayersMap[key] || key === activeBaseKey) return;
  if (baseLayersMap[activeBaseKey]) map.removeLayer(baseLayersMap[activeBaseKey]);
  baseLayersMap[key].addTo(map);
  activeBaseKey = key;

  // Si elige Google Hybrid que ya trae etiquetas propias, evitamos duplicar capa CARTO
  if (key === "google_hybrid") {
    if (map.hasLayer(cartoLabelsLayer)) map.removeLayer(cartoLabelsLayer);
  } else if (state.labelsVisible && !map.hasLayer(cartoLabelsLayer)) {
    cartoLabelsLayer.addTo(map);
  }
}

/* ============================================================================
   2. Eventos de Interfaz, Buscador Omnibox, Coordenadas GMS y Atajos
   ============================================================================ */
function bindUIEvents() {
  // Colapsar/Expandir Paneles Laterales
  document.getElementById("btnToggleLeftPanel").addEventListener("click", () => {
    document.getElementById("mainWorkspace").classList.toggle("left-collapsed");
    setTimeout(() => map.invalidateSize(), 200);
  });

  const toggleRightDrawer = () => {
    const ws = document.getElementById("mainWorkspace");
    ws.classList.toggle("right-collapsed");
    document.getElementById("btnToggleExecDrawer").classList.toggle("active-drawer-btn", !ws.classList.contains("right-collapsed"));
    setTimeout(() => {
      map.invalidateSize();
      if (state.analysis) {
        drawFourPillarRadar(state.analysis.prospectivity_summary?.component_scores);
        drawCrossSectionProfile();
      }
    }, 200);
  };
  document.getElementById("btnToggleExecDrawer").addEventListener("click", toggleRightDrawer);
  document.getElementById("btnCloseExecDrawer").addEventListener("click", toggleRightDrawer);

  // Riel de 9 Pasos
  document.querySelectorAll(".step-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("mainWorkspace").classList.remove("left-collapsed");
      activateStep(btn.dataset.step);
      setTimeout(() => map.invalidateSize(), 150);
    });
  });

  // Chips Rápidos de Distrito
  document.querySelectorAll("#quickDistrictChips .chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const pid = chip.dataset.preset;
      const sel = document.getElementById("presetSelect");
      sel.value = pid;
      sel.dispatchEvent(new Event("change"));
      document.querySelectorAll("#quickDistrictChips .chip-btn").forEach((c) => c.classList.toggle("active", c === chip));
    });
  });

  // Selector de Mapa Base y Capa Ráster
  document.getElementById("selBaseMap").addEventListener("change", (e) => switchBaseMap(e.target.value));
  document.getElementById("selRasterLayer").addEventListener("change", () => {
    updateActiveRasterOverlay();
    updateLegendForLayer(document.getElementById("selRasterLayer").value);
  });
  document.getElementById("rngOpacity").addEventListener("input", () => {
    if (rasterOverlay) {
      rasterOverlay.setOpacity(Number(document.getElementById("rngOpacity").value) / 100);
    }
  });

  // Botón de Nombres de Municipios y Ríos
  document.getElementById("btnToggleLabels").addEventListener("click", () => {
    state.labelsVisible = !state.labelsVisible;
    const btn = document.getElementById("btnToggleLabels");
    btn.textContent = state.labelsVisible ? "🏷️ Nombres: ON" : "🏷️ Nombres: OFF";
    btn.classList.toggle("btn-primary-outline", state.labelsVisible);
    if (state.labelsVisible) {
      if (activeBaseKey !== "google_hybrid") cartoLabelsLayer.addTo(map);
      townLabelsGroup.addTo(map);
    } else {
      if (map.hasLayer(cartoLabelsLayer)) map.removeLayer(cartoLabelsLayer);
      if (map.hasLayer(townLabelsGroup)) map.removeLayer(townLabelsGroup);
    }
  });

  // Minimizar Leyenda e Inspector HUD
  document.getElementById("btnToggleLegend").addEventListener("click", () => {
    const body = document.getElementById("legendBody");
    body.classList.toggle("hidden");
    document.getElementById("btnToggleLegend").textContent = body.classList.contains("hidden") ? "+" : "–";
  });
  document.getElementById("btnToggleHud").addEventListener("click", () => {
    const body = document.getElementById("hudBody");
    body.classList.toggle("hidden");
    document.getElementById("btnToggleHud").textContent = body.classList.contains("hidden") ? "+" : "–";
  });

  // Toggles Vectoriales
  document.getElementById("chkVecTargets").addEventListener("change", (e) => toggleGroup(targetsLayerGroup, e.target.checked));
  document.getElementById("chkVecFallas").addEventListener("change", (e) => toggleGroup(fallasLayerGroup, e.target.checked));
  document.getElementById("chkVecDepositos").addEventListener("change", (e) => toggleGroup(depositosLayerGroup, e.target.checked));
  document.getElementById("chkVecAnm").addEventListener("change", (e) => toggleGroup(anmLayerGroup, e.target.checked));

  // Sincronización entre selectores de Modelo de Depósito (Paso 1 y Paso 5)
  const syncModelSelects = (sourceEl, targetEl) => {
    sourceEl.addEventListener("change", () => {
      targetEl.value = sourceEl.value;
      updateDepositDescription();
      // Si selecciona placer aluvial, sugerir automáticamente capa aluvial o focos limpios
      if (sourceEl.value === "aluvial_placer" && state.analysis) {
        showToast("Modelo Placer Aluvial seleccionado: priorizando terrazas Q-al, gravas y pozas.");
      }
    });
  };
  syncModelSelects(document.getElementById("inpDepositModelQuick"), document.getElementById("inpDepositModel"));
  syncModelSelects(document.getElementById("inpDepositModel"), document.getElementById("inpDepositModelQuick"));

  // Selector de Distrito
  document.getElementById("presetSelect").addEventListener("change", (e) => {
    const p = (state.catalog?.presets || []).find((x) => x.id === e.target.value);
    if (!p) return;
    document.getElementById("inpLat").value = p.lat;
    document.getElementById("inpLon").value = p.lon;
    document.getElementById("inpRoiKm").value = p.roi_size_km;
    document.getElementById("inpDepositModel").value = p.deposit_model;
    document.getElementById("inpDepositModelQuick").value = p.deposit_model;
    document.getElementById("inpSensorMode").value = p.sensor_mode;
    state.customTransect = null;
    updateDmsTelemetry();
    updateDepositDescription();
    runPipeline();
    runMagnetometry(true);
  });

  // Coordenadas: soporte de pegado compuesto (ej. "7.0792, -74.6988" o GMS)
  ["inpLat", "inpLon"].forEach((id) => {
    const el = document.getElementById(id);
    el.addEventListener("input", updateDmsTelemetry);
    el.addEventListener("paste", (ev) => {
      const txt = (ev.clipboardData || window.clipboardData).getData("text");
      const parsed = tryParseCoordinatePair(txt);
      if (parsed) {
        ev.preventDefault();
        document.getElementById("inpLat").value = parsed.lat.toFixed(6);
        document.getElementById("inpLon").value = parsed.lon.toFixed(6);
        updateDmsTelemetry();
        map.flyTo([parsed.lat, parsed.lon], 14, { duration: 0.7 });
        showToast(`Coordenadas aplicadas: ${parsed.lat.toFixed(5)}, ${parsed.lon.toFixed(5)}`);
      }
    });
  });

  document.getElementById("btnCopyCenterGps").addEventListener("click", () => {
    const lat = Number(document.getElementById("inpLat").value);
    const lon = Number(document.getElementById("inpLon").value);
    const dms = `${decimalToDms(lat, true)} ${decimalToDms(lon, false)}`;
    copyToClipboard(`${lat.toFixed(6)}, ${lon.toFixed(6)} (${dms})`, "Coordenada central copiada al portapapeles");
  });

  // Botón Mi Ubicación GPS real del dispositivo
  document.getElementById("btnMyGps").addEventListener("click", () => {
    if (!navigator.geolocation) {
      showToast("Su navegador no soporta geolocalización GPS.");
      return;
    }
    showToast("Obteniendo posición GPS del dispositivo...");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = Number(pos.coords.latitude.toFixed(6));
        const lon = Number(pos.coords.longitude.toFixed(6));
        jumpToLocation(lat, lon, "Mi Ubicación GPS", null, true);
      },
      (err) => {
        showToast("No se pudo acceder al GPS: verifique permisos de ubicación (" + err.message + ")");
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  });

  // Buscador Inteligente Omnibox (Local + Nominatim OSM + Coordenadas)
  bindOmniboxSearch();

  document.getElementById("selIndexInspect").addEventListener("change", renderSelectedIndexStats);
  document.getElementById("btnRunPipeline").addEventListener("click", runPipeline);

  // Atajo Ctrl+R
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "r") {
      e.preventDefault();
      runPipeline();
    }
  });

  // Tema e Idioma
  document.getElementById("btnTheme").addEventListener("click", () => {
    const html = document.documentElement;
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    document.getElementById("btnTheme").textContent = next === "dark" ? "☀" : "🌙";
    if (state.magResult) drawMagnetometry3D();
    if (state.analysis) {
      renderSelectedIndexStats();
      drawFourPillarRadar(state.analysis.prospectivity_summary?.component_scores);
      drawCrossSectionProfile();
    }
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

  // Captura interactiva de muestras supervisadas
  document.getElementById("btnToggleSampleMode").addEventListener("click", () => {
    state.sampleCaptureMode = !state.sampleCaptureMode;
    if (state.sampleCaptureMode) state.measureMode = false;
    const btn = document.getElementById("btnToggleSampleMode");
    btn.textContent = state.sampleCaptureMode ? "🎯 Marcar Muestras: ON" : "🎯 Marcar Muestras: OFF";
    btn.classList.toggle("btn-primary-outline", state.sampleCaptureMode);
  });

  document.getElementById("btnClearSamples").addEventListener("click", () => {
    state.userSamples = [];
    samplesLayerGroup.clearLayers();
    document.getElementById("sampleCount").textContent = "0";
    showToast("Muestras supervisadas limpiadas.");
  });

  // Regla Estructural de Rumbo / Azimut y Corte A–B
  document.getElementById("btnMeasureDist").addEventListener("click", () => {
    state.measureMode = !state.measureMode;
    state.sampleCaptureMode = false;
    state.measurePts = [];
    if (rubberBandLine) {
      map.removeLayer(rubberBandLine);
      rubberBandLine = null;
    }
    if (!state.measureMode) {
      measureLayerGroup.clearLayers();
    } else {
      measureLayerGroup.clearLayers();
      showToast("Haga clic en Punto A y Punto B en el mapa para medir Rumbo Estructural y trazar el Corte A–B.");
    }
    const btn = document.getElementById("btnMeasureDist");
    btn.classList.toggle("btn-primary-outline", state.measureMode);
    btn.textContent = state.measureMode ? "📏 Marque A → B en Mapa" : "📏 Rumbo / Corte A–B";
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

  // Exportaciones Directas a Campo (.GPX, .KML, .GeoJSON, .CSV, .geoau, PDF/HTML)
  document.getElementById("btnExportGpx").addEventListener("click", exportTargetsGpx);
  document.getElementById("btnQuickGpx").addEventListener("click", exportTargetsGpx);
  document.getElementById("btnExportKml").addEventListener("click", exportTargetsKml);
  document.getElementById("btnQuickKml").addEventListener("click", exportTargetsKml);

  document.getElementById("btnExportGeojson").addEventListener("click", () => {
    if (!state.analysis) return;
    downloadTextFile(
      JSON.stringify(state.analysis.targets_geojson, null, 2),
      "focos_oro_geoauv2.geojson",
      "application/geo+json"
    );
    showToast("Archivo GeoJSON exportado.");
  });

  document.getElementById("btnExportCsv").addEventListener("click", () => {
    if (!state.analysis) return;
    downloadTextFile(state.analysis.targets_csv, "focos_oro_geoauv2.csv", "text/csv;charset=utf-8");
    showToast("Tabla CSV exportada.");
  });

  const openPrintableReport = () => {
    if (!state.analysis?.standalone_report_html) return;
    const w = window.open("", "_blank");
    if (w) {
      w.document.open();
      w.document.write(state.analysis.standalone_report_html);
      w.document.close();
    }
  };
  document.getElementById("btnOpenHtmlReport").addEventListener("click", openPrintableReport);
  document.getElementById("btnQuickPdf").addEventListener("click", openPrintableReport);

  document.getElementById("btnExportGeoau").addEventListener("click", () => {
    const cfg = buildAnalysisPayload();
    downloadTextFile(JSON.stringify(cfg, null, 2), "proyecto_exploracion.geoau", "application/json");
    showToast("Configuración .geoau descargada.");
  });

  document.getElementById("btnSaveCloudProject").addEventListener("click", saveProjectToSupabase);
  document.getElementById("selGeeTemplate").addEventListener("change", fetchGeeTemplate);
  document.getElementById("btnCopyGee").addEventListener("click", async () => {
    const code = document.getElementById("geeCodeBox").textContent;
    await copyToClipboard(code, "Código Google Earth Engine copiado");
  });
  document.getElementById("btnDownloadGee").addEventListener("click", () => {
    const code = document.getElementById("geeCodeBox").textContent;
    const tpl = document.getElementById("selGeeTemplate").value;
    downloadTextFile(code, `geoauv2_${tpl}.js`, "application/javascript");
  });

  // Modales Guía y Nube
  document.getElementById("btnOpenGuide").addEventListener("click", () => {
    document.getElementById("guideModal").classList.remove("hidden");
  });
  document.getElementById("btnCloseGuide").addEventListener("click", () => {
    document.getElementById("guideModal").classList.add("hidden");
  });
  document.getElementById("btnCloudHistory").addEventListener("click", openCloudModal);
  document.getElementById("btnCloseModal").addEventListener("click", () => {
    document.getElementById("cloudModal").classList.add("hidden");
  });
}

/* ============================================================================
   3. Buscador Inteligente de Lugares y Conversor Decimal <-> GMS (DMS)
   ============================================================================ */
function bindOmniboxSearch() {
  const inp = document.getElementById("inpPlaceSearch");
  const dd = document.getElementById("searchDropdown");

  inp.addEventListener("input", () => {
    const q = inp.value.trim();
    if (q.length < 2) {
      dd.classList.add("hidden");
      return;
    }

    // 1. Verificar si pegó coordenadas directas
    const coord = tryParseCoordinatePair(q);
    if (coord) {
      dd.innerHTML = `<div class="search-item" data-lat="${coord.lat}" data-lon="${coord.lon}" data-name="Coordenada GPS">
        <div><strong>📍 Ir a Coordenada Exacta</strong><br><small>${coord.lat.toFixed(6)}, ${coord.lon.toFixed(6)}</small></div>
        <span class="pill">Analizar</span>
      </div>`;
      dd.classList.remove("hidden");
      attachSearchItemClicks(dd);
      return;
    }

    // 2. Coincidencias instantáneas en catálogo aurífero local
    const ql = q.toLowerCase();
    const localHits = MINING_PLACES_DB.filter(
      (p) => p.name.toLowerCase().includes(ql) || p.sub.toLowerCase().includes(ql)
    ).slice(0, 6);

    renderSearchDropdown(localHits, []);

    // 3. Búsqueda geográfica global complementaria en OpenStreetMap Nominatim
    clearTimeout(state.nominatimTimer);
    state.nominatimTimer = setTimeout(async () => {
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&limit=5&countrycodes=co,pe,bo,ec,cl,us&q=${encodeURIComponent(q)}`;
        const r = await fetch(url, { headers: { "Accept-Language": "es" } });
        if (!r.ok) return;
        const remote = await r.json();
        const osmHits = (remote || []).map((it) => ({
          name: it.display_name.split(",").slice(0, 2).join(", "),
          sub: it.display_name.split(",").slice(2, 4).join(", "),
          lat: Number(it.lat),
          lon: Number(it.lon),
          model: null,
        }));
        renderSearchDropdown(localHits, osmHits);
      } catch (_) {
        /* silencioso si sin red externa */
      }
    }, 340);
  });

  inp.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const first = dd.querySelector(".search-item");
      if (first) first.click();
    }
  });

  document.addEventListener("click", (e) => {
    if (!document.getElementById("searchOmniWrap").contains(e.target)) {
      dd.classList.add("hidden");
    }
  });
}

function renderSearchDropdown(localHits, osmHits) {
  const dd = document.getElementById("searchDropdown");
  const combined = [...localHits];
  osmHits.forEach((o) => {
    if (!combined.some((c) => Math.abs(c.lat - o.lat) < 0.03 && Math.abs(c.lon - o.lon) < 0.03)) {
      combined.push(o);
    }
  });

  if (!combined.length) {
    dd.classList.add("hidden");
    return;
  }

  dd.innerHTML = combined
    .slice(0, 8)
    .map(
      (item) => `<div class="search-item" data-lat="${item.lat}" data-lon="${item.lon}" data-name="${item.name}" data-model="${item.model || ""}">
        <div><strong>${item.name}</strong><br><small>${item.sub || ""}</small></div>
        <span class="pill">${item.model === "aluvial_placer" ? "🌊 Aluvial" : (item.model ? "⛏️ Distrito Au" : "🗺️ Mapa")}</span>
      </div>`
    )
    .join("");
  dd.classList.remove("hidden");
  attachSearchItemClicks(dd);
}

function attachSearchItemClicks(dd) {
  dd.querySelectorAll(".search-item").forEach((el) => {
    el.addEventListener("click", () => {
      const lat = Number(el.dataset.lat);
      const lon = Number(el.dataset.lon);
      const nm = el.dataset.name;
      const mdl = el.dataset.model || null;
      dd.classList.add("hidden");
      document.getElementById("inpPlaceSearch").value = nm;
      jumpToLocation(lat, lon, nm, mdl, true);
    });
  });
}

function jumpToLocation(lat, lon, labelName, modelOverride, autoRun = true) {
  document.getElementById("inpLat").value = lat.toFixed(5);
  document.getElementById("inpLon").value = lon.toFixed(5);
  if (modelOverride) {
    document.getElementById("inpDepositModel").value = modelOverride;
    document.getElementById("inpDepositModelQuick").value = modelOverride;
    updateDepositDescription();
  }
  state.customTransect = null;
  updateDmsTelemetry();
  map.flyTo([lat, lon], 14, { duration: 0.75 });
  if (autoRun) {
    runPipeline(labelName);
    runMagnetometry(true);
  }
}

function tryParseCoordinatePair(str) {
  if (!str) return null;
  // Formato decimal simple: "7.0792, -74.6988" o "7.0792 -74.6988"
  const decMatch = str.trim().match(/^(-?\d{1,2}\.\d+)\s*[,;\s]\s*(-?\d{1,3}\.\d+)$/);
  if (decMatch) {
    const la = Number(decMatch[1]);
    const lo = Number(decMatch[2]);
    if (Math.abs(la) <= 90 && Math.abs(lo) <= 180) return { lat: la, lon: lo };
  }
  // Formato GMS: 7°04'45"N 74°41'55"W
  const dmsRegex = /(\d{1,3})[°º\s]+(\d{1,2})['’\s]+(\d{1,2}(?:\.\d+)?)["”\s]*([NSEWO])/gi;
  const parts = [...str.matchAll(dmsRegex)];
  if (parts.length >= 2) {
    const toDec = (m) => {
      let v = Number(m[1]) + Number(m[2]) / 60 + Number(m[3]) / 3600;
      const hem = m[4].toUpperCase();
      if (hem === "S" || hem === "W" || hem === "O") v = -v;
      return v;
    };
    const la = toDec(parts[0]);
    const lo = toDec(parts[1]);
    if (Math.abs(la) <= 90 && Math.abs(lo) <= 180) return { lat: la, lon: lo };
  }
  return null;
}

function decimalToDms(deg, isLat) {
  const abs = Math.abs(Number(deg) || 0);
  const d = Math.floor(abs);
  const mFloat = (abs - d) * 60;
  const m = Math.floor(mFloat);
  const s = ((mFloat - m) * 60).toFixed(1);
  const hem = isLat ? (deg >= 0 ? "N" : "S") : (deg >= 0 ? "E" : "W");
  return `${d}°${String(m).padStart(2, "0")}'${String(s).padStart(4, "0")}"${hem}`;
}

function updateDmsTelemetry() {
  const lat = Number(document.getElementById("inpLat").value);
  const lon = Number(document.getElementById("inpLon").value);
  const el = document.getElementById("dmsTelemetryBar");
  if (el && !isNaN(lat) && !isNaN(lon)) {
    el.textContent = `${decimalToDms(lat, true)} · ${decimalToDms(lon, false)}`;
  }
}

/* ============================================================================
   4. Ejecución del Motor Analítico y Renderizado de Resultados
   ============================================================================ */
function activateStep(stepNum) {
  document.querySelectorAll(".step-btn").forEach((b) => b.classList.toggle("active", b.dataset.step === String(stepNum)));
  document.querySelectorAll(".step-pane").forEach((p) => p.classList.toggle("active", p.id === `step-${stepNum}`));

  const sel = document.getElementById("selRasterLayer");
  if (stepNum === "2") sel.value = "idx_arcilla";
  else if (stepNum === "4") sel.value = "ml_clusters";
  else if (stepNum === "5") sel.value = "favorability";
  else if (stepNum === "6" || stepNum === "7") sel.value = "gold_hotspots";
  updateActiveRasterOverlay();
  updateLegendForLayer(sel.value);
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
    console.warn("Verificación de salud API:", err);
  }
}

async function loadCatalog() {
  const r = await fetch("/api/catalog");
  state.catalog = await r.json();

  const presetSel = document.getElementById("presetSelect");
  presetSel.innerHTML = (state.catalog.presets || [])
    .map((p) => `<option value="${p.id}">${p.name}</option>`)
    .join("");

  const modelHtml = Object.entries(state.catalog.deposit_models || {})
    .map(([k, v]) => `<option value="${k}">${v.label}</option>`)
    .join("");

  const depSel = document.getElementById("inpDepositModel");
  const depQuick = document.getElementById("inpDepositModelQuick");
  depSel.innerHTML = modelHtml;
  depQuick.innerHTML = modelHtml;
  depSel.value = "orogenico_vetas";
  depQuick.value = "orogenico_vetas";
  updateDepositDescription();

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

function buildAnalysisPayload(customProjectName = null) {
  const presetId = document.getElementById("presetSelect").value;
  const presetObj = (state.catalog?.presets || []).find((p) => p.id === presetId);
  const lat = Number(document.getElementById("inpLat").value);
  const lon = Number(document.getElementById("inpLon").value);
  const sameAsPreset = presetObj && Math.abs(presetObj.lat - lat) < 0.01 && Math.abs(presetObj.lon - lon) < 0.01;

  return {
    preset_id: sameAsPreset ? presetId : null,
    project_name: customProjectName || (sameAsPreset ? presetObj.name : null),
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

function startLoadingProgress() {
  const loader = document.getElementById("loadingOverlay");
  const txt = document.getElementById("loadingStepText");
  const bar = document.getElementById("loadingProgressBar");
  loader.classList.remove("hidden");

  const steps = [
    [22, "Ensamblando mosaico satelital libre de nubes HD (Sentinel-2 / Óptico)..."],
    [48, "Consultando fallas y ocurrencias del Servicio Geológico (SGC) y Catastro ANM..."],
    [72, "Calculando 27 índices mineralógicos y clasificación IA de alteraciones..."],
    [90, "Delimitando focos de oro (P1/P2), isolíneas y estado jurídico por blanco..."],
  ];
  let idx = 0;
  bar.style.width = "16%";
  txt.textContent = steps[0][1];
  clearInterval(state.loadingTimer);
  state.loadingTimer = setInterval(() => {
    if (idx < steps.length) {
      bar.style.width = `${steps[idx][0]}%`;
      txt.textContent = steps[idx][1];
      idx++;
    }
  }, 420);
}

function stopLoadingProgress() {
  clearInterval(state.loadingTimer);
  document.getElementById("loadingProgressBar").style.width = "100%";
  setTimeout(() => {
    document.getElementById("loadingOverlay").classList.add("hidden");
  }, 140);
}

async function runPipeline(customName = null) {
  startLoadingProgress();
  try {
    const cleanName = typeof customName === "string" ? customName : null;
    const payload = buildAnalysisPayload(cleanName);
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
    console.error("Error ejecutando análisis GeoAuV2:", err);
    showToast("Error procesando el cuadrante: " + err.message);
  } finally {
    stopLoadingProgress();
  }
}

function renderAllAnalysisViews(data) {
  const prosp = data.prospectivity_summary;
  const val = data.validation;
  const diag = data.diagnostics;
  const targets = data.targets || [];
  const p1Count = targets.filter((t) => t.priority_code === "P1").length;
  const freeCount = targets.filter((t) => t.is_free_area !== false).length;

  // 1. KPIs Izquierdos
  const kpiMpi = document.getElementById("kpiMpi");
  kpiMpi.textContent = `${prosp.mpi} (${prosp.classification_code})`;
  kpiMpi.style.color = prosp.classification_color;
  document.getElementById("kpiClass").textContent = prosp.classification_label;
  document.getElementById("kpiTargets").textContent = `${targets.length} (${p1Count} P1)`;
  document.getElementById("kpiAreaPct").textContent = `${freeCount} en Área Libre ANM`;
  document.getElementById("kpiKappa").textContent = `κ ${val.kappa}`;
  document.getElementById("kpiGain").textContent = `Ganancia ${val.spatial_gain}×`;

  // 2. Drawer Derecho: Resumen Ejecutivo Hero + Radar 4 Pilares + Corte A–B
  document.getElementById("execZoneSubtitle").textContent =
    `${data.metadata.roi_name} · ${data.metadata.roi_size_km}×${data.metadata.roi_size_km} km`;
  const heroVal = document.getElementById("heroMpiVal");
  heroVal.textContent = Math.round(prosp.mpi);
  heroVal.style.color = prosp.classification_color;
  const qBadge = document.getElementById("heroClassBadge");
  qBadge.textContent = `Categoría ${prosp.classification_code} · Confianza ${prosp.confidence}`;
  qBadge.style.borderColor = prosp.classification_color;
  qBadge.style.color = prosp.classification_color;
  document.getElementById("heroClassLabel").textContent = prosp.classification_label;

  const aluvBadge = diag.alluvial_mining_active_pct >= 0.4
    ? `<span class="pill">🌊 Aluvial Activo ${diag.alluvial_mining_active_pct}%</span>`
    : "";
  document.getElementById("heroQuickTags").innerHTML = `
    <span class="pill">🎯 ${targets.length} Focos (${p1Count} P1)</span>
    <span class="legal-pill free">🟢 ${freeCount} Libres</span>
    ${aluvBadge}
  `;
  document.getElementById("opticalSourceBadge").textContent = (diag.optical_source || "Sin Nubes HD").slice(0, 26);

  drawFourPillarRadar(prosp.component_scores);
  drawCrossSectionProfile();
  renderTargetCardsList(targets, "execHotspotsList", 6);
  renderTargetCardsList(targets, "targetsList", 25);

  // 3. Paso 1: Cascada y Trazabilidad
  const ms = diag.mask_stats || {};
  document.getElementById("cascadeBadges").innerHTML = `
    <span class="pill">${diag.optical_source || "Mosaico Sin Nubes"}</span>
    <span class="pill">SWIR: ${diag.aster_swir_available ? "14 Bandas" : "Cascada S2+L8"}</span>
    <span class="pill">Suelo/Roca Analizable: ${ms.valid_rock_soil_pct || 0}%</span>
  `;
  document.getElementById("cascadeLogs").innerHTML = (diag.cascade_logs || [])
    .map((l) => `<li>${l}</li>`)
    .join("");

  // 4. Paso 2: Índices e Histograma
  const idxSel = document.getElementById("selIndexInspect");
  const prevVal = idxSel.value;
  const idxKeys = Object.keys(data.indices_stats || {});
  idxSel.innerHTML = idxKeys
    .map((k) => `<option value="${k}">${data.indices_stats[k].name} (${k})</option>`)
    .join("");
  if (idxKeys.includes(prevVal)) idxSel.value = prevVal;
  renderSelectedIndexStats();

  // 5. Paso 3: Stack Multibanda IA
  const stInfo = data.stack_info;
  document.getElementById("stackMetaBox").textContent =
    `Matriz activa: ${stInfo.dimensions.join(" × ")} (${stInfo.bands_count} capas · ${stInfo.memory_kb} KB)`;
  document.getElementById("stackCheckList").innerHTML = idxKeys
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

  // 6. Paso 4: IA / Machine Learning
  const ml = data.ml_summary;
  const sim = ml.spectral_similarity || {};
  document.getElementById("spectralSimBox").innerHTML =
    `<strong>Similitud Espectral con Minas Ancla:</strong> Coherencia LOO <code>${sim.loo_coherence ?? "--"}</code> · Δ Fondo <code>${sim.discrimination_delta ?? "--"}</code><br><small>${sim.verdict || ""}</small>`;

  const accBox = document.getElementById("mlAccuracyBox");
  if (ml.accuracy_metrics) {
    const am = ml.accuracy_metrics;
    accBox.innerHTML = `<div class="mini-stats-grid" style="margin-top:6px;">
      <div class="mini-stat"><span>Precisión OA</span><strong>${(am.overall_accuracy * 100).toFixed(1)}%</strong></div>
      <div class="mini-stat"><span>Kappa IA</span><strong>${am.kappa}</strong></div>
      <div class="mini-stat"><span>Entrenamiento</span><strong>${am.training_samples} px</strong></div>
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

  // 7. Paso 5: Favorabilidad Mineral
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

  // 8. Paso 6: Pilares + SGC/ANM
  const cs = prosp.component_scores || {};
  const compMap = [
    ["Alteración Espectral / Aluvial", cs.spectral || 0],
    ["Control Estructural & Relieve DEM", cs.structural || 0],
    ["Geología y Metalogenia SGC", cs.geological_sgc || 0],
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
    <div class="mini-stat"><span>Densidad Estruct.</span><strong>${stStats.lineament_density_mean}</strong></div>
  `;

  const sgc = data.sgc_metrics || {};
  const leg = data.legal_status || {};
  document.getElementById("sgcAnmSummary").innerHTML = `
    <p class="muted-note"><strong>Fallas SGC:</strong> ${sgc.fault_count} trazas (más cercana: ${sgc.nearest_fault_km} km · densidad ${sgc.fault_density_km_km2} km/km²)</p>
    <p class="muted-note"><strong>Referencia Aurífera:</strong> ${sgc.nearest_deposit_name || "Área de exploración"} ${sgc.known_gold_grade_gt ? `(${sgc.known_gold_grade_gt} g/t Au)` : ""}</p>
    <p class="muted-note"><strong>Ambiente Geológico:</strong> ${sgc.deposit_type_detected}</p>
    <p class="muted-note"><strong>Catastro Minero ANM:</strong> <span style="color:var(--accent);">${leg.status_summary}</span></p>
  `;

  // 9. Paso 8: Validación Estadística
  document.getElementById("valLandisBadge").innerHTML =
    `<strong>Concordancia Kappa = ${val.kappa}:</strong> ${val.kappa_interpretation}<br><small>Proyección métrica: EPSG:${val.utm_epsg} · ${val.validation_mode}</small>`;
  document.getElementById("valMetricsGrid").innerHTML = `
    <div class="mini-stat"><span>Precisión OA</span><strong>${(val.overall_accuracy * 100).toFixed(1)}%</strong></div>
    <div class="mini-stat"><span>F1-Score</span><strong>${val.f1_score}</strong></div>
    <div class="mini-stat"><span>Ganancia Espacial</span><strong>${val.spatial_gain}×</strong></div>
    <div class="mini-stat"><span>Tasa Captura</span><strong>${val.capture_rate_pct}%</strong></div>
    <div class="mini-stat"><span>Precisión Pos.</span><strong>${(val.precision * 100).toFixed(1)}%</strong></div>
    <div class="mini-stat"><span>Área Blanca</span><strong>${val.target_area_pct_of_roi}%</strong></div>
  `;
  const cm = val.confusion_matrix || {};
  document.getElementById("valConfusionTable").innerHTML = `
    <table class="data-table">
      <thead><tr><th>Real \\ Predicho</th><th>En Foco Aurífero</th><th>Fondo Estéril</th></tr></thead>
      <tbody>
        <tr><td><strong>Yacimiento / Control (+)</strong></td><td>TP = <b>${cm.tp}</b></td><td>FN = ${cm.fn}</td></tr>
        <tr><td><strong>Fondo Aleatorio (–)</strong></td><td>FP = ${cm.fp}</td><td>TN = <b>${cm.tn}</b></td></tr>
      </tbody>
    </table>
  `;
  document.getElementById("valControlPoints").innerHTML = (val.control_points || [])
    .map(
      (cp) => `<div class="cluster-card">
        <div class="row-between">
          <strong>${cp.name}</strong>
          <span style="color:${cp.captured ? "var(--success)" : "#ef4444"};font-weight:700;">
            ${cp.captured ? "✓ Capturado" : "✕ Fuera"} (${cp.distance_to_target_m} m)
          </span>
        </div>
        <small style="color:var(--text-muted);">${cp.source} · (${cp.lat}, ${cp.lon})</small>
      </div>`
    )
    .join("");

  // 10. Paso 9: Plan Operativo & GEE
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

  // 11. Renderizar Geometrías, Pines Pulsantes y Capas Ráster en el Mapa
  renderMapLayers(data);
}

function renderTargetCardsList(targets, containerId, maxCount) {
  const wrap = document.getElementById(containerId);
  if (!wrap) return;
  if (!targets || targets.length === 0) {
    wrap.innerHTML = `<div class="info-banner">0 focos superan el umbral actual (${document.getElementById("inpTargetThr").value}). Zona estéril o control negativo.</div>`;
    return;
  }

  wrap.innerHTML = targets
    .slice(0, maxCount)
    .map((t) => {
      const pkLat = t.peak_lat ?? t.lat;
      const pkLon = t.peak_lon ?? t.lon;
      const pct = Math.round(t.score_max * 100);
      const isFree = t.is_free_area !== false;
      const legClass = isFree ? "free" : "titled";
      const legIcon = isFree ? "🟢" : "🔵";
      const gmaps = `https://www.google.com/maps?q=${pkLat},${pkLon}`;
      return `<div class="target-card" style="border-left-color:${t.color}" onclick="zoomToTarget(${pkLat}, ${pkLon})">
        <div class="row-between">
          <strong>🎯 ${t.id || "#" + t.rank} · ${t.priority_code} (${pct}% Au)</strong>
          <span class="pill">${t.area_ha} ha</span>
        </div>
        <div class="row-between" style="margin-top:4px;">
          <span style="color:var(--text-muted);font-size:10.5px;">${t.dominant_alteration}</span>
          <span class="legal-pill ${legClass}">${legIcon} ${t.legal_state || "Área Libre"}</span>
        </div>
        <div class="mono" style="font-size:10.5px;color:var(--accent);margin-top:4px;">
          Pico: ${pkLat.toFixed(5)}, ${pkLon.toFixed(5)}
        </div>
        <div class="target-actions" onclick="event.stopPropagation();">
          <button type="button" class="btn-xs" onclick="zoomToTarget(${pkLat}, ${pkLon})">🔍 Zoom</button>
          <button type="button" class="btn-xs" onclick="copyGpsPair(${pkLat}, ${pkLon}, '${t.id || t.rank}')">📋 Copiar GPS</button>
          <button type="button" class="btn-xs" onclick="profileAcrossPoint(${pkLat}, ${pkLon}, '${t.id || t.rank}')">📈 Corte A–B</button>
          <a href="${gmaps}" target="_blank" rel="noopener" class="btn-xs" style="text-decoration:none;">🧭 Maps ↗</a>
        </div>
      </div>`;
    })
    .join("");
}

window.zoomToTarget = function (lat, lon) {
  map.flyTo([lat, lon], 16, { duration: 0.75 });
};

window.copyGpsPair = function (lat, lon, label) {
  const dms = `${decimalToDms(lat, true)} ${decimalToDms(lon, false)}`;
  copyToClipboard(`${lat.toFixed(6)}, ${lon.toFixed(6)} (${dms})`, `GPS de ${label} copiado`);
};

window.profileAcrossPoint = function (lat, lon, label) {
  const spanDeg = 0.008; // ~1.8 km sección WSW-ENE perpendicular a estructuras andinas típicas
  state.customTransect = [
    [lat - spanDeg * 0.38, lon - spanDeg * 0.92],
    [lat + spanDeg * 0.38, lon + spanDeg * 0.92],
  ];
  document.getElementById("profileSourceLbl").textContent = `Sección: ${label}`;
  drawCrossSectionProfile();
  drawTransectLineOnMap(state.customTransect[0], state.customTransect[1], `Corte ${label}`);
  showToast(`Corte Topográfico–Aurífero trazado sobre ${label}`);
};

/* ============================================================================
   5. Visualización Cartográfica de Alta Nitidez (Pines 🎯 Pulsantes + Fondo Limpio)
   ============================================================================ */
function renderMapLayers(data) {
  const [minLon, minLat, maxLon, maxLat] = data.metadata.bbox;
  const bounds = [[minLat, minLon], [maxLat, maxLon]];

  if (roiLayer) map.removeLayer(roiLayer);
  roiLayer = L.rectangle(bounds, {
    color: "#fde047",
    weight: 2,
    fillOpacity: 0.0,
    dashArray: "7,5",
    interactive: false,
  }).addTo(map);

  if (centerCrosshair) map.removeLayer(centerCrosshair);
  centerCrosshair = L.circleMarker([data.metadata.center_lat, data.metadata.center_lon], {
    radius: 4,
    color: "#fde047",
    weight: 1.5,
    fillColor: "#0b0f17",
    fillOpacity: 0.8,
  }).bindTooltip("Centro del Cuadrante").addTo(map);

  map.fitBounds(bounds, { padding: [32, 32] });
  updateActiveRasterOverlay();
  updateLegendForLayer(document.getElementById("selRasterLayer").value);

  // 1. Blancos Auríferos: Polígonos Translúcidos + Pines Bullseye Pulsantes en el Pico Exacto
  targetsLayerGroup.clearLayers();
  if (data.targets_geojson?.features?.length) {
    L.geoJSON(data.targets_geojson, {
      style: (feat) => {
        const isP1 = feat.properties.priority_code === "P1";
        return {
          color: isP1 ? "#fde047" : (feat.properties.color || "#f59e0b"),
          weight: isP1 ? 2.6 : 2.0,
          fillColor: feat.properties.color || "#ef4444",
          fillOpacity: 0.14,
          dashArray: isP1 ? null : "4,3",
        };
      },
      onEachFeature: (feat, layer) => {
        layer.bindPopup(buildTargetPopupHtml(feat.properties));
      },
    }).addTo(targetsLayerGroup);
  }

  // Pines numerados pulsantes exactamente en (peak_lat, peak_lon)
  (data.targets || []).slice(0, 12).forEach((t) => {
    const pkLat = t.peak_lat ?? t.lat;
    const pkLon = t.peak_lon ?? t.lon;
    const pct = Math.round(t.score_max * 100);
    const pCls = t.priority_code === "P1" ? "p1" : (t.priority_code === "P2" ? "p2" : "p3");

    const pinIcon = L.divIcon({
      className: "",
      html: `<div class="au-hotspot-pin">
        ${t.priority_code !== "P3" ? `<span class="au-pin-pulse ${pCls}"></span>` : ""}
        <span class="au-pin-badge ${pCls}">🎯 #${t.rank} · ${pct}%</span>
      </div>`,
      iconSize: [86, 26],
      iconAnchor: [43, 13],
    });

    L.marker([pkLat, pkLon], { icon: pinIcon, zIndexOffset: 650 - t.rank * 10 })
      .bindPopup(buildTargetPopupHtml(t))
      .addTo(targetsLayerGroup);
  });

  // 2. Fallas Estructurales SGC
  fallasLayerGroup.clearLayers();
  if (data.vector_layers?.fallas?.features?.length) {
    L.geoJSON(data.vector_layers.fallas, {
      style: { color: "#00e5ff", weight: 2.3, dashArray: "6,4", opacity: 0.9 },
      onEachFeature: (f, l) => {
        const pr = f.properties || {};
        l.bindPopup(
          `<div class="popup-card"><div class="popup-head">⚡ Estructura / Falla SGC</div>` +
          `<div>${pr.NOMBRE || pr.TIPO || "Traza estructural cartografiada"}</div></div>`
        );
      },
    }).addTo(fallasLayerGroup);
  }

  // 3. Minas Conocidas y Yacimientos Oficiales SGC (Distintivo 🪙)
  depositosLayerGroup.clearLayers();
  (data.validation?.control_points || []).forEach((cp) => {
    const isCrossCheck = (cp.source || "").includes("Cross-Check");
    if (isCrossCheck) return; // No duplicar pines sobre anomalías auto-generadas en áreas sin catálogo
    const mineIcon = L.divIcon({
      className: "",
      html: `<div class="mine-ref-pin">🪙 ${cp.name.slice(0, 18)}</div>`,
      iconSize: null,
      iconAnchor: [45, 12],
    });
    L.marker([cp.lat, cp.lon], { icon: mineIcon, zIndexOffset: 300 })
      .bindPopup(
        `<div class="popup-card">
          <div class="popup-head">🪙 ${cp.name}</div>
          <div><strong>Fuente:</strong> ${cp.source}</div>
          <div><strong>Distancia a Blanco IA:</strong> ${cp.distance_to_target_m} m</div>
          <div class="popup-gps">${cp.lat.toFixed(5)}, ${cp.lon.toFixed(5)}</div>
        </div>`
      )
      .addTo(depositosLayerGroup);
  });

  // 4. Títulos Mineros ANM
  anmLayerGroup.clearLayers();
  if (data.vector_layers?.titulos_vigentes?.features?.length) {
    L.geoJSON(data.vector_layers.titulos_vigentes, {
      style: { color: "#a855f7", weight: 1.8, fillColor: "#a855f7", fillOpacity: 0.08 },
      onEachFeature: (f, l) => {
        const pr = f.properties || {};
        const exp = pr.CODIGO_EXPEDIENTE || pr.NUMERO_EXPEDIENTE || pr.EXPEDIENTE || "Vigente";
        const tit = pr.NOMBRE_DE_TITULAR || pr.TITULAR || "Concesión Minera Registrada";
        l.bindPopup(
          `<div class="popup-card">
            <div class="popup-head" style="color:#c084fc;">📜 Título Minero ANM</div>
            <div><strong>Expediente:</strong> ${exp}</div>
            <div><strong>Titular:</strong> ${tit}</div>
            <div><strong>Mineral:</strong> ${pr.MINERALES || "Metales Preciosos"}</div>
          </div>`
        );
      },
    }).addTo(anmLayerGroup);
  }
}

function buildTargetPopupHtml(p) {
  const pkLat = Number(p.peak_lat ?? p.lat);
  const pkLon = Number(p.peak_lon ?? p.lon);
  const dms = `${decimalToDms(pkLat, true)}<br>${decimalToDms(pkLon, false)}`;
  const pct = Math.round(Number(p.score_max) * 100);
  const isFree = p.is_free_area !== false;
  const legColor = isFree ? "#34d399" : "#60a5fa";
  const gmaps = `https://www.google.com/maps?q=${pkLat},${pkLon}`;

  return `<div class="popup-card">
    <div class="popup-head">
      <span>🎯 Foco ${p.id || "#" + p.rank} (${p.priority_code})</span>
      <span>${pct}% Au</span>
    </div>
    <div><strong>Dominio:</strong> ${p.dominant_alteration}</div>
    <div><strong>Extensión:</strong> ${p.area_ha} ha · Media: ${Math.round(Number(p.score_mean) * 100)}%</div>
    <div><strong>Catastro ANM:</strong> <span style="color:${legColor};font-weight:700;">${p.legal_state || "Área Libre"}</span></div>
    <div class="popup-gps">
      <strong>Foco Pico Exacto (WGS84):</strong><br>
      ${pkLat.toFixed(6)}, ${pkLon.toFixed(6)}<br>
      <span style="color:#94a3b8;">${dms}</span>
    </div>
    <div class="popup-btns">
      <button type="button" class="popup-btn" onclick="copyGpsPair(${pkLat}, ${pkLon}, '${p.id || p.rank}')">📋 Copiar GPS</button>
      <a href="${gmaps}" target="_blank" rel="noopener" class="popup-btn">🧭 Google Maps</a>
    </div>
  </div>`;
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

function updateLegendForLayer(layerKey) {
  const cfg = LEGEND_CONFIGS[layerKey] || {
    title: "🛰️ Capa Satelital / Índice Mineralógico",
    gradient: "linear-gradient(90deg, #1e293b 0%, #38bdf8 50%, #fde047 100%)",
    ticks: ["Mín (P2)", "Bajo", "Medio", "Máx (P98)"],
  };
  document.getElementById("legendTitle").textContent = cfg.title;
  document.getElementById("legendGradientBar").style.background = cfg.gradient;
  document.getElementById("legendTicks").innerHTML = cfg.ticks.map((t) => `<span>${t}</span>`).join("");
}

/* ============================================================================
   6. Gráfico Radar Retina de 4 Pilares & Corte Transversal Topográfico-Aurífero A–B
   ============================================================================ */
function drawFourPillarRadar(scores) {
  const canvas = document.getElementById("radarChartCanvas");
  if (!canvas || !scores) return;
  const dpr = window.devicePixelRatio || 1;
  const cssW = 320;
  const cssH = 205;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, cssW, cssH);

  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  const gridCol = isLight ? "rgba(15, 23, 42, 0.14)" : "rgba(148, 163, 184, 0.2)";
  const txtCol = isLight ? "#0f172a" : "#e2e8f0";

  const cx = cssW / 2;
  const cy = cssH / 2 + 4;
  const R = 68;
  const axes = [
    { label: `Espectral (${Math.round(scores.spectral || 0)})`, val: (scores.spectral || 0) / 100, ang: -Math.PI / 2 },
    { label: `Estructural (${Math.round(scores.structural || 0)})`, val: (scores.structural || 0) / 100, ang: 0 },
    { label: `Geología SGC (${Math.round(scores.geological_sgc || 0)})`, val: (scores.geological_sgc || 0) / 100, ang: Math.PI / 2 },
    { label: `Geofísica (${Math.round(scores.geophysical || 0)})`, val: (scores.geophysical || 0) / 100, ang: Math.PI },
  ];

  // Anillos concéntricos (25%, 50%, 75%, 100%)
  ctx.strokeStyle = gridCol;
  ctx.lineWidth = 1;
  [0.25, 0.5, 0.75, 1.0].forEach((lvl) => {
    ctx.beginPath();
    axes.forEach((ax, idx) => {
      const x = cx + Math.cos(ax.ang) * R * lvl;
      const y = cy + Math.sin(ax.ang) * R * lvl;
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.stroke();
  });

  // Ejes
  axes.forEach((ax) => {
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(ax.ang) * R, cy + Math.sin(ax.ang) * R);
    ctx.stroke();
  });

  // Polígono Aurífero
  ctx.beginPath();
  axes.forEach((ax, idx) => {
    const rVal = Math.max(0.06, Math.min(1.0, ax.val)) * R;
    const x = cx + Math.cos(ax.ang) * rVal;
    const y = cy + Math.sin(ax.ang) * rVal;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fillStyle = "rgba(245, 158, 11, 0.30)";
  ctx.fill();
  ctx.strokeStyle = "#fde047";
  ctx.lineWidth = 2.2;
  ctx.stroke();

  // Nodos y etiquetas
  ctx.font = "700 10.5px Inter";
  ctx.fillStyle = txtCol;
  axes.forEach((ax, idx) => {
    const rVal = Math.max(0.06, Math.min(1.0, ax.val)) * R;
    const px = cx + Math.cos(ax.ang) * rVal;
    const py = cy + Math.sin(ax.ang) * rVal;
    ctx.beginPath();
    ctx.arc(px, py, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = "#fde047";
    ctx.fill();

    ctx.fillStyle = txtCol;
    ctx.textAlign = idx === 1 ? "left" : (idx === 3 ? "right" : "center");
    const lx = cx + Math.cos(ax.ang) * (R + 12);
    const ly = cy + Math.sin(ax.ang) * (R + 14) + (idx === 2 ? 6 : 0);
    ctx.fillText(ax.label, lx, ly);
  });
  ctx.textAlign = "left";
}

function drawCrossSectionProfile() {
  const canvas = document.getElementById("profileCanvas");
  const pi = state.analysis?.pixel_inspector;
  if (!canvas || !pi?.elevation_m || !state.analysis?.metadata?.bbox) return;

  const dpr = window.devicePixelRatio || 1;
  const W = 320;
  const H = 145;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, W, H);

  const [minLon, minLat, maxLon, maxLat] = state.analysis.metadata.bbox;
  let ptA, ptB;

  if (state.customTransect && state.customTransect.length === 2) {
    [ptA, ptB] = state.customTransect;
  } else if (state.analysis.targets?.length > 0) {
    const t1 = state.analysis.targets[0];
    const cLat = t1.peak_lat ?? t1.lat;
    const cLon = t1.peak_lon ?? t1.lon;
    const dLon = (maxLon - minLon) * 0.34;
    const dLat = (maxLat - minLat) * 0.16;
    ptA = [cLat - dLat, cLon - dLon];
    ptB = [cLat + dLat, cLon + dLon];
    document.getElementById("profileSourceLbl").textContent = `Auto: Foco ${t1.id || "#1"}`;
  } else {
    const cLat = 0.5 * (minLat + maxLat);
    ptA = [cLat, minLon + 0.12 * (maxLon - minLon)];
    ptB = [cLat, maxLon - 0.12 * (maxLon - minLon)];
    document.getElementById("profileSourceLbl").textContent = "Sección O–E";
  }

  const N = 46;
  const g = pi.grid_size;
  const elevs = [];
  const prosps = [];
  const alters = [];
  const isAlluvial = document.getElementById("inpDepositModel").value === "aluvial_placer";

  for (let i = 0; i < N; i++) {
    const t = i / (N - 1);
    const la = ptA[0] + t * (ptB[0] - ptA[0]);
    const lo = ptA[1] + t * (ptB[1] - ptA[1]);
    const col = Math.min(g - 1, Math.max(0, Math.floor(((lo - minLon) / Math.max(maxLon - minLon, 1e-6)) * g)));
    const row = Math.min(g - 1, Math.max(0, Math.floor(((maxLat - la) / Math.max(maxLat - minLat, 1e-6)) * g)));

    elevs.push(Math.max(0, pi.elevation_m?.[row]?.[col] ?? 1000));
    prosps.push(Math.max(0, pi.prospectivity?.[row]?.[col] ?? 0));
    const altVal = isAlluvial
      ? Math.max(0, pi.alluvial_power?.[row]?.[col] ?? 0)
      : Math.max(0, pi.clay_index?.[row]?.[col] ?? 0);
    alters.push(altVal);
  }

  const eMin = Math.min(...elevs);
  const eMax = Math.max(...elevs, eMin + 12);
  const padL = 32, padR = 28, padT = 16, padB = 20;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  // Área sombreada de Relieve Topográfico (gris pizarra)
  ctx.beginPath();
  elevs.forEach((ev, i) => {
    const x = padL + (i / (N - 1)) * plotW;
    const y = padT + plotH - ((ev - eMin) / (eMax - eMin)) * plotH * 0.86;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.lineTo(padL + plotW, padT + plotH);
  ctx.lineTo(padL, padT + plotH);
  ctx.closePath();
  ctx.fillStyle = "rgba(100, 116, 139, 0.34)";
  ctx.fill();

  // Curva de Alteración / Potencial Aluvial (Cian punteada)
  ctx.beginPath();
  ctx.setLineDash([3, 3]);
  alters.forEach((av, i) => {
    const x = padL + (i / (N - 1)) * plotW;
    const y = padT + plotH - Math.min(1, av) * plotH;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 1.4;
  ctx.stroke();
  ctx.setLineDash([]);

  // Curva Principal de Potencial Aurífero (Oro brillante)
  let peakIdx = 0;
  prosps.forEach((pv, i) => { if (pv > prosps[peakIdx]) peakIdx = i; });

  ctx.beginPath();
  prosps.forEach((pv, i) => {
    const x = padL + (i / (N - 1)) * plotW;
    const y = padT + plotH - Math.min(1, pv) * plotH;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#fde047";
  ctx.lineWidth = 2.3;
  ctx.stroke();

  // Marcador del Pico de Oro sobre la sección A–B
  if (prosps[peakIdx] >= 0.45) {
    const px = padL + (peakIdx / (N - 1)) * plotW;
    const py = padT + plotH - Math.min(1, prosps[peakIdx]) * plotH;
    ctx.beginPath();
    ctx.arc(px, py, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#ef4444";
    ctx.fill();
    ctx.strokeStyle = "#fde047";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  // Etiquetas de ejes
  const distKm = calculateHaversineKm(ptA[0], ptA[1], ptB[0], ptB[1]);
  ctx.fillStyle = "#94a3b8";
  ctx.font = "9.5px JetBrains Mono";
  ctx.fillText(`${Math.round(eMax)}m`, 2, padT + 8);
  ctx.fillText(`${Math.round(eMin)}m`, 2, padT + plotH);
  ctx.fillStyle = "#fde047";
  ctx.fillText("100%", W - 26, padT + 8);
  ctx.fillText("0%", W - 20, padT + plotH);
  ctx.fillStyle = "#cbd5e1";
  ctx.fillText("A", padL, H - 5);
  ctx.fillText(`Sección ${distKm.toFixed(2)} km`, W / 2 - 42, H - 5);
  ctx.fillText("B", padL + plotW - 6, H - 5);
}

/* ============================================================================
   7. Interacción en el Mapa: Rumbo/Azimut, Muestras e Inspector en Vivo
   ============================================================================ */
function calculateBearingAndStrike(lat1, lon1, lat2, lon2) {
  const toRad = (d) => (d * Math.PI) / 180;
  const toDeg = (r) => (r * 180) / Math.PI;
  const dLon = toRad(lon2 - lon1);
  const y = Math.sin(dLon) * Math.cos(toRad(lat2));
  const x =
    Math.cos(toRad(lat1)) * Math.sin(toRad(lat2)) -
    Math.sin(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(dLon);
  const az = (toDeg(Math.atan2(y, x)) + 360) % 360;

  let strike;
  if (az <= 90) strike = `N${az.toFixed(1)}°E`;
  else if (az <= 180) strike = `S${(180 - az).toFixed(1)}°E`;
  else if (az <= 270) strike = `S${(az - 180).toFixed(1)}°W`;
  else strike = `N${(360 - az).toFixed(1)}°W`;

  return { azimuth: az.toFixed(1), strike };
}

function calculateHaversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371.0;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0, 1 - a)));
}

function drawTransectLineOnMap(p1, p2, labelText) {
  measureLayerGroup.clearLayers();
  L.circleMarker(p1, { radius: 5, color: "#fde047", fillColor: "#0b0f17", fillOpacity: 1 })
    .bindTooltip("A", { permanent: true, direction: "left" })
    .addTo(measureLayerGroup);
  L.circleMarker(p2, { radius: 5, color: "#fde047", fillColor: "#ef4444", fillOpacity: 1 })
    .bindTooltip("B", { permanent: true, direction: "right" })
    .addTo(measureLayerGroup);
  L.polyline([p1, p2], { color: "#fde047", weight: 2.8, dashArray: "6,4" })
    .bindTooltip(labelText, { permanent: true, direction: "top" })
    .addTo(measureLayerGroup);
}

function onMapClick(e) {
  const { lat, lng } = e.latlng;

  if (state.measureMode) {
    state.measurePts.push([lat, lng]);
    if (state.measurePts.length === 1) {
      measureLayerGroup.clearLayers();
      L.circleMarker([lat, lng], { radius: 5, color: "#00e5ff", fillOpacity: 1 })
        .bindTooltip("A", { permanent: true })
        .addTo(measureLayerGroup);
      showToast("Punto A fijado. Haga clic en el Punto B para calcular Rumbo y Corte A–B.");
    } else if (state.measurePts.length >= 2) {
      const p1 = state.measurePts[state.measurePts.length - 2];
      const p2 = state.measurePts[state.measurePts.length - 1];
      if (rubberBandLine) {
        map.removeLayer(rubberBandLine);
        rubberBandLine = null;
      }
      const distM = map.distance(p1, p2);
      const distStr = distM >= 1000 ? `${(distM / 1000).toFixed(2)} km` : `${Math.round(distM)} m`;
      const { azimuth, strike } = calculateBearingAndStrike(p1[0], p1[1], p2[0], p2[1]);
      const fullLbl = `${distStr} · Rumbo ${strike} (Az ${azimuth}°)`;

      drawTransectLineOnMap(p1, p2, fullLbl);
      state.customTransect = [p1, p2];
      document.getElementById("profileSourceLbl").textContent = `${distStr} · ${strike}`;
      drawCrossSectionProfile();

      state.measureMode = false;
      state.measurePts = [];
      const btn = document.getElementById("btnMeasureDist");
      btn.classList.remove("btn-primary-outline");
      btn.textContent = "📏 Rumbo / Corte A–B";
      showToast(`Medición lista: ${fullLbl} (Corte A–B actualizado)`);
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
      .bindPopup(`Muestra de Entrenamiento: <b>${cname}</b>`)
      .addTo(samplesLayerGroup);
    return;
  }

  // Clic estándar: mover centro del cuadrante y mostrar vista previa
  document.getElementById("inpLat").value = lat.toFixed(5);
  document.getElementById("inpLon").value = lng.toFixed(5);
  updateDmsTelemetry();
  if (centerCrosshair) centerCrosshair.setLatLng([lat, lng]);
  showToast(`Centro fijado en (${lat.toFixed(4)}, ${lng.toFixed(4)}) — Presione 'Analizar Oro'`);
}

function onMapMouseMove(e) {
  const { lat, lng } = e.latlng;

  // Línea elástica en vivo mientras mide Rumbo A -> B
  if (state.measureMode && state.measurePts.length === 1) {
    const p1 = state.measurePts[0];
    if (!rubberBandLine) {
      rubberBandLine = L.polyline([p1, [lat, lng]], { color: "#00e5ff", weight: 2, dashArray: "4,4" }).addTo(map);
    } else {
      rubberBandLine.setLatLngs([p1, [lat, lng]]);
    }
  }

  if (!state.analysis?.pixel_inspector) return;
  const [minLon, minLat, maxLon, maxLat] = state.analysis.metadata.bbox;
  if (lng < minLon || lng > maxLon || lat < minLat || lat > maxLat) return;

  const pi = state.analysis.pixel_inspector;
  const g = pi.grid_size;
  const col = Math.min(g - 1, Math.max(0, Math.floor(((lng - minLon) / (maxLon - minLon)) * g)));
  const row = Math.min(g - 1, Math.max(0, Math.floor(((maxLat - lat) / (maxLat - minLat)) * g)));

  document.getElementById("hudCoords").textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
  const elevVal = pi.elevation_m?.[row]?.[col] ?? -1;
  document.getElementById("hudElev").textContent = elevVal >= 0 ? `Elev: ${Math.round(elevVal)} msnm` : "Elev: --";

  const pVal = pi.prospectivity?.[row]?.[col] ?? -1;
  const cVal = pi.clay_index?.[row]?.[col] ?? -1;
  const fVal = pi.feox_index?.[row]?.[col] ?? -1;
  const aVal = pi.alluvial_power?.[row]?.[col] ?? 0;
  const nVal = pi.ndvi?.[row]?.[col] ?? -1;

  // Diagnóstico geológico instantáneo bajo el cursor
  const vBadge = document.getElementById("hudVerdictBadge");
  if (pVal >= 0.80) {
    vBadge.className = "verdict-pill core";
    vBadge.textContent = `🔥 NÚCLEO AURÍFERO P1 (${Math.round(pVal * 100)}%)`;
  } else if (aVal >= 0.45) {
    vBadge.className = "verdict-pill alluvial";
    vBadge.textContent = `🌊 TERRAZA / PLACER ALUVIAL (${Math.round(aVal * 100)}%)`;
  } else if (pVal >= 0.58) {
    vBadge.className = "verdict-pill halo";
    vBadge.textContent = `⚡ VETA / HALO HIDROTERMAL (${Math.round(pVal * 100)}%)`;
  } else if (nVal >= 0.48) {
    vBadge.className = "verdict-pill veg";
    vBadge.textContent = `🌿 DOSEL VEGETAL (NDVI ${nVal.toFixed(2)})`;
  } else {
    vBadge.className = "verdict-pill neutral";
    vBadge.textContent = `🪨 ROCA DE CAJA / FONDO (${pVal >= 0 ? Math.round(pVal * 100) + "%" : "--"})`;
  }

  document.getElementById("hudReadout").innerHTML = `
    <span>Oro: <b>${pVal >= 0 ? Math.round(pVal * 100) + "%" : "--"}</b></span>
    <span>Arcilla: <b>${cVal >= 0 ? cVal.toFixed(2) : "Mask"}</b></span>
    <span>FeOx: <b>${fVal >= 0 ? fVal.toFixed(2) : "Mask"}</b></span>
    <span>Aluvial: <b>${aVal > 0.05 ? Math.round(aVal * 100) + "%" : "0%"}</b></span>
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

  const padL = 22, padR = 10, padT = 8, padB = 16;
  ctx.strokeStyle = "rgba(245, 158, 11, 0.18)";
  ctx.beginPath();
  pts.forEach((p, k) => {
    const x = padL + (k / (pts.length - 1)) * (w - padL - padR);
    ctx.moveTo(x, padT);
    ctx.lineTo(x, h - padB);
  });
  ctx.stroke();

  ctx.strokeStyle = "#fde047";
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
    ctx.fillStyle = "#f59e0b";
    ctx.beginPath();
    ctx.arc(x, y, 2.4, 0, Math.PI * 2);
    ctx.fill();

    if (k % 2 === 0 || k === pts.length - 1) {
      ctx.fillStyle = "#94a3b8";
      ctx.font = "8.5px JetBrains Mono";
      ctx.fillText(p.label, x - 9, h - 3);
    }
  });
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
    <div class="mini-stat"><span>Enmascarado</span><strong>${st.nodata_pct}%</strong></div>
  `;

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
    ctx.fillStyle = i >= 18 ? "#ef4444" : "#f59e0b";
    ctx.fillRect(x + 1, y, Math.max(barW - 2, 2), bh);
  });

  ctx.fillStyle = "#94a3b8";
  ctx.font = "10px Inter";
  ctx.fillText("0.0 (Fondo)", pad, h - 4);
  ctx.fillText("0.5", w / 2 - 8, h - 4);
  ctx.fillText("1.0 (Anomalía P98)", w - 102, h - 4);
}

/* ============================================================================
   8. Exportación Directa a Dispositivos GPS de Campo (.GPX y .KML)
   ============================================================================ */
function exportTargetsGpx() {
  const targets = state.analysis?.targets || [];
  if (!targets.length) {
    showToast("No hay focos de oro activos para exportar a GPX.");
    return;
  }
  const roiName = escapeXml(state.analysis.metadata.roi_name || "GeoAuV2");
  const wpts = targets
    .map((t) => {
      const la = t.peak_lat ?? t.lat;
      const lo = t.peak_lon ?? t.lon;
      const pct = Math.round(t.score_max * 100);
      const nm = escapeXml(`${t.id || "AU-" + t.rank} (${pct}% Au - ${t.priority_code})`);
      const desc = escapeXml(`${t.dominant_alteration} | Área: ${t.area_ha} ha | ANM: ${t.legal_state}`);
      return `  <wpt lat="${la}" lon="${lo}">
    <name>${nm}</name>
    <desc>${desc}</desc>
    <sym>Flag, Red</sym>
  </wpt>`;
    })
    .join("\n");

  const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="GeoAuV2 Prospeccion Aurifera" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Focos Auriferos — ${roiName}</name>
    <time>${new Date().toISOString()}</time>
  </metadata>
${wpts}
</gpx>`;

  downloadTextFile(gpx, `focos_oro_${roiName.replace(/\s+/g, "_")}.gpx`, "application/gpx+xml");
  showToast(`Exportados ${targets.length} waypoints .GPX listos para Garmin / GPS móvil`);
}

function exportTargetsKml() {
  const targets = state.analysis?.targets || [];
  if (!targets.length) {
    showToast("No hay focos de oro activos para exportar a KML.");
    return;
  }
  const roiName = escapeXml(state.analysis.metadata.roi_name || "GeoAuV2");
  const placemarks = targets
    .map((t) => {
      const la = t.peak_lat ?? t.lat;
      const lo = t.peak_lon ?? t.lon;
      const pct = Math.round(t.score_max * 100);
      const nm = escapeXml(`${t.id || "AU-" + t.rank} · ${pct}% Au (${t.priority_code})`);
      const desc = escapeXml(
        `Prioridad: ${t.priority} | Dominio: ${t.dominant_alteration} | Área: ${t.area_ha} ha | Catastro ANM: ${t.legal_state}`
      );
      let polyXml = "";
      const geom = t.geometry;
      if (geom?.type === "Polygon" && geom.coordinates?.[0]) {
        const ring = geom.coordinates[0].map((c) => `${c[0]},${c[1]},0`).join(" ");
        polyXml = `
      <Polygon>
        <outerBoundaryIs><LinearRing><coordinates>${ring}</coordinates></LinearRing></outerBoundaryIs>
      </Polygon>`;
      }
      return `    <Placemark>
      <name>${nm}</name>
      <description>${desc}</description>
      <styleUrl>#${t.priority_code === "P1" ? "styleP1" : "styleP2"}</styleUrl>
      <MultiGeometry>
        <Point><coordinates>${lo},${la},0</coordinates></Point>${polyXml}
      </MultiGeometry>
    </Placemark>`;
    })
    .join("\n");

  const kml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>GeoAuV2 — ${roiName}</name>
    <Style id="styleP1">
      <LineStyle><color>ff47e0fd</color><width>2.5</width></LineStyle>
      <PolyStyle><color>55303bff</color></PolyStyle>
    </Style>
    <Style id="styleP2">
      <LineStyle><color>ff0b9ef5</color><width>2.0</width></LineStyle>
      <PolyStyle><color>44129cf3</color></PolyStyle>
    </Style>
${placemarks}
  </Document>
</kml>`;

  downloadTextFile(kml, `focos_oro_${roiName.replace(/\s+/g, "_")}.kml`, "application/vnd.google-earth.kml+xml");
  showToast(`Archivo .KML exportado para Google Earth 3D`);
}

function escapeXml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ============================================================================
   9. Laboratorio de Magnetometría 3D, Scripts GEE y Persistencia Cloud
   ============================================================================ */
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
      <div class="mini-stat"><span>Vacíos Hidro.</span><strong style="color:#38bdf8;">${res.void_zones_count} corredor(es)</strong></div>
    `;
    document.getElementById("magInterpText").textContent = res.interpretation;
    drawMagnetometry3D();

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
      showToast("Malla de magnetometría 3D procesada y proyectada.");
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
    const nx = c / (N - 1) - 0.5;
    const ny = r / (N - 1) - 0.5;
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
    if (q.zAvg <= voidThr) fill = "rgba(14, 165, 233, 0.88)";
    else if (t > 0.72) fill = "rgba(239, 68, 68, 0.85)";
    else if (t > 0.48) fill = "rgba(245, 158, 11, 0.80)";
    else fill = "rgba(52, 211, 153, 0.76)";

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
  ctx.fillText("■ Azul: Vacío Magnético Hidrotermal (Zona Pirita/Cuarzo)", 8, 14);
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
  const name = prompt("Nombre del proyecto exploratorio para guardar en la nube:", state.analysis.metadata.roi_name);
  if (!name) return;
  const cfg = buildAnalysisPayload(name);
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
    showToast("Proyecto guardado en la base de datos Cloud.");
  } else {
    showToast("Aviso al guardar proyecto: verifique conexión.");
  }
}

async function openCloudModal() {
  const modal = document.getElementById("cloudModal");
  const wrap = document.getElementById("cloudRunsTableWrap");
  modal.classList.remove("hidden");
  wrap.innerHTML = "<p>Consultando corridas guardadas...</p>";

  try {
    const [rRuns, rProjs] = await Promise.all([fetch("/api/runs?limit=15"), fetch("/api/projects?limit=10")]);
    const runsData = await rRuns.json();
    const projsData = await rProjs.json();

    const rowsHtml = (runsData.runs || [])
      .map(
        (r) => `<tr style="cursor:pointer;" onclick="loadCloudRun(${r.center_lat}, ${r.center_lon}, '${(r.district_name || "").replace(/'/g, "")}', '${r.deposit_model || "orogenico_vetas"}')">
          <td>${(r.created_at || "").slice(0, 16).replace("T", " ")}</td>
          <td><strong>${r.district_name || r.quadrant_key}</strong></td>
          <td>${r.sensor_mode}</td>
          <td><b>${r.mpi_score}</b> (${r.classification_code})</td>
          <td>${r.targets_count} (${r.p1_targets_count} P1)</td>
          <td>${r.validation_kappa ?? "--"}</td>
        </tr>`
      )
      .join("");

    wrap.innerHTML = `
      <h3 style="margin:6px 0;">Últimas Corridas Analíticas (${runsData.count}) — <small style="color:var(--accent);">Clic en una fila para reabrir zona</small></h3>
      <table class="data-table">
        <thead>
          <tr><th>Fecha UTC</th><th>Zona Explorada</th><th>Sensor</th><th>MPI</th><th>Focos Au</th><th>Kappa</th></tr>
        </thead>
        <tbody>${rowsHtml || "<tr><td colspan='6'>Sin registros aún</td></tr>"}</tbody>
      </table>
      <p class="muted-note" style="margin-top:10px;">Proyectos guardados: <strong>${projsData.count}</strong></p>
    `;
  } catch (err) {
    wrap.innerHTML = `<p>Error consultando historial: ${err.message}</p>`;
  }
}

window.loadCloudRun = function (lat, lon, name, model) {
  document.getElementById("cloudModal").classList.add("hidden");
  jumpToLocation(Number(lat), Number(lon), name || "Zona Recuperada", model || null, true);
};

async function copyToClipboard(text, msg) {
  try {
    await navigator.clipboard.writeText(text);
    showToast(msg || "Copiado al portapapeles");
  } catch (_) {
    showToast("No se pudo copiar automáticamente");
  }
}

function showToast(message) {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.remove();
  }, 3400);
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
