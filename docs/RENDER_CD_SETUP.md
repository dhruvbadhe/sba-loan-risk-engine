# S9: Deploy only after CI passes

The Blueprint declares `branch: main` and `autoDeployTrigger: checksPass` for the
API. The existing service must also have the matching settings saved in Render.
S9 remains pending until the owner confirms those settings.

## Save the Render settings

1. Open [the API service settings](https://dashboard.render.com/web/srv-d9h55a4m0tmc73bruu70/settings).
2. Find **Branch** under the service's build/deploy settings. Click **Edit**, select
   `main`, and save if necessary. Confirm the repository is
   `dhruvbadhe/sba-loan-risk-engine`.
3. Find **Auto-Deploy** (or **Auto-Deploy Trigger**) and click **Edit**.
4. Select **After CI Checks Pass**, then click **Save Changes**.
5. Refresh the page. Confirm the branch still says `main` and auto-deploy still
   says **After CI Checks Pass**.
6. Reply **Render gating confirmed**. You do not need to share any credentials or
   deploy-hook URL.

If the service is managed by a Blueprint and the dashboard field is locked, the
Blueprint change in this PR must first reach its configured source branch and be
synced. Confirm the resulting service settings afterward; an unmerged file alone
does not change the running service.

## How the gates work

- Branch protection requires a PR and `lint-test-build` before merging to `main`,
  including for administrators. The branch must be up to date.
- CI runs Ruff, tests with coverage, and a Docker build in order. It also runs on
  pushes to `main`, covering the commit that Render will deploy.
- Render waits for that commit's CI checks before starting an automatic deploy.
  Render accepts GitHub conclusions `success`, `neutral`, and `skipped` as passed.
  The CI job has no skip filters or success overrides, so failed lint, tests, or
  Docker builds fail the check.
- A failed required PR check blocks merging; a failed check on a new `main` commit
  blocks its automatic Render deploy. This covers failures detected by CI, not
  every possible application defect.
- This setting gates automatic deploys. Manual deploys and deploy hooks are
  separate triggers; do not use them to promote a commit whose CI has failed.

## First deployment after the upgrade PRs land

The CI workflow is still on the upgrade branches until those PRs are merged.
Follow [the stack instructions](BRANCH_PROTECTION.md) to land the reviewed code
and workflow while preserving the test/fix commits.

After merging the upgrade stack, open **GitHub → Actions → CI** and wait for the
`push` run on `main` to pass. In **Render → Events**, confirm the automatic deploy
uses that same commit and starts after the CI completion time. Once it succeeds,
check `/health`. Record a failure as a failure; do not claim that the production
deployment has been verified before observing it.

Reference: [Render deployment documentation](https://render.com/docs/deploys) and
[Blueprint configuration](https://render.com/docs/blueprint-spec).
