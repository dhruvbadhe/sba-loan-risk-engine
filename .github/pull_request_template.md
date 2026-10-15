## Change

Describe the problem and the resulting behavior. Include the upgrade task ID, if applicable.

## Validation

List the commands run and their results. For bug fixes, include the failing result
before the fix and the passing result afterward.

## Review checklist

- [ ] The task's done-check passes; any pending external settings are identified.
- [ ] The change stays within the task's scope and contains no real secrets.
- [ ] CI `lint-test-build` passes on the latest commit before merging to `main`.
