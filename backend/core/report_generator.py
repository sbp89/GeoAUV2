"""
Generador de Reporte Técnico HTML/PDF Autónomo — GeoAUV2 (Paso 9)
"""
from typing import Any, Dict


def build_standalone_html_report(analysis: Dict[str, Any]) -> str:
    """Genera un informe técnico profesional listo para imprimir o exportar a PDF desde el navegador."""
    meta = analysis.get("metadata", {})
    prosp = analysis.get("prospectivity_summary", {})
    val = analysis.get("validation", {})
    diag = analysis.get("diagnostics", {})
    sgc = analysis.get("sgc_metrics", {})
    legal = analysis.get("legal_status", {})
    targets = analysis.get("targets", [])
    plan = analysis.get("geoai_plan", {})
    ml_info = analysis.get("ml_summary", {})

    rows_targets = ""
    for t in targets[:15]:
        rows_targets += (
            f"<tr><td>#{t['rank']}</td><td><strong>{t['priority_code']}</strong> ({t['priority']})</td>"
            f"<td>{t['lat']:.5f}, {t['lon']:.5f}</td><td>{t['area_ha']} ha</td>"
            f"<td>{t['score_max']:.3f}</td><td>{t['score_mean']:.3f}</td>"
            f"<td>{t['dominant_alteration']}</td></tr>"
        )
    if not rows_targets:
        rows_targets = "<tr><td colspan='7'>Sin polígonos sobre el umbral configurado (control negativo o fondo litológico).</td></tr>"

    rows_clusters = ""
    for c in ml_info.get("clusters", []):
        rows_clusters += (
            f"<tr><td>Clase {c['cluster_id']}</td><td>{c['geological_zone']}</td>"
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
<title>Reporte Técnico Exploratorio GeoAUV2 — {meta.get('roi_name', 'Cuadrante')}</title>
<style>
  body {{ font-family: 'Segoe UI', Roboto, Arial, sans-serif; color: #1c2430; margin: 32px; line-height: 1.5; }}
  header {{ border-bottom: 3px solid #f39c12; padding-bottom: 14px; margin-bottom: 22px; display: flex; justify-content: space-between; align-items: flex-end; }}
  h1 {{ margin: 0; font-size: 24px; color: #111827; }}
  h2 {{ font-size: 17px; color: #b9770e; border-left: 4px solid #f39c12; padding-left: 10px; margin-top: 26px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0; }}
  .kpi {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }}
  .kpi .lbl {{ font-size: 11px; text-transform: uppercase; color: #64748b; }}
  .kpi .val {{ font-size: 22px; font-weight: 700; color: #0f172a; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 7px 9px; text-align: left; }}
  th {{ background: #1e2229; color: #f8fafc; }}
  .phase {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; }}
  .phase h4 {{ margin: 0 0 6px 0; color: #92400e; }}
  @media print {{ .no-print {{ display: none; }} body {{ margin: 12mm; }} }}
</style>
</head>
<body>
<div class="no-print" style="margin-bottom:16px;text-align:right;">
  <button onclick="window.print()" style="background:#f39c12;color:#111;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer;">Imprimir / Guardar como PDF</button>
</div>
<header>
  <div>
    <h1>GeoAUV2 — Informe Geocientífico de Exploración Mineral Multisensor</h1>
    <div style="font-size:13px;color:#475569;">Arquitectura GeoMineral AI v2 · Centro: ({meta.get('center_lat')}, {meta.get('center_lon')}) · Área: {meta.get('roi_size_km')}×{meta.get('roi_size_km')} km</div>
  </div>
  <div style="text-align:right;font-size:12px;color:#64748b;">
    Fecha UTC: {meta.get('timestamp', '')[:19]}<br>
    Modo Sensor: <strong>{diag.get('sensor_mode', 'multisensor').upper()}</strong>
  </div>
</header>

<div class="kpi-grid">
  <div class="kpi"><div class="lbl">Índice MPI Global</div><div class="val">{prosp.get('mpi', 0)} / 100 ({prosp.get('classification_code', 'Q3')})</div></div>
  <div class="kpi"><div class="lbl">Targets Delineados</div><div class="val">{len(targets)} (P1: {sum(1 for t in targets if t['priority_code']=='P1')})</div></div>
  <div class="kpi"><div class="lbl">Índice Kappa Validación</div><div class="val">{val.get('kappa', 0)} (OA {round(val.get('overall_accuracy', 0)*100, 1)}%)</div></div>
  <div class="kpi"><div class="lbl">Ganancia Espacial</div><div class="val">{val.get('spatial_gain', 0)}×</div></div>
</div>

<h2>1. Resumen Ejecutivo y Diagnóstico Multisensor en Cascada</h2>
<p>{plan.get('executive_narrative', '')}</p>
<ul>{logs_html}</ul>

<h2>2. Clasificación IA ({ml_info.get('method', 'K-Means++')})</h2>
<table>
  <thead><tr><th>ID</th><th>Dominio de Alteración / Cobertura</th><th>Área (%)</th><th>Confianza</th></tr></thead>
  <tbody>{rows_clusters}</tbody>
</table>

<h2>3. Targets de Exploración Priorizados (Paso 7)</h2>
<table>
  <thead><tr><th>Rank</th><th>Prioridad</th><th>Centroide (Lat, Lon)</th><th>Área</th><th>Score Máx</th><th>Score Medio</th><th>Alteración Dominante</th></tr></thead>
  <tbody>{rows_targets}</tbody>
</table>

<h2>4. Validación Estadística Espacial (UTM EPSG:{val.get('utm_epsg')} · Buffer {val.get('buffer_m')} m)</h2>
<p><strong>Escala Landis & Koch (1977):</strong> {val.get('kappa_interpretation')} ·
Matriz de Confusión: TP={cm.get('tp', 0)}, FP={cm.get('fp', 0)}, FN={cm.get('fn', 0)}, TN={cm.get('tn', 0)} ·
F1-Score: {val.get('f1_score', 0)}</p>

<h2>5. Contexto Geológico Oficial (SGC) y Estado Jurídico (ANM)</h2>
<p><strong>SGC:</strong> {sgc.get('fault_count', 0)} fallas cartografiadas (más cercana a {sgc.get('nearest_fault_km', 'N/A')} km),
{sgc.get('deposit_count', 0)} depósitos registrados ({sgc.get('nearest_deposit_name') or 'Sin registro local'}),
Tipología: {sgc.get('deposit_type_detected', 'N/A')}.<br>
<strong>Catastro Minero ANM:</strong> {legal.get('status_summary', 'Consulta regional completada')}.</p>

<h2>6. Plan de Exploración Recomendado por Fases (Asesor GeoAI)</h2>
{phases_html}
</body>
</html>"""
