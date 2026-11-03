"""
Generador de Informe Técnico Geocientífico HTML/PDF Imprimible — GeoAuV2
"""
from typing import Any, Dict


def build_standalone_html_report(analysis: Dict[str, Any]) -> str:
    """Genera un informe técnico ejecutivo y de campo listo para imprimir o exportar a PDF."""
    meta = analysis.get("metadata", {})
    prosp = analysis.get("prospectivity_summary", {})
    val = analysis.get("validation", {})
    diag = analysis.get("diagnostics", {})
    sgc = analysis.get("sgc_metrics", {})
    legal = analysis.get("legal_status", {})
    targets = analysis.get("targets", [])
    plan = analysis.get("geoai_plan", {})
    ml_info = analysis.get("ml_summary", {})
    comp = prosp.get("component_scores", {})

    rows_targets = ""
    for t in targets[:18]:
        pk_lat = t.get("peak_lat", t["lat"])
        pk_lon = t.get("peak_lon", t["lon"])
        leg_st = t.get("legal_state", "Área Libre")
        leg_col = "#065f46" if t.get("is_free_area", True) else "#1e40af"
        leg_bg = "#d1fae5" if t.get("is_free_area", True) else "#dbeafe"
        gmaps_url = f"https://www.google.com/maps?q={pk_lat},{pk_lon}"
        rows_targets += (
            f"<tr>"
            f"<td><strong>{t.get('id', '#' + str(t['rank']))}</strong></td>"
            f"<td><strong>{t['priority_code']}</strong> ({t['priority']})</td>"
            f"<td><a href='{gmaps_url}' target='_blank' style='color:#b45309;text-decoration:none;font-weight:600;'>"
            f"{pk_lat:.6f}, {pk_lon:.6f} ↗</a></td>"
            f"<td>{t['area_ha']} ha</td>"
            f"<td><strong>{round(t['score_max'] * 100, 1)}%</strong> ({t['score_max']:.3f})</td>"
            f"<td>{t['dominant_alteration']}</td>"
            f"<td><span style='background:{leg_bg};color:{leg_col};padding:2px 7px;border-radius:99px;font-size:11px;font-weight:700;'>{leg_st}</span></td>"
            f"</tr>"
        )
    if not rows_targets:
        rows_targets = "<tr><td colspan='7'>Sin focos auríferos sobre el umbral configurado (zona estéril o control negativo).</td></tr>"

    rows_clusters = ""
    for c in ml_info.get("clusters", []):
        rows_clusters += (
            f"<tr><td>Dominio {c['cluster_id']}</td><td>{c['geological_zone']}</td>"
            f"<td>{c['area_pct']}%</td><td>{c.get('confidence', 'Media')}</td></tr>"
        )

    phases_html = ""
    for ph in plan.get("phases", []):
        items = "".join(f"<li>{act}</li>" for act in ph.get("actions", []))
        phases_html += f"<div class='phase'><h4>{ph['phase']}</h4><ul>{items}</ul></div>"

    cm = val.get("confusion_matrix", {})
    logs_html = "".join(f"<li>{lg}</li>" for lg in diag.get("cascade_logs", []))

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Informe Técnico GeoAuV2 — {meta.get('roi_name', 'Cuadrante')}</title>
<style>
  body {{ font-family: 'Segoe UI', Inter, Roboto, Arial, sans-serif; color: #1c2430; margin: 30px; line-height: 1.5; }}
  header {{ border-bottom: 3px solid #f59e0b; padding-bottom: 14px; margin-bottom: 22px; display: flex; justify-content: space-between; align-items: flex-end; }}
  h1 {{ margin: 0; font-size: 23px; color: #0f172a; }}
  h2 {{ font-size: 16px; color: #b45309; border-left: 4px solid #f59e0b; padding-left: 10px; margin-top: 24px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0; }}
  .kpi {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }}
  .kpi .lbl {{ font-size: 11px; text-transform: uppercase; color: #64748b; letter-spacing: 0.04em; }}
  .kpi .val {{ font-size: 21px; font-weight: 800; color: #0f172a; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12.5px; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 7px 9px; text-align: left; }}
  th {{ background: #0f172a; color: #f8fafc; }}
  .phase {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; }}
  .phase h4 {{ margin: 0 0 6px 0; color: #92400e; }}
  @media print {{ .no-print {{ display: none; }} body {{ margin: 10mm; }} }}
</style>
</head>
<body>
<div class="no-print" style="margin-bottom:16px;text-align:right;">
  <button onclick="window.print()" style="background:#f59e0b;color:#111;border:none;padding:9px 18px;border-radius:6px;font-weight:700;cursor:pointer;">🖨️ Imprimir / Guardar Informe PDF</button>
</div>
<header>
  <div>
    <h1>GeoAuV2 — Informe Técnico de Prospección Aurífera Multisensor</h1>
    <div style="font-size:13px;color:#475569;">Zona: <strong>{meta.get('roi_name')}</strong> · Centro GPS: ({meta.get('center_lat')}, {meta.get('center_lon')}) · Cuadrante: {meta.get('roi_size_km')}×{meta.get('roi_size_km')} km</div>
  </div>
  <div style="text-align:right;font-size:12px;color:#64748b;">
    Fecha UTC: {meta.get('timestamp', '')[:19]}<br>
    Mosaico Base: <strong>{diag.get('optical_source', 'Multisensor Sin Nubes')}</strong>
  </div>
</header>

<div class="kpi-grid">
  <div class="kpi"><div class="lbl">Índice MPI Aurífero</div><div class="val">{prosp.get('mpi', 0)} / 100 ({prosp.get('classification_code', 'Q3')})</div></div>
  <div class="kpi"><div class="lbl">Focos de Oro Detectados</div><div class="val">{len(targets)} (P1: {sum(1 for t in targets if t['priority_code']=='P1')})</div></div>
  <div class="kpi"><div class="lbl">Validación Kappa / OA</div><div class="val">{val.get('kappa', 0)} ({round(val.get('overall_accuracy', 0)*100, 1)}%)</div></div>
  <div class="kpi"><div class="lbl">Ganancia Espacial</div><div class="val">{val.get('spatial_gain', 0)}×</div></div>
</div>

<p style="font-size:13px;background:#f1f5f9;padding:10px 14px;border-radius:8px;">
  <strong>Desglose de los 4 Pilares Geocientíficos:</strong>
  Espectral Hidrotermal/Aluvial: <strong>{comp.get('spectral', 0)}%</strong> ·
  Control Estructural DEM: <strong>{comp.get('structural', 0)}%</strong> ·
  Geología y Metalogenia SGC: <strong>{comp.get('geological_sgc', 0)}%</strong> ·
  Respuesta Geofísica: <strong>{comp.get('geophysical', 0)}%</strong>
</p>

<h2>1. Síntesis Ejecutiva y Trazabilidad Multisensor</h2>
<p>{plan.get('executive_narrative', '')}</p>
<ul>{logs_html}</ul>

<h2>2. Blancos y Focos Auríferos Priorizados para Verificación en Campo</h2>
<table>
  <thead><tr><th>ID</th><th>Prioridad</th><th>Coordenada Foco Pico (WGS84)</th><th>Área</th><th>Potencial Pico</th><th>Dominio Mineralógico</th><th>Estado Catastral ANM</th></tr></thead>
  <tbody>{rows_targets}</tbody>
</table>

<h2>3. Dominios de Alteración Clasificados por IA ({ml_info.get('method', 'K-Means++')})</h2>
<table>
  <thead><tr><th>ID</th><th>Dominio Mineralógico / Cobertura</th><th>Área (%)</th><th>Confianza</th></tr></thead>
  <tbody>{rows_clusters}</tbody>
</table>

<h2>4. Validación Estadística Espacial (UTM EPSG:{val.get('utm_epsg')} · Buffer {val.get('buffer_m')} m)</h2>
<p><strong>Escala Landis & Koch (1977):</strong> {val.get('kappa_interpretation')} ·
Matriz de Confusión: TP={cm.get('tp', 0)}, FP={cm.get('fp', 0)}, FN={cm.get('fn', 0)}, TN={cm.get('tn', 0)} ·
F1-Score: {val.get('f1_score', 0)}</p>

<h2>5. Contexto Geológico Oficial (SGC) y Catastro Minero (ANM)</h2>
<p><strong>Servicio Geológico Colombiano (SGC):</strong> {sgc.get('fault_count', 0)} fallas cartografiadas (más cercana a {sgc.get('nearest_fault_km', 'N/A')} km),
{sgc.get('deposit_count', 0)} ocurrencias/yacimientos ({sgc.get('nearest_deposit_name') or 'Sin registro puntual en SGC'}),
Tipología: {sgc.get('deposit_type_detected', 'N/A')}.<br>
<strong>Agencia Nacional de Minería (ANM):</strong> {legal.get('status_summary', 'Consulta regional completada')}.</p>

<h2>6. Plan Operativo de Exploración Recomendado por Fases</h2>
{phases_html}
</body>
</html>"""
