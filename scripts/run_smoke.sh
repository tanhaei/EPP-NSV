#!/usr/bin/env bash
set -euo pipefail
python -m compileall -q src
python -m pytest -q
python -m epp_nsv.experiments --n-pairs 64 --seed 17 --out-dir outputs/smoke
