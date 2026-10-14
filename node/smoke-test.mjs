import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { PteClient } from './pte-client.mjs';
const client = new PteClient();
const types = await client.questionTypes();
assert.equal(types.types.length, 22);
const mcq = await client.scoreQuestion({id:'mcq', type:'MCM_R', correct:['a','b'], response:['a','x']});
assert.equal(mcq.score, 0);
const bytes = await readFile(new URL('../examples/read-aloud.wav', import.meta.url));
const audio = await client.scoreAudio({id:'audio-ra', type:'RA', reference:'They have enough work to keep them going.'}, bytes, {allowProxyScores:true});
assert.equal(audio.status, 'scored');
assert.ok(audio.audio.transcript.toLowerCase().includes('work'));
assert.ok(audio.details.pronunciation_words.length > 0);
await writeFile(new URL('../examples/audio-result.json', import.meta.url), JSON.stringify(audio, null, 2));
const writing = await client.scoreQuestion({id:'local-llm-swt', type:'SWT',
  reference:'Libraries provide free books, internet access and study spaces. They support students and help communities learn.',
  response:'Libraries support community learning by offering free books, internet access and study spaces.'});
assert.equal(writing.status, 'scored');
await writeFile(new URL('../examples/local-llm-result.json', import.meta.url), JSON.stringify(writing, null, 2));
const attempt = await client.scoreAttempt({attempt_id:'node-demo', questions:[
  {id:'mcq',type:'MCM_R',correct:['a','b'],response:['a','x']},
  {id:'dictation',type:'WFD',reference:'They have enough work to keep them going.',response:'They have work to keep them going.'}
]});
assert.equal(attempt.report.overall.complete,false);
assert.equal(attempt.report.overall.practice_score_10_90,null);
await writeFile(new URL('../examples/attempt-result.json', import.meta.url), JSON.stringify(attempt, null, 2));
console.log(JSON.stringify({types:types.types.length, negativeMarking:mcq.score, audioTranscript:audio.audio.transcript,
  audioScore:audio.score, audioMax:audio.max_score, status:audio.status, writingScore:writing.score, writingMax:writing.max_score,
  incompleteAttemptHandled:!attempt.report.overall.complete}));
