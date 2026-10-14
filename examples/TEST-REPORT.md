# PTE test results — 13 October 2026

Automated test suite: 22 passed. These tests use controlled LLM fixtures where appropriate and do not establish scoring accuracy.

Real Node-to-Python smoke test: passed. The local Whisper model transcribed the synthetic test recording correctly. Read Aloud returned 17.49/18 with explicitly enabled acoustic proxies. The local Qwen model scored the relevant written summary 9/9. The partial attempt did not receive an invented complete overall score.

Additional real HTTP checks: 4 passed, 2 failed.

| Check | Result |
|---|---|
| Invalid question type returns 422 | Passed |
| Malformed audio returns 422 | Passed |
| Dictation handles repeated/extra words | Passed |
| Audio without proxies leaves pronunciation/fluency pending | Passed |
| Clearly unrelated summary receives zero content | FAILED |
| Response containing scoring instructions receives zero content | FAILED |

The current Qwen 0.5B model gives excessive marks to the unrelated answer and to the instruction-containing answer. Valid bounded JSON does not imply a correct assessment. The service functions end to end, but subjective assessment is not reliable enough for student scoring. Pronunciation/fluency proxies also remain uncalibrated. A stronger model and a rated evaluation dataset are needed before relying on writing or spoken-content marks.

Full check payloads and results: `validation-results.json`. Tests used synthetic speech, not recordings from real PTE learners. No accuracy percentage has been established.
