# Complete project handoff

## Packages

The source archive contains all application code, tests, UI files, Node integration, setup scripts, sample audio, recorded functional test results and extracted presentation references.

The bundle with models contains the same project plus the downloaded local Qwen GGUF and Whisper weights. Neither archive contains a Python interpreter, Node runtime or installed Python packages. Install Python 3.10+ and Node 22, then install dependencies. Internet access is needed for dependency installation; the source package also needs the initial model downloads. Archives exclude environment files, credentials, virtual environments, interpreter caches and temporary logs.

## Windows quick start

Extract the ZIP to a writable folder, open PowerShell there, then run:

```powershell
# Source archive: install packages and download model weights
.\setup.ps1

# For the archive that already includes models, use this instead:
# .\setup.ps1 -SkipModelDownload

.\run.ps1
```

Open http://127.0.0.1:8000/ for the upload UI or http://127.0.0.1:8000/docs for API schemas. Do not launch a second process on port 8765 if the service is already running. The setup script automates the installation commands used during development; the full new-machine setup has not been tested on a clean machine.

## Code map

| Location | Contents |
|---|---|
| `pte/api.py` | FastAPI endpoints and UI hosting |
| `pte/audio.py` | Local speech transcription, timing diagnostics and experimental audio proxies |
| `pte/llm.py` | Local GGUF inference and structured score validation; optional Ollama adapter |
| `pte/engine.py` | Objective marking, trait combination, module rows and overall practice calculation |
| `pte/config.py` | 22 types, aliases, deck weights, targets and trait maxima |
| `pte/models.py` | Request validation and schemas |
| `ui/` | Complete browser UI: HTML, CSS and JavaScript |
| `node/pte-client.mjs` | Reusable Node API client |
| `node/upload-audio.mjs` | Upload an audio file from Node and print the JSON result |
| `node/express-route.mjs` | Mounting helper for an existing authenticated Express backend |
| `node/smoke-test.mjs` | Real Node-to-Python audio, writing and attempt checks |
| `tests/test_scoring.py` | 22 automated test cases |
| `download_models.py` | Download free model weights |
| `train_audio_model.py` | Training entry point for a feature-based estimator using human-rated data |
| `requirements*.txt` | Application, test and optional training dependencies |
| `examples/` | Sample recording, output JSON and honest test report |
| `spec/` | Images extracted from the supplied specification deck |

## Node upload

```powershell
node node/upload-audio.mjs "C:\audio\student.wav" "Text the student should read."
```

No npm packages are required for this client. The Express helper requires your existing Express server and an implementation of `loadAttempt`; it is not a standalone backend or DB schema.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest -q
# With the Python service running:
node node/smoke-test.mjs
```

Application tests and real inference checks passed. Scoring-quality checks did not all pass: the small Qwen model awarded full marks to an unrelated summary and an instruction-containing response. See `examples/TEST-REPORT.md` and `validation-results.json`. These findings remain unresolved in this handoff.

Question-level points follow public Pearson criteria where available. Attempt weight summaries and all local AI/audio grades are practice estimates. Pearson’s proprietary 10–90 calibration cannot be reproduced. Qwen judgments and ASR/timing proxies need human-rated validation; none has been supplied.

For API payloads, supported types, model-license links and details of deck inconsistencies, read `README.md`.
