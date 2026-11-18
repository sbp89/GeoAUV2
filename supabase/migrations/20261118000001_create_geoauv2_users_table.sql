-- Migración: Tabla de Usuarios y Control de Acceso GeoAuV2
CREATE TABLE IF NOT EXISTS public.geoauv2_users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username text UNIQUE NOT NULL,
    username_lower text UNIQUE NOT NULL,
    password_hash text NOT NULL,
    full_name text NOT NULL DEFAULT '',
    role text NOT NULL DEFAULT 'admin',
    created_by text NOT NULL DEFAULT 'Momentum',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_geoauv2_users_username_lower ON public.geoauv2_users (username_lower);

ALTER TABLE public.geoauv2_users ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.geoauv2_users TO anon, authenticated;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'geoauv2_users' AND policyname = 'geoauv2_users_select') THEN
        CREATE POLICY geoauv2_users_select ON public.geoauv2_users FOR SELECT TO anon, authenticated USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'geoauv2_users' AND policyname = 'geoauv2_users_insert') THEN
        CREATE POLICY geoauv2_users_insert ON public.geoauv2_users FOR INSERT TO anon, authenticated WITH CHECK (char_length(username) BETWEEN 3 AND 60 AND char_length(password_hash) >= 20);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'geoauv2_users' AND policyname = 'geoauv2_users_update') THEN
        CREATE POLICY geoauv2_users_update ON public.geoauv2_users FOR UPDATE TO anon, authenticated USING (char_length(username) BETWEEN 3 AND 60) WITH CHECK (char_length(username) BETWEEN 3 AND 60 AND char_length(password_hash) >= 20);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'geoauv2_users' AND policyname = 'geoauv2_users_delete') THEN
        CREATE POLICY geoauv2_users_delete ON public.geoauv2_users FOR DELETE TO anon, authenticated USING (username_lower <> 'momentum');
    END IF;
END $$;
