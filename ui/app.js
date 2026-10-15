const $ = id => document.getElementById(id);
let recording = null, objectUrl = null, lastResult = null, busy = false;
const labels = {
  SWT: ['Source passage', 'Paste the passage to summarize…', 'Write one sentence of 5–75 words that captures the main ideas.'],
  WE: ['Essay prompt', 'Enter the essay question…', 'Write a structured essay of 200–300 words addressing the prompt.'],
  SST: ['Source lecture transcript', 'Paste the lecture transcript…', 'Summarize the spoken text in 50–70 words.'],
  WFD: ['Reference sentence', 'Enter the sentence from the dictation…', 'Type the words you heard. Correct spelling is scored word by word.'],
  RA: ['Reference text', 'Enter the exact text the student should read…', 'The transcript is compared with this text to find missed, extra and changed words.'],
  RS: ['Reference sentence', 'Enter the sentence the student should repeat…', 'Enter the original sentence, not the student transcript.'],
  DI: ['Image description / key information', 'Describe the chart, image and its important features…', 'The current model uses this description. It does not inspect an image.'],
  RL: ['Source lecture transcript', 'Paste the original lecture transcript…', 'Upload the student’s retelling, and provide the source lecture here.'],
  SGD: ['Source discussion transcript', 'Paste the discussion, with speaker labels…', 'Include each speaker’s views in the source transcript.'],
  RTS: ['Situation prompt', 'Describe the situation and who the student is speaking to…', 'Give the original situation the student was asked to respond to.'],
  ASQ: ['Question', 'Enter the short-answer question…', 'Upload the spoken answer. Add accepted answers in the answer key below.'],
  FIB: ['Passage', 'Paste the passage with blanks…', 'Enter the correct blank words and your answers in matching line order.'],
  FIB_DD: ['Passage', 'Paste the passage with blanks…', 'Enter the correct blank words and your answers in matching line order.'],
  FIB_L: ['Listening transcript', 'Paste the transcript with blanks…', 'Enter the correct blank words and your answers in matching line order.'],
  RO: ['Paragraphs or prompt', 'Enter the paragraph set or prompt…', 'Enter the correct paragraph IDs and your order, one ID per line.'],
  MCM_R: ['Reading passage and question', 'Paste the passage and question…', 'Use option IDs to show all correct choices and the choices you selected.'],
  MCM_L: ['Listening transcript and question', 'Paste the transcript and question…', 'Use option IDs to show all correct choices and the choices you selected.'],
  MCS_R: ['Reading passage and question', 'Paste the passage and question…', 'Enter the correct option ID and the option you selected.'],
  MCS_L: ['Listening transcript and question', 'Paste the transcript and question…', 'Enter the correct option ID and the option you selected.'],
  HCS: ['Listening transcript and question', 'Paste the transcript and question…', 'Enter the correct summary ID and the summary you selected.'],
  SMW: ['Listening transcript and question', 'Paste the transcript with the missing word…', 'Enter the correct option ID and the option you selected.'],
  HIW: ['Transcript and question', 'Paste the transcript…', 'Use the word IDs from the options list; correct selections earn points and incorrect selections lose points.']
};
const AUDIO_TYPES = new Set(['RA','RS','DI','RL','SGD','RTS','ASQ']);
const TEXT_TYPES = new Set(['SWT','WE','SST','WFD']);
const STRUCTURED_TYPES = new Set(['ASQ','FIB','FIB_DD','FIB_L','RO','MCM_R','MCM_L','MCS_R','MCS_L','HCS','SMW','HIW']);
const ARRAY_TYPES = new Set(['FIB','FIB_DD','FIB_L','RO','MCM_R','MCM_L','HIW']);
const OPTION_TYPES = new Set(['MCM_R','MCM_L','MCS_R','MCS_L','HCS','SMW','HIW']);
function status(message, error = false) { $('status').textContent = message; $('status').className = error ? 'error' : ''; }
function setRecording(file) {
  if (busy) return;
  if (!file || !file.size) { status('Choose a nonempty audio file.', true); return; }
  if (file.size > 10000000) { status('Choose an audio file smaller than 10 MB.', true); return; }
  recording = file;
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(file);
  $('player').src = objectUrl; $('player').hidden = false;
  $('filename').textContent = `${file.name} · ${(file.size / 1024).toFixed(0)} KB`;
  $('results').hidden = true; $('empty').hidden = false; $('download').hidden = true; lastResult = null;
  status('Recording ready. Add the question context and analyze.');
}
function updateType() {
  const [label, placeholder, help] = labels[$('type').value];
  $('context-label').textContent = label; $('context').placeholder = placeholder; $('context-help').textContent = help;
  const type=$('type').value, audio=AUDIO_TYPES.has(type), typed=TEXT_TYPES.has(type), structured=STRUCTURED_TYPES.has(type);
  $('context').required = true;
  $('audio-input').hidden = !audio; $('proxy-option').hidden = !audio; $('writing-input').hidden = !typed; $('structured-input').hidden = !structured;
  $('writing-answer').required = typed; $('answer-key').required = structured; $('student-answer').required = structured && type!=='ASQ';
  $('student-answer-input').hidden = type==='ASQ'; $('options-input').hidden = !OPTION_TYPES.has(type);
  $('structured-guidance').textContent = structured ? help : '';
  $('input-heading').textContent = audio ? 'Your recording' : structured ? 'Your answer' : 'Your writing';
  $('submit').textContent = audio ? 'Analyze recording ↗' : structured ? 'Check answer ↗' : 'Analyze writing ↗';
  $('writing-guidance').textContent = typed ? help : '';
  $('results').hidden = true; $('empty').hidden = false; $('download').hidden = true; lastResult = null; status('');
}
$('writing-answer').addEventListener('input', () => {
  const count = ($('writing-answer').value.match(/[\p{L}\p{N}_]+(?:['’][\p{L}\p{N}_]+)*/gu) || []).length;
  $('word-count').textContent = `${count} words`;
});
$('type').addEventListener('change', updateType);
$('file').addEventListener('change', e => setRecording(e.target.files[0]));
for (const name of ['dragenter', 'dragover']) $('dropzone').addEventListener(name, e => { e.preventDefault(); $('dropzone').classList.add('dragging'); });
for (const name of ['dragleave', 'drop']) $('dropzone').addEventListener(name, e => { e.preventDefault(); $('dropzone').classList.remove('dragging'); });
$('dropzone').addEventListener('drop', e => setRecording(e.dataTransfer.files[0]));
$('sample').addEventListener('click', async () => {
  if (busy) return;
  try {
    const r = await fetch('/sample-audio'); if (!r.ok) throw new Error('Sample audio could not be loaded.');
    setRecording(new File([await r.blob()], 'sample-read-aloud.wav', { type: 'audio/wav' }));
    $('type').value = 'RA'; updateType(); $('context').value = 'They have enough work to keep them going.';
  } catch (e) { status(e.message, true); }
});
function base64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = () => reject(new Error('Could not read the audio file.')); reader.readAsDataURL(file);
  });
}
function word(parent, text, cls, title) {
  const el = document.createElement('span'); el.className = `word ${cls || ''}`; el.textContent = text;
  if (title) el.title = title; parent.append(el);
}
function render(data) {
  lastResult = data; $('empty').hidden = true; $('results').hidden = false; $('download').hidden = false;
  $('result-state').className = 'result-state' + (data.status === 'pending' ? ' pending' : '');
  const writingData = data.writing;
  const writing = ['SWT','WE','SST'].includes(data.type);
  const semantic = ['DI','RL','SGD','RTS','SWT','WE','SST'].includes(data.type);
  $('result-state').textContent = data.status === 'pending' ? `Partial result · pending: ${data.pending_traits.join(', ').replaceAll('_', ' ')}` : data.type === 'RA' ? 'Read Aloud · normalized 0–5 practice scale' : semantic ? (data.traits.form?.score === 0 ? 'Form check complete · response outside writing requirements' : 'Published rubric · local AI estimate') : data.audio?.proxy_scores_used ? 'Published rubric · experimental audio estimates' : 'Published item scoring rules';
  $('score-label').textContent = data.type === 'RA' ? 'Read Aloud practice score' : 'Question points';
  $('score').textContent = data.score == null ? 'Pending' : `${data.score} / ${data.max_score}`;
  $('trait-scale').textContent = data.type === 'RA' ? 'Normalized practice points' : 'Published rubric points';
  $('score-explanation').hidden = true;
  $('score-explanation').textContent = '';
  const textAnswer = TEXT_TYPES.has(data.type);
  const hasAudio = !!data.audio;
  if (writing) {
    $('score-label').textContent = 'Writing rubric points';
    $('score-explanation').hidden = false;
    $('score-explanation').textContent = `${writingData?.guidance || labels[data.type][2]} ${writingData?.limitation || 'The answer uses published item traits; this local assessment is not a calibrated Pearson score.'}`;
  }
  if (data.type === 'RA') {
    $('score-explanation').hidden = false;
    $('score-explanation').textContent = 'Content is normalized proportionally from credited prompt words to 0–5; pronunciation and oral fluency are each scored 0–5. This custom practice scale differs from Pearson’s prompt-length content points and calibrated 10–90 score.';
  }
  $('correctness-label').textContent = 'Rubric points %';
  $('correctness').textContent = data.correctness == null ? '—' : `${data.correctness.toFixed(1)}%`;
  $('length-label').textContent = textAnswer ? 'Word count' : hasAudio ? 'Audio length' : 'Answer';
  const responseWords=typeof data.response==='string' ? (data.response.match(/[\p{L}\p{N}_]+(?:['’][\p{L}\p{N}_]+)*/gu)||[]).length : 0;
  $('duration').textContent = writing && writingData ? writingData.word_count : textAnswer ? (data.details.word_count ?? responseWords) : hasAudio ? `${data.audio.duration_seconds.toFixed(1)}s` : '—';
  $('response-heading').textContent = hasAudio ? 'Transcript' : 'Your answer';
  const submitted = hasAudio ? data.audio.transcript : data.response;
  $('transcript').textContent = Array.isArray(submitted) ? submitted.join('\n') : submitted || 'No response.';
  $('audio-words').hidden = !hasAudio; $('audio-diagnostics').hidden = !hasAudio;
  $('traits').replaceChildren();
  const traitEntries = writing && writingData ? Object.keys(writingData.trait_maxima).map(name => [name, data.traits[name]]) : Object.entries(data.traits);
  for (const [name, trait] of traitEntries) {
    const row = document.createElement('div'); row.className = 'trait';
    const label = document.createElement('span'); label.textContent = name.replaceAll('_', ' ');
    const bar = document.createElement('div'); bar.className = 'bar';
    const fill = document.createElement('div'); fill.className = 'fill'; fill.style.width = `${trait?.max ? trait.score / trait.max * 100 : 0}%`; bar.append(fill);
    const points = document.createElement('span'); points.className = 'points'; points.textContent = trait ? `${trait.score} / ${trait.max}` : 'Pending'; row.append(label, bar, points); $('traits').append(row);
  }
  const skills = data.type === 'RA' ? data.skill_analysis : null;
  $('skill-analysis').hidden = !skills;
  $('skill-metrics').replaceChildren();
  $('skill-description').textContent = skills?.description || '';
  for (const [key, metric] of Object.entries(skills?.metrics || {})) {
    const row = document.createElement('div'); row.className = 'skill-row';
    const label = document.createElement('span'); label.textContent = metric.label;
    const bar = document.createElement('div'); bar.className = 'skill-bar';
    if (metric.percent != null) {
      bar.setAttribute('role', 'meter'); bar.setAttribute('aria-label', metric.label);
      bar.setAttribute('aria-valuemin', '0'); bar.setAttribute('aria-valuemax', '100'); bar.setAttribute('aria-valuenow', String(metric.percent));
    }
    const fill = document.createElement('div'); fill.style.width = `${metric.percent ?? 0}%`; bar.append(fill);
    const value = document.createElement('span'); value.className = 'skill-value';
    value.textContent = metric.percent == null ? 'N/A' : `${metric.percent}%`;
    const info = document.createElement('details'); info.className = 'skill-info';
    const toggle = document.createElement('summary'); toggle.textContent = '?'; toggle.setAttribute('aria-label', `About ${metric.label}`);
    const explanation = document.createElement('p'); explanation.textContent = metric.explanation;
    if (key === 'stress' && metric.coverage_percent != null) explanation.textContent += ` Assessed ${metric.coverage_percent}% of recognized words.`;
    if (key === 'speed' && metric.words_per_minute != null) explanation.textContent += ` Measured pace: ${metric.words_per_minute} words/min.`;
    info.append(toggle, explanation); row.append(label, bar, value, info); $('skill-metrics').append(row);
  }
  if (skills?.metrics.stress?.status === 'estimated') {
    const note = document.createElement('p'); note.className = 'help';
    note.textContent = 'Stress is an experimental emphasis-variation measure. Higher is not necessarily better; it does not check correct syllable stress.';
    $('skill-metrics').append(note);
  }
  $('words').replaceChildren();
  const timed = data.audio?.words || [];
  timed.forEach((item, i) => {
    const confidence = item.recognition_confidence * 100;
    word($('words'), item.word, confidence >= 80 ? 'green' : confidence >= 50 ? 'yellow' : 'red', `${confidence.toFixed(1)}% recognition confidence · ${item.start.toFixed(2)}–${item.end.toFixed(2)}s`);
    if (i + 1 < timed.length && timed[i + 1].start - item.end >= .5) { const pause = document.createElement('span'); pause.textContent = '/'; pause.className = 'pause'; $('words').append(pause); }
  });
  if (!timed.length) $('words').textContent = 'No recognized words.';
  $('comparison').replaceChildren();
  const compared = data.details.words || []; $('comparison-block').hidden = !compared.length;
  compared.forEach(item => word($('comparison'), item.word, item.status === 'correct' ? 'green' : item.status, item.status));
  $('pace').textContent = hasAudio ? `${data.audio.words_per_minute} words/min` : '';
  $('confidence').textContent = hasAudio ? `${(data.audio.recognition_confidence * 100).toFixed(1)}%` : '';
  $('feedback').replaceChildren();
  for (const message of data.feedback.length ? data.feedback : ['No additional feedback.']) { const li = document.createElement('li'); li.textContent = message; $('feedback').append(li); }
  $('json').textContent = JSON.stringify(data, null, 2);
}
$('form').addEventListener('submit', async e => {
  e.preventDefault(); if (busy) return;
  const type=$('type').value, audio=AUDIO_TYPES.has(type), typed=TEXT_TYPES.has(type), structured=STRUCTURED_TYPES.has(type);
  if (audio && !recording) { status('Choose a recording or try the sample audio first.', true); return; }
  if (typed && !$('writing-answer').value.trim()) { status('Enter your answer first.', true); return; }
  const keyLines=$('answer-key').value.split('\n').map(x=>x.trim()).filter(Boolean);
  const responseLines=$('student-answer').value.split('\n').map(x=>x.trim()).filter(Boolean);
  if (structured && !keyLines.length) { status('Enter the answer key first.', true); return; }
  if (structured && type!=='ASQ' && !responseLines.length) { status('Enter your answer first.', true); return; }
  const context = $('context').value.trim(); if (!context) { status('Enter the question context first.', true); return; }
  busy = true; $('submit').disabled = true; $('submit').textContent = 'Analyzing…'; $('sample').disabled = true;
  $('type').disabled = true;
  $('results').hidden = true; $('empty').hidden = false; $('download').hidden = true; lastResult = null;
  const semantic=['DI','RL','SGD','RTS','SWT','WE','SST'].includes(type);
  status(audio ? 'Processing audio locally. The first request can take longer while the models load.' : semantic ? 'Assessing your response with the local AI model. The first request can take longer while it loads.' : 'Checking your answer.');
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 240000);
  try {
    const question = { id: `ui-${Date.now()}`, type };
    if (['RA','RS','RL','SGD','SWT','SST','WFD','FIB','FIB_DD','FIB_L','RO'].includes(type)) question.reference = context;
    else question.prompt = context;
    if (structured) {
      question.correct = ARRAY_TYPES.has(type) ? keyLines : type==='ASQ' ? keyLines : keyLines[0];
      if (type!=='ASQ') question.response = ARRAY_TYPES.has(type) ? responseLines : responseLines[0] || '';
      const options=$('options').value.split('\n').map(x=>x.trim()).filter(Boolean);
      if (options.length) question.options=options;
    }
    const headers = { 'Content-Type': 'application/json' }; if ($('service-key').value) headers['X-Service-Key'] = $('service-key').value;
    if (typed) question.response = $('writing-answer').value.trim();
    const payload = audio ? { question, audio_base64: await base64(recording), allow_proxy_scores: $('proxy').checked } : question;
    const response = await fetch(audio ? '/v1/score-audio' : '/v1/score-question', { method: 'POST', headers, signal: controller.signal, body: JSON.stringify(payload) });
    const data = await response.json();
    if (!response.ok) {
      const detail = data.detail; throw new Error(Array.isArray(detail) ? detail.map(x => x.msg).join('; ') : detail || `Request failed (${response.status}).`);
    }
    render(data); status(data.status === 'pending' ? 'Assessment incomplete. See the feedback below for the reason.' : 'Analysis complete. You can download the full JSON response.');
  } catch (e) { status(e.name === 'AbortError' ? 'Analysis timed out after 4 minutes. Try again with a shorter response.' : e.message, true); }
  finally { clearTimeout(timer); busy = false; $('submit').disabled = false; $('submit').textContent = audio ? 'Analyze recording ↗' : structured ? 'Check answer ↗' : 'Analyze writing ↗'; $('sample').disabled = false; $('type').disabled = false; }
});
$('download').addEventListener('click', () => {
  if (!lastResult) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' }));
  const a = document.createElement('a'); a.href = url; a.download = `pte-${lastResult.id}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
fetch('/health').then(r => { if (!r.ok) throw new Error(); return r.json(); }).then(() => { $('connection').textContent = 'Service online'; $('connection').classList.add('online'); }).catch(() => { $('connection').textContent = 'Service unavailable'; });
