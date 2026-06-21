.PHONY: install test smoke experiment mutation

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest -q

smoke:
	python -m epp_nsv.experiments --n-pairs 64 --seed 17 --out-dir outputs/smoke

experiment:
	python -m epp_nsv.experiments --n-pairs 300 --seed 7 --out-dir outputs/experiment

mutation:
	python -m epp_nsv.mutation --n-pairs 64 --seed 17 --out-dir outputs/mutation_seed17
