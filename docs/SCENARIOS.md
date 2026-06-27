# Three Scenarios

1) Greenfield
- Task: Build the entire URL shortener from scratch (APIs, DB, frontend).
- Decomposition: models -> storage -> APIs -> frontend -> tests -> CI -> docs.
- Validation: unit/integration tests; local docker-compose smoke tests.

2) Brownfield
- Task: Add analytics tracking to an existing shortener (ClickEvent + API).
- Decomposition: DB migration or new table -> capture events on redirect -> analytics endpoint -> tests.
- Validation: integration tests that emulate shortening + clicks.

3) Ambiguous
- Task: “Add analytics” without definition of scope.
- Approach: ask clarification, assume required: daily counts, total clicks, last-N-days view; implement accordingly and document assumptions.
- Validation: documented assumptions, tests to show expected aggregation.