# Local PTE practice scoring for a Node backend

This project runs Python locally, processes recorded spoken responses with faster-whisper, uses a local Qwen language model for textual assessment, and returns JSON for your Node backend. No paid API or cloud inference is needed. Initial installation downloads free model weights.

The service is your own application around existing open models. A newly trained PTE language/pronunciation model is not included: that requires licensed training data and human-rated recordings. Qwen 0.5B is a small CPU demonstration model and its judgments need review. Larger compatible GGUF models can replace it by setting `PTE_MODEL_PATH`.

## Run on Windows

Python 3.10+ and Node 22 are used in this workspace.

```powershell
cd C:\Users\hp\Documents\ChatGPT\linkdin\pte-scoring
python -m pip install -r requirements.txt
python -m pip install llama-cpp-python==0.3.36 --only-binary=:all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
python download_models.py
.\run.ps1
```

Models were downloaded and runtime dependencies were installed during implementation. The service binds to loopback, port 8765. Interactive API documentation: http://127.0.0.1:8765/docs. Models load on their first request, so the first request takes longer. The CPU runs models with a lock to prevent concurrent inference on a shared instance. Large batches may need an asynchronous job queue in your backend.

## Browser audio tester

Open http://127.0.0.1:8765/ to upload or drag in an audio file, play it, choose a spoken question type, and enter its reference or source context. Click **Analyze recording** to see the transcript, raw trait scores, word recognition confidence, pauses, content comparison and complete JSON. **Try sample audio** loads the included synthetic Read Aloud recording and reference. Results can be downloaded as JSON. Turn off experimental audio scores to leave pronunciation and fluency pending. The optional service key is held only in the current page, not saved in browser storage.

The UI supports the seven spoken question types. Other question types use the text APIs. The browser page is served by the same Python process; no separate frontend build or Node server is required. Browser QA verified sample analysis, actual file upload, pending trait display with proxies disabled, and JSON download.

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
the submitted answer, word count, and `writing.practice_score_10_90` (10 + 80 times
the raw-score fraction). Missing model assessments stay pending. The local model
now requests structured, response-specific feedback for these two writing tasks.

The bundled Qwen 0.5B model is **blocked for writing assessment** after it awarded
full content marks to unrelated and contradictory summaries. Form checks still
work. Writing now uses the installed Qwen 1.5B model for experimental scores. Override
its path with `PTE_WRITING_MODEL_PATH`, or configure `PTE_MODEL_PATH` or an Ollama provider,
then run `python check_writing_quality.py`. This is a small semantic smoke check,
not a human-rated accuracy benchmark; passing it does not establish 90% accuracy.
Writing grades and feedback require human validation before learner decisions.

On the supplied bioluminescence example, the tested Qwen 1.5B Q4_K_M candidate
still gave unsupported grammar criticism and undervalued accurate summaries.
It passed only four of six final semantic smoke checks. It is enabled for
experimental writing feedback, not as a validated grader or a 90%-accurate service. See `examples/writing-quality-check.json` for outputs.
These six developer cases are not an accuracy percentage or a PTE calibration set.

### Read Aloud score display

Read Aloud responses include `read_aloud_score` in the question, audio and attempt APIs.
Its `total` and `traits` (content, pronunciation, oral_fluency) are integer practice
scores from 10 to 90. Each trait uses `10 + 80 * raw_score / raw_maximum`.
The total uses `10 + 80 * mean(content_ratio, pronunciation_ratio, fluency_ratio)`,
rounded once to the nearest integer. Equal trait weighting is an explicit practice
assumption, not Pearson's proprietary score conversion. Normalization prevents
longer reference passages from increasing content's share of the displayed total.
For example, content 3/4, pronunciation 2.5/5 and fluency 5/5 display 70, 50 and
90, with a total of 70/90. Existing zero-content/no-response gates produce 10/90.
Missing acoustic evidence leaves the total and missing traits null (Pending).
The existing raw `score`, `max_score`, `traits`, and report calculations are retained.
The browser displays this summary for Read Aloud; other question types retain raw points.

Read Aloud audio responses also include `skill_analysis`, shown as a separate card
with percentage bars and expandable explanations. Pronunciation accuracy uses mean
ASR confidence; fluency uses the existing pace/pause estimate; speed shows pace fit
(100% at 100–230 words/min, reduced outside that range). These are uncalibrated
diagnostics, not learner percentiles or additional total-score components. Stress
uses an experimental Praat acoustic variation estimate (see below). With no
detected speech or experimental scores disabled, percentages are null and the UI
shows N/A. Each metric includes its status and explanation in downloaded JSON.

Stress estimation (`acoustic_variation_v1`) uses Praat pitch tracking and Whisper
word boundaries. At least four words and 50% of recognized words must have usable
timing, recognition confidence >=0.5, and three voiced frames with pitch strength
>=0.6. It measures the 10th–90th percentile spreads of median word pitch (semitones),
word RMS loudness (dB), and log2 word duration. The displayed percentage is
`100 * (0.5 * min(pitch_spread/6, 1) + 0.35 * min(loudness_spread/12, 1) + 0.15 * min(duration_spread/1.5, 1))`.
These caps and weights are unvalidated heuristics. Higher means more acoustic
variation, not better stress or correct lexical stress. Word length and intonation
also affect the measure. Recording gain is normalized; low-coverage responses stay
unavailable. Coverage, features, weights, and caps are returned in JSON. This
diagnostic never changes trait scores or the 10–90 total.

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

Overall is calculated from its own question weights and is never an average of the modules. The 10–90 practice display uses `10 + 0.8 × weighted_correctness`. This is an uncalibrated display mapping, not Pearson's proprietary score conversion. Do not market these numbers as certified PTE predictions without validation on held-out rated attempts. Objective marking includes negative marking with a zero floor, positional blanks, adjacent pairs, and counted dictation words with extras struck and missed words red.

Writing and extended spoken content use bounded structured JSON judgments from Qwen. Form and zero-content gates are applied server-side. The rubric prompt is a simplified practice rubric, not a full replica of every official descriptor. The small model may score incorrectly even when it produces valid JSON. Writing form checks are approximations; abbreviations, bullet-only writing and unusual sentence boundaries require further linguistic validation.

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
- [Qwen2.5 0.5B GGUF model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF)
- [Pearson score guide](https://www.pearsonpte.com/content/dam/ELL/pte/pearsonpte/resources/PTE-Academic-Test-Taker-Score-Guide.pdf)

The bundled `read-aloud.wav` was generated locally with Windows speech synthesis for a repeatable functional test. Extracted deck images under `spec` are specification evidence, not a training dataset.
