# Privacy model

## Enforced boundaries
| Boundary | Mechanism |
|---|---|
| Bank → coordinator | Only numpy parameter arrays; `assert_only_parameters` guard |
| Bank data isolation | Per-bank read-only volume mounts; `assert_path_within` guard against `../` and symlinks |
| Coordinator | Mounts only the model registry; no bank data path exists in its container |
| Image content | Dockerfile copies code only; data is never baked into images |
| Repository | `.gitignore` excludes `ai_engine/data/banks/*` and model artifacts |
| Secrets | `.env` ignored; production startup rejects placeholder secrets |

## Not yet protected (honest gaps)
- Parameter updates can leak training data. Planned: clipping + calibrated Gaussian noise, with measured
  utility/privacy trade-off; secure aggregation evaluated.
- Alert metadata is sensitive; field-level minimisation and access auditing are Phase 2/7 work.
- Docker-volume isolation is a simulation of organisational isolation, not a substitute for it.
