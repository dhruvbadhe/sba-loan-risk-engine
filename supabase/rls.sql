-- Run as the database owner in the Supabase SQL editor.
-- Backend-only tables: this replaces ALL existing policies on these two tables.
-- service_role is used by backend secret keys and bypasses RLS in Supabase.
BEGIN;

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    existing_policy record;
    table_name text;
    column_names text;
BEGIN
    FOR existing_policy IN
        SELECT tablename, policyname FROM pg_policies
        WHERE schemaname = 'public' AND tablename IN ('users', 'predictions')
    LOOP
        EXECUTE format('DROP POLICY %I ON public.%I',
                       existing_policy.policyname, existing_policy.tablename);
    END LOOP;

    FOREACH table_name IN ARRAY ARRAY['users', 'predictions'] LOOP
        -- Table REVOKE alone does not remove previously granted column access.
        SELECT string_agg(format('%I', attname), ', ') INTO column_names
        FROM pg_attribute
        WHERE attrelid = format('public.%I', table_name)::regclass
          AND attnum > 0 AND NOT attisdropped;
        EXECUTE format(
            'REVOKE SELECT (%s), INSERT (%s), UPDATE (%s), REFERENCES (%s) '
            'ON public.%I FROM PUBLIC, anon, authenticated',
            column_names, column_names, column_names, column_names, table_name);
    END LOOP;
END $$;

REVOKE ALL PRIVILEGES ON TABLE public.users, public.predictions
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.users, public.predictions TO service_role;

CREATE POLICY backend_only ON public.users
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY backend_only ON public.predictions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Support generated integer IDs without granting access to unrelated sequences.
DO $$
DECLARE
    sequence_name text;
BEGIN
    FOR sequence_name IN
        SELECT pg_get_serial_sequence(format('public.%I', c.relname), a.attname)
        FROM pg_class c JOIN pg_attribute a ON a.attrelid = c.oid
        WHERE c.oid IN ('public.users'::regclass, 'public.predictions'::regclass)
          AND a.attnum > 0 AND NOT a.attisdropped
    LOOP
        IF sequence_name IS NOT NULL THEN
            EXECUTE format('GRANT USAGE, SELECT ON SEQUENCE %s TO service_role',
                           sequence_name);
        END IF;
    END LOOP;
END $$;

COMMIT;
