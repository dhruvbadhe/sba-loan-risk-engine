# Supabase security: owner actions

These steps must be performed by the project owner. No hosted database or
dashboard changes are made by this PR. The previously committed key remains in
Git history and **must be replaced and revoked**; removing it from `render.yaml`
does not revoke it. Do not rewrite Git history or paste credentials into Git,
issues, screenshots, or chat.

## 1. Create a backend key and update Render

1. Open the Supabase dashboard and select this project's Supabase project.
2. Click **Project Settings** (gear), then **API Keys**.
3. Open **Publishable and secret API keys**. In **Secret keys**, click
   **Create new secret key**, name it `render-backend`, and create it.
4. Copy the new `sb_secret_...` value into your password manager. This is a
   server-only credential; never use it in Streamlit/browser code. A publishable
   `sb_publishable_...` key cannot access these backend-only tables after RLS.
5. Open Render, select **sba-loan-risk-api**, and click **Environment**.
6. Click **Edit**, find `SUPABASE_KEY`, and replace its value with the new secret
   key. Leave `SUPABASE_URL` pointing at the same Supabase project.
7. Click **Save, rebuild, and deploy** (or **Save, restart, and deploy**, if
   offered). Wait for the deployment to be **Live**.
8. Open `/health` and confirm `{"status":"healthy","version":"1.0.0"}`.
   Use an existing test account to log in through `/docs`. Confirm login works.
   Do not revoke the old key until the new backend key works.

The Blueprint now uses `sync: false`: set this value manually for an existing
service and provide it when creating a new service from the Blueprint.

## 2. Apply backend-only access rules

1. In the same Supabase project, click **SQL Editor** in the left sidebar.
2. Click **New query**. Copy the complete contents of
   [supabase/rls.sql](../supabase/rls.sql) into the editor.
3. Check the project name and confirm `public.users` and `public.predictions`
   already exist. This script does not create or delete tables or data.
4. Run as the database owner (`postgres`) and click **Run**. Confirm success.
   The script runs in a transaction and can be rerun.
5. Click **Table Editor**, open each table, and check that RLS is enabled.
   Its only policy should be `backend_only`, targeting `service_role`.
6. In SQL Editor, run this verification query. Both rows must show `true`:

   ```sql
   SELECT relname, relrowsecurity
   FROM pg_class
   WHERE oid IN ('public.users'::regclass, 'public.predictions'::regclass);
   ```

7. Run the following. Both `can_select` and `can_insert` must be `false` for
   every row:

   ```sql
   SELECT role_name, table_name,
          has_table_privilege(role_name, 'public.' || table_name, 'SELECT') AS can_select,
          has_table_privilege(role_name, 'public.' || table_name, 'INSERT') AS can_insert
   FROM (VALUES ('anon'), ('authenticated')) r(role_name)
   CROSS JOIN (VALUES ('users'), ('predictions')) t(table_name);
   ```

8. Test signup/login and an authenticated prediction through the API. Confirm a
   corresponding prediction appears in Table Editor. If something fails, keep
   RLS enabled and check the backend key/project and API logs.

This intentionally replaces all existing policies on these two tables and
revokes public, anonymous, and Supabase-authenticated table/column grants.
Choose this backend-only design because this application authenticates users
itself and never queries these tables from a browser. Other applications using
direct table access will lose access; migrate them first.

Supabase's `service_role` has `BYPASSRLS`; the named policies document backend
access, while RLS and revoked grants deny browser roles. Database owners and
administrators retain maintenance access. A stolen backend secret can bypass
RLS, which is why it belongs only in Render's environment. This script does not
audit unrelated views, security-definer functions, tables, or custom roles.

## 3. Revoke the old key

1. Return to **Project Settings → API Keys → Publishable and secret API keys**.
2. Find the old committed publishable key (compare privately with your prior
   configuration). Replace it in any other applications that still need it.
3. Open its action menu and click **Delete** or **Revoke**, then confirm.
   Revoke any superseded secret keys as well. Never delete the new Render key.
4. Recheck API login and prediction. Confirm requests with the retired key are
   rejected; do not put that key in a terminal command saved in shell history.

If the old credential is instead a legacy `anon`/`service_role` JWT key, migrate
all consumers to new publishable/secret keys first. Open the **Legacy API Keys**
tab and disable legacy keys after the migration. If that control is unavailable,
follow Supabase's legacy JWT-secret rotation workflow; it can invalidate
sessions and other consumers. Do not rotate unrelated JWT signing settings just
to replace a new-style publishable key.

Official references: [API keys](https://supabase.com/docs/guides/getting-started/api-keys),
[RLS and backend bypass](https://supabase.com/docs/guides/database/postgres/row-level-security),
[legacy signing-key migration](https://supabase.com/docs/guides/auth/signing-keys).
