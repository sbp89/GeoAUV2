-- ============================================================================
-- GeoAuV2 - Esquema PostgreSQL de Prospección Aurífera + RLS Seguro
-- Proyecto Supabase: srigpcynpkybntclrume
-- Motor Multisensor, IA Espectral, Catastro Minero y Geofísica 3D
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.geoauv2_projects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text UNIQUE,
    name text NOT NULL,
    district_code text,
    sensor_mode text NOT NULL DEFAULT 'multisensor',
    deposit_model text NOT NULL DEFAULT 'epitermal_as',
    center_lat double precision NOT NULL,
    center_lon double precision NOT NULL,
    roi_size_km double precision NOT NULL DEFAULT 4.0,
    bbox jsonb NOT NULL DEFAULT '[]'::jsonb,
    config_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.geoauv2_analysis_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid REFERENCES public.geoauv2_projects(id) ON DELETE SET NULL,
    quadrant_key text NOT NULL,
    district_name text,
    sensor_mode text NOT NULL,
    deposit_model text NOT NULL,
    ml_method text NOT NULL DEFAULT 'kmeans',
    center_lat double precision NOT NULL,
    center_lon double precision NOT NULL,
    roi_size_km double precision NOT NULL,
    mpi_score numeric(6,2) NOT NULL,
    favorability_mean numeric(6,4) NOT NULL DEFAULT 0,
    prospectivity_mean numeric(6,4) NOT NULL DEFAULT 0,
    classification_code text NOT NULL,
    targets_count integer NOT NULL DEFAULT 0,
    p1_targets_count integer NOT NULL DEFAULT 0,
    validation_oa numeric(6,4),
    validation_kappa numeric(6,4),
    spatial_gain numeric(8,3),
    cascade_level integer NOT NULL DEFAULT 0,
    aster_swir_available boolean NOT NULL DEFAULT false,
    summary_metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.geoauv2_targets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL REFERENCES public.geoauv2_analysis_runs(id) ON DELETE CASCADE,
    target_rank integer NOT NULL,
    priority text NOT NULL,
    priority_code text NOT NULL,
    area_ha numeric(10,2) NOT NULL,
    score_max numeric(6,4) NOT NULL,
    score_mean numeric(6,4) NOT NULL,
    dominant_alteration text,
    lat double precision NOT NULL,
    lon double precision NOT NULL,
    geom_geojson jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.geoauv2_training_samples (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid REFERENCES public.geoauv2_projects(id) ON DELETE CASCADE,
    region_code text NOT NULL DEFAULT 'global',
    class_id integer NOT NULL,
    class_name text NOT NULL,
    class_color text NOT NULL DEFAULT '#f39c12',
    lat double precision NOT NULL,
    lon double precision NOT NULL,
    spectral_signature jsonb NOT NULL DEFAULT '{}'::jsonb,
    source text NOT NULL DEFAULT 'user',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.geoauv2_magnetometry_surveys (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_name text NOT NULL,
    district_name text,
    regional_baseline_ut numeric(8,3) NOT NULL,
    min_b_ut numeric(8,3) NOT NULL,
    max_b_ut numeric(8,3) NOT NULL,
    void_zones_count integer NOT NULL DEFAULT 0,
    points_count integer NOT NULL DEFAULT 0,
    points_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    interpretation text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.geoauv2_mineral_deposits (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code text UNIQUE NOT NULL,
    name text NOT NULL,
    country text NOT NULL DEFAULT 'Colombia',
    department_or_region text,
    municipality text,
    deposit_type text NOT NULL,
    primary_mineral text NOT NULL DEFAULT 'Au',
    alteration_style text,
    host_rock text,
    metallogenic_belt text,
    grade_gt numeric(8,2),
    lat double precision NOT NULL,
    lon double precision NOT NULL,
    source text NOT NULL DEFAULT 'SGC / Catálogo GeoAuV2',
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.geoauv2_mining_cadastre (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    expediente text UNIQUE NOT NULL,
    record_type text NOT NULL DEFAULT 'titulo',
    titular text,
    estado text,
    etapa text,
    minerales text,
    area_ha numeric(12,2),
    departamento text,
    municipio text,
    min_lon double precision,
    min_lat double precision,
    max_lon double precision,
    max_lat double precision,
    geom_geojson jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.geoauv2_sync_logs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source text NOT NULL,
    records_synced integer NOT NULL DEFAULT 0,
    status text NOT NULL,
    details text,
    executed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_geoauv2_runs_project_id ON public.geoauv2_analysis_runs (project_id);
CREATE INDEX IF NOT EXISTS idx_geoauv2_runs_quadrant ON public.geoauv2_analysis_runs (quadrant_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_geoauv2_targets_run_id ON public.geoauv2_targets (run_id);
CREATE INDEX IF NOT EXISTS idx_geoauv2_samples_project_id ON public.geoauv2_training_samples (project_id);
CREATE INDEX IF NOT EXISTS idx_geoauv2_samples_region ON public.geoauv2_training_samples (region_code);
CREATE INDEX IF NOT EXISTS idx_geoauv2_deposits_coords ON public.geoauv2_mineral_deposits (lat, lon);
CREATE INDEX IF NOT EXISTS idx_geoauv2_cadastre_bbox ON public.geoauv2_mining_cadastre (min_lat, max_lat, min_lon, max_lon);

ALTER TABLE public.geoauv2_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geoauv2_analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geoauv2_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geoauv2_training_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geoauv2_magnetometry_surveys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geoauv2_mineral_deposits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geoauv2_mining_cadastre ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.geoauv2_sync_logs ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT ON public.geoauv2_projects TO anon, authenticated;
GRANT SELECT, INSERT ON public.geoauv2_analysis_runs TO anon, authenticated;
GRANT SELECT, INSERT ON public.geoauv2_targets TO anon, authenticated;
GRANT SELECT, INSERT ON public.geoauv2_training_samples TO anon, authenticated;
GRANT SELECT, INSERT ON public.geoauv2_magnetometry_surveys TO anon, authenticated;
GRANT SELECT ON public.geoauv2_mineral_deposits TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.geoauv2_mining_cadastre TO anon, authenticated;
GRANT SELECT, INSERT ON public.geoauv2_sync_logs TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.geoauv2_sync_logs_id_seq TO anon, authenticated;

CREATE POLICY geoauv2_projects_select ON public.geoauv2_projects FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY geoauv2_runs_select ON public.geoauv2_analysis_runs FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY geoauv2_targets_select ON public.geoauv2_targets FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY geoauv2_samples_select ON public.geoauv2_training_samples FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY geoauv2_mag_select ON public.geoauv2_magnetometry_surveys FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY geoauv2_deposits_select ON public.geoauv2_mineral_deposits FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY geoauv2_cadastre_select ON public.geoauv2_mining_cadastre FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY geoauv2_sync_logs_select ON public.geoauv2_sync_logs FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY geoauv2_projects_insert ON public.geoauv2_projects
    FOR INSERT TO anon, authenticated
    WITH CHECK (char_length(name) BETWEEN 1 AND 200 AND center_lat BETWEEN -90.0 AND 90.0 AND center_lon BETWEEN -180.0 AND 180.0 AND roi_size_km BETWEEN 0.1 AND 100.0);

CREATE POLICY geoauv2_runs_insert ON public.geoauv2_analysis_runs
    FOR INSERT TO anon, authenticated
    WITH CHECK (char_length(quadrant_key) BETWEEN 3 AND 160 AND mpi_score BETWEEN 0.0 AND 100.0 AND center_lat BETWEEN -90.0 AND 90.0 AND center_lon BETWEEN -180.0 AND 180.0);

CREATE POLICY geoauv2_targets_insert ON public.geoauv2_targets
    FOR INSERT TO anon, authenticated
    WITH CHECK (priority_code IN ('P1', 'P2', 'P3') AND area_ha >= 0.0 AND score_max BETWEEN 0.0 AND 1.0 AND lat BETWEEN -90.0 AND 90.0 AND lon BETWEEN -180.0 AND 180.0);

CREATE POLICY geoauv2_samples_insert ON public.geoauv2_training_samples
    FOR INSERT TO anon, authenticated
    WITH CHECK (class_id BETWEEN 1 AND 50 AND char_length(class_name) BETWEEN 1 AND 120 AND lat BETWEEN -90.0 AND 90.0 AND lon BETWEEN -180.0 AND 180.0);

CREATE POLICY geoauv2_mag_insert ON public.geoauv2_magnetometry_surveys
    FOR INSERT TO anon, authenticated
    WITH CHECK (char_length(survey_name) BETWEEN 1 AND 200 AND points_count BETWEEN 1 AND 10000);

CREATE POLICY geoauv2_cadastre_insert ON public.geoauv2_mining_cadastre
    FOR INSERT TO anon, authenticated
    WITH CHECK (char_length(expediente) BETWEEN 1 AND 100 AND record_type IN ('titulo', 'solicitud'));

CREATE POLICY geoauv2_cadastre_update ON public.geoauv2_mining_cadastre
    FOR UPDATE TO anon, authenticated
    USING (char_length(expediente) BETWEEN 1 AND 100)
    WITH CHECK (char_length(expediente) BETWEEN 1 AND 100 AND record_type IN ('titulo', 'solicitud'));

CREATE POLICY geoauv2_sync_logs_insert ON public.geoauv2_sync_logs
    FOR INSERT TO anon, authenticated
    WITH CHECK (char_length(source) BETWEEN 1 AND 100 AND records_synced >= 0);
