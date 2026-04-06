# METATRON QUANTUM OS v3.1 — Makefile
.PHONY: install run train export clean test

install:
	chmod +x install.sh && ./install.sh

run:
	source venv/bin/activate && python quantum_desktop.py

train:
	source venv/bin/activate && python z9_qat_training.py

train-full:
	source venv/bin/activate && python z9_qat_training.py full

export:
	source venv/bin/activate && python z9_qat_training.py export
	ollama create z9-gemma-abliterated -f Modelfile

test:
	source venv/bin/activate && python -m pytest tests/ -v

clean:
	rm -rf logs/metatron.log checkpoints/*.pth __pycache__ core/__pycache__ agents/__pycache__
