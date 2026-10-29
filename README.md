# Local PTE practice scoring for a Node backend

This project runs Python locally, processes recorded spoken responses with faster-whisper, uses a local Qwen language model for textual assessment, and returns JSON for your Node backend. No paid API or cloud inference is needed. Initial installation downloads free model weights.

The service follows Pearson’s published per-question scoring rules where public. It cannot reproduce Pearson’s proprietary calibrated 10–90 scoring engine. Local AI and acoustic estimates are practice guidance, not official PTE scores.

## Run on Windows

Python 3.10+ and Node 22 are used in this workspace.

```powershell
cd C:\path\to\pte-scoring
python -m pip install -r requirements.txt
python -m pip install llama-cpp-python==0.3.36 --only-binary=:all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
python download_models.py
.\run.ps1
```

Models were downloaded and runtime dependencies were installed during implementation. The service binds to loopback, port 8000. Interactive API documentation: http://127.0.0.1:8000/docs. Models load on their first request, so the first request takes longer. The CPU runs models with a lock to prevent concurrent inference on a shared instance. Large batches may need an asynchronous job queue in your backend. Transcription defaults to English-only Whisper `base.en`; set `PTE_WHISPER_MODEL=tiny.en` for faster, lighter inference.

## Browser audio tester

Open http://127.0.0.1:8000/ to upload or drag in an audio file, play it, choose a spoken question type, and enter its reference or source context. Click **Analyze recording** to see the transcript, raw trait scores, word recognition confidence, pauses, content comparison and complete JSON. **Try sample audio** loads the included synthetic Read Aloud recording and reference. Results can be downloaded as JSON. Turn off experimental audio scores to leave pronunciation and fluency pending. The optional service key is held only in the current page, not saved in browser storage.

The browser UI covers all 22 supported PTE Academic item types. Spoken responses use local transcription; writing tasks and objective reading/listening answers use text or line-by-line answer-key inputs. The page is served by the same Python process.

Optional environment settings:

```powershell
$env:PTE_SERVICE_KEY = 'set-a-shared-secret'
$env:PTE_MODEL_PATH = 'C:\models\your-instruct-model.gguf'
$env:PTE_WHISPER_MODEL = 'small.en'
```

Use the same service key in Node. Do not expose this inference service directly to the public. Authenticate users and fetch answer keys and acoustic evidence in your Node backend.

## Node integration

### Writing in the browser

Choose **Summarize Written Text** or **Write Essay**, enter the source passage or
essay prompt, and type the student's response. The form shows a live word count
and sends text to `/v1/score-question`. Results include raw rubric traits, feedback,
the submitted answer and word count. No 10–90 conversion is invented. Missing
model assessments stay pending.

Extended responses, including open-response speaking tasks, use a free local Qwen
3B Q4 model with task-specific published-rubric guidance. Override it with
`PTE_WRITING_MODEL_PATH` or `PTE_MODEL_PATH`, or configure an Ollama provider.
`python check_writing_quality.py` runs a small semantic smoke check, not a
human-rated accuracy benchmark; passing it does not establish 90% accuracy.

The bundled models are not trained or validated on Pearson’s human-rated response
set. They can still make incorrect trait judgements. Incomplete feedback is replaced
with a warning. Do not treat local marks as a 90%-accurate service or as Pearson scores.

### Published item scores and audio evidence

Question results use Pearson’s public PTE Academic item rules where available. For this app’s requested practice display, Read Aloud credited words are normalized proportionally to content /5; pronunciation and oral fluency are each /5. The normalized content scale differs from Pearson’s prompt-length content points. Other speaking and writing tasks use their published trait maxima. Objective reading/listening tasks use per-blank, per-word, adjacent-pair or answer-key points, including the published zero-floor penalty for incorrect multiple selections. Writing form checks implement the published SWT, SST and essay word-count bands.

These are question-level points, not a conversion to an official communicative skill or overall score. Pearson’s 10–90 model is proprietary and calibrated against expert ratings; selected answers cannot produce an official predicted score.

Read Aloud audio responses include `skill_analysis` diagnostics. Pronunciation accuracy is marked unavailable because ASR confidence cannot measure phoneme production. Recognition confidence is reported separately; fluency and speed remain uncalibrated pace/pause diagnostics. Stress uses an experimental Praat acoustic variation estimate (see below).

Stress estimation (`acoustic_variation_v1`) uses Praat pitch tracking and Whisper word boundaries. At least four words and 50% of recognized words must have usable timing, recognition confidence >=0.5, and three voiced frames with pitch strength >=0.6. It measures the 10th–90th percentile spreads of median word pitch (semitones), word RMS loudness (dB), and log2 word duration. The displayed percentage is `100 * (0.5 * min(pitch_spread/6, 1) + 0.35 * min(loudness_spread/12, 1) + 0.15 * min(duration_spread/1.5, 1)`. These caps and weights are unvalidated heuristics. Higher means more acoustic variation, not better stress or correct lexical stress. Word length and intonation also affect the measure. Recording gain is normalized; low-coverage responses stay unavailable. Coverage, features, weights, and caps are returned in JSON. This diagnostic never changes the task-point score.

The backend was not present in the supplied workspace, so the integration is a reusable ESM module rather than a patch to your existing server.

```javascript
import { readFile } from 'node:fs/promises';
import { PteClient } from './node/pte-client.mjs';
const pte = new PteClient();
const recording = await readFile('/path/to/student-recording.wav');
const result = await pte.scoreAudio({
  id: 'q-1',
  type: 'RA',
  reference: 'They have enough work to keep them going.'
}, recording, { allowProxyScores: true });
console.log(result);
```

The audio API accepts WAV, MP3, WebM and other formats supported by PyAV. Limits: 10 MB decoded base64 bytes, 0.25–240 seconds. This implementation holds audio in memory and does not save student recordings. Your Node upload middleware should enforce the same file-size limit before buffering.

`allowProxyScores: true` returns a complete practice result for spoken tasks using ASR word confidence as a recognition proxy and speaking pace/pauses as fluency proxies. These are **not validated pronunciation/fluency marks**. Word colors use confidence thresholds 80 and 50; `/` marks gaps of at least 0.5 seconds. The response includes confidence, word timestamps, pace, pauses and the limitation. The default is false: transcription/content are processed but pronunciation/fluency remain pending. For validated acoustic scores, pass trusted server-generated `speech` evidence to the question/attempt endpoint instead.

The Express mounting helper is `node/express-route.mjs`. Its `loadAttempt` callback must retrieve questions and student responses from your DB and check ownership. Do not accept `correct`, reference text or speech scores from the learner as trusted data. Store the transcription and audio diagnostics for later reporting. When opted into proxies, map the audio trait scores and word diagnostics into `speech` with source `uncalibrated_local_asr_and_timing_proxy` before scoring the complete attempt.

## Endpoints and types

| Endpoint | Purpose |
|---|---|
| GET /health | Service configuration and load state, not a model accuracy check |
| GET /v1/question-types | 22 types, aliases, weights, targets and trait maxima |
| POST /v1/score-question | Score a response/transcript with an answer key or local LLM |
| POST /v1/score-audio | Transcribe a speaking recording and score its response |
| POST /v1/score-attempt | Generate all module analysis rows and independent overall analysis |
| POST /v1/gre/analytical-writing | Estimate a GRE Analyze an Issue essay score (0–6, half-point steps) |
| POST /v1/chat | Answer a basic question with the configured local LLM |

The GRE essay route is separate from PTE attempt totals. Send `{ "prompt": "...", "instructions": "...", "response": "..." }` to `/v1/gre/analytical-writing`. The score is a local practice estimate, mapped from the model's doubled integer rubric onto the published 0–6 half-point scale; an empty response returns `no_score`. The `/v1/chat` route identifies itself as Ooshas AI and accepts `{ "message": "...", "prompt": "...optional student details...", "history": [{ "role": "user", "content": "..." }] }`. Use `prompt` to pass relevant learner context such as exam, target score, test date, or study level. History is optional and limited to 20 turns. Both routes use the same configured local model and service-key authentication as the PTE endpoints. In Node, `PteClient` provides `scoreGreEssay({ prompt, instructions, response })` and `chat(message, history, prompt)`.

| Type | Question | Response/key |
|---|---|---|
| RA | Read Aloud | Text/transcript plus reference |
| RS | Repeat Sentence | Text/transcript plus reference |
| DI | Describe Image | Transcript plus server-written image description/key points |
| RL | Retell Lecture | Transcript plus source lecture transcript |
| SGD | Summarize Group Discussion | Transcript plus source including each speaker |
| RTS | Respond to a Situation | Transcript plus situation prompt |
| ASQ | Answer Short Question | Transcript and accepted answer(s) |
| WE | Write Essay | Text plus prompt |
| SWT | Summarize Written Text | Text plus source |
| SST | Summarize Spoken Text | Written response plus source audio transcript |
| FIB | Reading dropdown blanks | Arrays of response words and correct words |
| FIB_DD | Reading drag/drop blanks | Arrays in blank order |
| FIB_L | Listening type-in blanks | Arrays in blank order |
| RO | Reorder Paragraphs | Arrays of unique paragraph IDs |
| MCM_R / MCM_L | Multiple answers | Arrays of selected and correct option IDs |
| MCS_R / MCS_L | Single answer | Selected and correct option ID |
| HCS | Highlight Correct Summary | Selected and correct option ID |
| SMW | Select Missing Word | Selected and correct option ID |
| HIW | Highlight Incorrect Words | Selected/correct token-position IDs, not word strings |
| WFD | Write from Dictation | Written response plus reference |

Describe Image currently requires a textual image description from your question bank; the model does not inspect images. Source lecture/discussion audio needs a prepared transcript. Recordings submitted to `/v1/score-audio` are student answers, not source material. Summarize Spoken Text and Write from Dictation assess typed student responses, so submit those to the text endpoint.

## Attempt request

```json
{
  "attempt_id": "student-attempt-1",
  "targets": {"RO": 50},
  "questions": [
    {"id":"1","type":"MCM_R","correct":["a","c"],"response":["a","b"]},
    {"id":"2","type":"RO","correct":["1","2","4","3","5"],"response":["1","2","3","4","5"]},
    {"id":"3","type":"WFD","reference":"They have enough work to keep them going.","response":"They have work to keep them going."}
  ]
}
```

You get `questions` with trait scores, word/blank/pair details, and feedback, plus `report.speaking`, `writing`, `reading`, `listening`, and `overall`. Rows have section, item, contribute, my_correctness, target, status and counts. Targets can be configured per canonical question type. Absent types are `Not attempted`; submitted blank responses are scored zero. Pending traits do not receive invented scores.

## How deck requirements are handled

Weights and targets come from screenshots on slides 3–6 and 29. The deck has inconsistencies: reading weights total 101%, the reorder examples do not consistently match the supplied key, slide 14 calls a written-text example group discussion, and slide 29 has three `<1%` overall weights. We use normalized reading weights, adjacent ordered paragraph pairs, SWT for the written example, and explicitly assume 0.5% for each `<1%` entry. All assumptions are returned in the report. Missing types prevent a complete module score; partial correctness and coverage are separate fields.

Overall practice correctness is calculated from its own question weights and is never an average of the modules. No 10–90 score is derived. Objective marking includes negative marking with a zero floor, positional blanks, adjacent pairs, and counted dictation words with extras struck and missed words red.

Writing and extended spoken content use bounded structured JSON judgments from Qwen 3B, guided by Pearson's public descriptors. Form and zero-content gates are applied server-side. AI trait marks remain unvalidated estimates. Writing form checks are code-based approximations; abbreviations and unusual sentence boundaries require further linguistic validation.

## Train your own acoustic estimator

`train_audio_model.py` provides a reproducible training path using free scikit-learn. Install `requirements-training.txt`, then supply **real human-rated** rows from your own licensed dataset with a speaker ID, audio features, and 0–5 trait scores. Splits are grouped by speaker to prevent the same speaker appearing in training and evaluation. The script reports held-out MAE and saves an estimator. It is a regression model over audio features, not a new foundation LLM or phoneme recognizer. No accuracy claims are possible without this data. The live service intentionally does not load an unvalidated estimator automatically. This training path has not been run on a real rated dataset, because none was supplied.

```powershell
python -m pip install -r requirements-training.txt
python train_audio_model.py human-rated-recordings.jsonl
```

Each JSONL row has this shape (values below illustrate the schema only):

```json
{"speaker_id":"speaker-001","features":{"recognition_confidence":0.85,"words_per_minute":135,"pause_ratio":0.12,"duration_seconds":35,"rms":0.08},"pronunciation":3,"oral_fluency":4}
```

## Test

```powershell
python -m pip install pytest==9.1.1 httpx==0.28.1
python -m pytest -q
# Run service in another terminal first:
node node/smoke-test.mjs
```

Unit tests cover all 22 types with controlled assessor fixtures, score arithmetic, penalties, validation, incomplete results, auth and silent/malformed audio. The Node smoke test makes real HTTP calls and performs real local Whisper inference on the bundled synthetic recording. `examples/local-llm-result.json` comes from actual local Qwen inference. These are functional checks, not evidence of exam scoring accuracy.

## Sources and model licenses

- [faster-whisper (MIT)](https://github.com/SYSTRAN/faster-whisper)
- [llama-cpp-python (MIT)](https://github.com/abetlen/llama-cpp-python)
- [Qwen2.5 3B GGUF model card](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF)
- [Pearson PTE Academic Test Taker Score Guide](https://www.pearsonpte.com/content/dam/ELL/pte/pearsonpte/pdfs/pte-academic-pdfs/PTE-Academic-Test-Taker-Score-Guide.pdf)

The bundled `read-aloud.wav` was generated locally with Windows speech synthesis for a repeatable functional test. Extracted deck images under `spec` are specification evidence, not a training dataset.
