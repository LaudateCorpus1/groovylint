all: update sync

sync:
	pip-sync requirements.txt

update:
	pip-compile --allow-unsafe --quiet requirements.in --output-file requirements.txt
	pip-compile --allow-unsafe --quiet requirements-dev.in --output-file requirements-dev.txt
