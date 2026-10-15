# S3: Confirm production secrets on Render

S3 is complete only after its local startup tests pass and the deployed service's
environment variables are confirmed. Do not paste secret values into chat,
screenshots, Git, or this document.

1. Open [Render Dashboard](https://dashboard.render.com/) and select the
   **sba-loan-risk-api** web service.
2. Click **Environment** in the left pane.
3. Under **Environment Variables**, check the following entries. Use **Edit** for
   existing entries, or **+ Add Environment Variable** for missing ones.

   | Key | Required value |
   | --- | --- |
   | `ENV` | `production` |
   | `DEBUG` | `false` |
   | `API_KEY` | A private random value, not blank or `dev-key-change-in-production` |
   | `JWT_SECRET_KEY` | A separate private random value, not blank or `super-secret-key-change-for-production` |

   The repository's Blueprint already requests generated values for both secrets.
   Keep existing private generated values if they meet these checks. If a value
   is missing or is a public default, generate a separate random value of at least
   32 characters for each using your password manager and enter it directly into
   Render. The test placeholders in the repository are not production secrets.
4. If you changed a value, select **Save and deploy** from the save dropdown.
   **Save only** does not apply new values to the running service. Changing the
   API key requires API-key clients to use the new value; changing the JWT secret
   requires users to sign in again.
5. Wait for the deploy to succeed and open
   [the health endpoint](https://sba-loan-risk-api.onrender.com/health). Confirm
   that it returns `{"status":"healthy","version":"1.0.0"}`. If deployment
   fails, report the error with any credentials redacted.
6. Reply **Render confirmed** after verifying all four entries and a healthy
   deployed service. Confirm only the checks, never the secret values.

Saving environment variables applies to the existing deployed build. The new
startup validation becomes live after the S3 code is merged and deployed.

Reference: [Render environment-variable documentation](https://render.com/docs/configure-environment-variables).
