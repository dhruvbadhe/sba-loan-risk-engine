-- Disposable PostgreSQL database ONLY. Never run this fixture in Supabase.
\set ON_ERROR_STOP on
CREATE ROLE anon;
CREATE ROLE authenticated;
CREATE ROLE service_role BYPASSRLS;
CREATE TABLE public.users (id bigserial PRIMARY KEY, username text, password_hash text);
CREATE TABLE public.predictions (id bigserial PRIMARY KEY, username text);
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON public.users, public.predictions TO PUBLIC, anon, authenticated;
GRANT SELECT (username) ON public.users TO anon, authenticated;
CREATE POLICY old_public_policy ON public.users FOR ALL TO PUBLIC USING (true);
CREATE POLICY old_public_policy ON public.predictions FOR ALL TO PUBLIC USING (true);

\ir ../rls.sql
-- Prove the migration is safe to rerun.
\ir ../rls.sql

DO $$
DECLARE
    table_name text;
    role_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['users', 'predictions'] LOOP
        IF NOT (SELECT relrowsecurity FROM pg_class
                WHERE oid = format('public.%I', table_name)::regclass) THEN
            RAISE EXCEPTION 'RLS is disabled on %', table_name;
        END IF;
        IF (SELECT count(*) FROM pg_policies WHERE schemaname = 'public'
            AND tablename = table_name AND roles = ARRAY['service_role']::name[]
            AND policyname = 'backend_only') <> 1 THEN
            RAISE EXCEPTION 'Missing backend-only policy on %', table_name;
        END IF;
        FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF has_table_privilege(role_name, 'public.' || table_name, 'SELECT,INSERT,UPDATE,DELETE')
               OR has_any_column_privilege(role_name, 'public.' || table_name, 'SELECT,INSERT,UPDATE') THEN
                RAISE EXCEPTION 'Browser role % retains access to %', role_name, table_name;
            END IF;
        END LOOP;
    END LOOP;
END $$;

SET ROLE service_role;
INSERT INTO public.users (username, password_hash) VALUES ('test-user', 'test-hash') RETURNING id;
INSERT INTO public.predictions (username) VALUES ('test-user') RETURNING id;
SELECT username FROM public.users;
SELECT username FROM public.predictions;
RESET ROLE;

DO $$
BEGIN
    BEGIN
        SET LOCAL ROLE anon;
        PERFORM username FROM public.users;
        RAISE EXCEPTION 'Anonymous users unexpectedly have access';
    EXCEPTION WHEN insufficient_privilege THEN
        RESET ROLE;
    END;
    BEGIN
        SET LOCAL ROLE authenticated;
        INSERT INTO public.predictions (username) VALUES ('blocked');
        RAISE EXCEPTION 'Authenticated browser users unexpectedly have access';
    EXCEPTION WHEN insufficient_privilege THEN
        RESET ROLE;
    END;
END $$;
SELECT 'RLS checks passed' AS result;
