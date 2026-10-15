# S8: Require CI before merging to main

The PR template is committed, but S8 is complete only after you save the following
GitHub settings. The assistant will verify the saved rule after your confirmation.

## Enable the rule

1. Open [repository branch settings](https://github.com/dhruvbadhe/sba-loan-risk-engine/settings/branches).
2. Under **Branch protection rules**, click **Add classic branch protection rule**.
3. Set **Branch name pattern** to `main`.
4. Check **Require a pull request before merging**.
   For a solo-maintained repository, leave **Require approvals** unchecked:
   the PR author cannot approve their own PR.
5. Check **Require status checks to pass before merging**.
6. Check **Require branches to be up to date before merging**.
7. In the status-check search box, search for `lint-test-build` and select it.
   Choose **GitHub Actions** as the expected source if GitHub offers that choice.
   This exact check passed in the S7 run. Do not select **Supabase Preview**, which
   is a separate integration and may be skipped.
8. Check **Do not allow bypassing the above settings** so the CI requirement also
   applies to repository administrators.
9. Leave **Allow force pushes** and **Allow deletions** unchecked. Leave
   **Lock branch** unchecked so passing PRs can still be merged.
10. Click **Create** (or **Save changes** if editing an existing rule), and complete
    GitHub's authentication prompt if shown.
11. Confirm the saved rule targets `main` and lists `lint-test-build` as required.
    Reply **Branch protection confirmed** in chat. No credentials are needed.

If the status-check search has no result, open the
[S7 CI run](https://github.com/dhruvbadhe/sba-loan-risk-engine/actions/runs/38756124322)
and confirm it succeeded, then refresh the settings page. GitHub requires the
check to have run recently before it can be selected.

## Existing stacked upgrade PRs

S1–S6 were opened before CI existed. They cannot satisfy a required CI check until
their proposed merge includes `.github/workflows/ci.yml`. Keep protection enabled.

One way to land the already-tested stack is to retarget the S7 PR to `main`:

1. Open [PR #7](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/7) and click
   **Edit** next to its title.
2. Change the **base** from `fix/S6-test-coverage` to `main`, confirm the base
   change, then click **Save**.
3. Review the cumulative diff: it will contain S1–S7. All predecessor commits are
   included because each task branch was based on the previous task.
4. If the branch is out of date, update it with `main`, then wait for
   `lint-test-build` to pass on the resulting latest commit.
5. When you choose to merge the reviewed changes, select **Create a merge commit**
   to preserve the separate failing-test and fix commits required by the plan.
   Squashing would collapse that evidence into one commit.
6. Retarget the S8 PR to `main` after S7 lands, and require its CI check to pass too.

These are manual steps for the owner; writing this document does not merge any PR.
The template becomes the default for new PRs after it reaches the default branch.

Reference: [GitHub's branch-protection guide](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule).
