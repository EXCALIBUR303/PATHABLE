# Phase 0 evidence

Date: 2026-10-12. Working directory: `/workspace/PATHABLE`. Git state: unborn local `work` branch, new files saved locally, no commit/push/deployment. Phase 0 design checks only; the following commands were executed.

| Command / inspection | Observed result |
| --- | --- |
| `git status --short --branch` before file creation | `No commits yet on work`; no existing source files |
| `git --version` | 2.52.0 |
| `python3 --version` | 3.12.14 |
| `node --version` | v24.19.0 |
| `npm --version` | 11.9.0 |
| `docker compose version` | v2.40.3, exit 0 |
| `docker info --format '{{.ServerVersion}}'` | 28.4.0, exit 0; daemon responds |
| native `psql` executable presence | Unavailable; not a Phase 0 requirement |
| npm `/latest` and PyPI `/json` HTTPS metadata queries using Python urllib | 15 package metadata reads succeeded; candidates/peer bounds recorded in architecture; no installation performed |
| `python3 scripts/validate_phase0.py` | Exit 0: **38 design checks passed**, including **13 exhaustive fixture scenarios** and **8 contrast pairs**; no failures or skips |
| `git diff --check` | Exit 0; separate validator whitespace check covers new untracked files |
| `git status --short --untracked-files=all` | Only newly created Phase 0 docs/scaffold/examples/configuration/validator; no pre-existing source modifications |
| Isolated negative control (exact command below) | Harness exit 0; validator correctly exited 1 at `design_case_unconstrained_stairs` after expected cost changed to 999; original checkout unchanged |

The design validator reports required file/link/scaffold checks, numerical-graph integrity, ECEF lower bounds and consistency, exhaustive tiny-fixture scenarios, authored API example consistency and proposed token contrast. These are not real application tests. Future application checks must be recorded separately with test-run counts and output evidence.

Required tests A–L: **all unrun** (their implementation phases have not started). Backend API, DB migrations/persistence, frontend build/browser/keyboard, Dijkstra/A* comparison, report/SSE integration, upload security, model training/evaluation, production build and fresh-task restoration: **unrun**. No skipped or expected-failure product test has been relabeled as a pass.

## Negative-control command

This intentionally corrupts a fixture only in a temporary copy. Its expected rejection is evidence that the design check detects an incorrect cost, not a production test failure.

```sh
python3 - <<'PY'
from pathlib import Path
import json,shutil,subprocess,tempfile
with tempfile.TemporaryDirectory(prefix='pathable-phase0-negative-',dir='/tmp') as directory:
 copy=Path(directory)/'PATHABLE'
 shutil.copytree('/workspace/PATHABLE',copy,ignore=shutil.ignore_patterns('.git'))
 file=copy/'docs/examples/routing-cases.json'
 cases=json.loads(file.read_text())
 cases[0]['expected_cost']=999
 file.write_text(json.dumps(cases,indent=2)+'\n')
 result=subprocess.run(['python3','scripts/validate_phase0.py'],cwd=copy,capture_output=True,text=True)
 assert result.returncode==1, result.stdout+result.stderr
 assert 'design_case_unconstrained_stairs' in result.stderr, result.stderr
 print('PASS negative control: altered expected route cost was rejected (validator exit 1). Original checkout unchanged.')
PY
```
