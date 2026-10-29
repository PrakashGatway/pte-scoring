// Copy this file into your backend and adjust the two model import paths.
// Requires Node 18+, node-cron, and the local PTE scoring service.
import cron from 'node-cron';
import { TestAttempt } from '../models/GGSschema/attemptSchema.js';
import { Question } from '../models/GGSschema/questionSchema.js';

const API = process.env.PTE_SERVICE_URL || 'http://127.0.0.1:8000';
const AUDIO_BASE = process.env.PTE_AUDIO_BASE_URL || 'https://prep.sfo3.cdn.digitaloceanspaces.com';
const TYPES = {
  read_aloud:'RA', repeat_sentence:'RS', describe_image:'DI', retell_lesson:'RL',
  short_answer:'ASQ', summarize_group_discussions:'SGD', pte_situational:'RTS',
  pte_summarize_writing:'SWT', essay:'WE', pte_writing:'WE',
  pte_summarize_spoken:'SST', pte_summarize_listening:'SST', pte_writing_listening:'WFD',
  pte_fill_in_blanks:'FIB', pte_fill_drag:'FIB_DD', pte_reorder:'RO',
  pte_mcq_multiple:'MCM_R', pte_mcq_single:'MCS_R', pte_fill_listening:'FIB_L',
  pte_mcq_multiple_listening:'MCM_L', pte_mcq_single_listening:'MCS_L',
  pte_mcq_missing_single_listening:'SMW', pte_highlight:'HIW',
};
const SPEAKING = new Set(['RA','RS','DI','RL','SGD','RTS']);

async function pte(path, body) {
  const headers = { 'content-type':'application/json' };
  if (process.env.PTE_SERVICE_KEY) headers['x-service-key'] = process.env.PTE_SERVICE_KEY;
  const res = await fetch(`${API.replace(/\/$/, '')}${path}`, {
    method:'POST', headers, body:JSON.stringify(body), signal:AbortSignal.timeout(240_000),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(`PTE API ${res.status}: ${JSON.stringify(data)}`);
  return data;
}

const asText = value => Array.isArray(value) ? value.join(' | ') : String(value || '').trim();
const split = value => Array.isArray(value) ? value.map(String) : asText(value).split(/\s*(?:\|\||\n|\|)\s*/).filter(Boolean);
const optionId = (option, i) => String(option._id || option.id || option.label || i);

async function makeQuestion(answer, doc) {
  const type = TYPES[doc.questionType];
  if (!type) return null;
  const id = String(answer._id || doc._id);
  const options = doc.options || [];
  const correctOptions = options.filter(x => x.isCorrect);
  const responseOptions = (answer.answerOptionIndexes || []).map(i => optionId(options[i] || {}, i));
  const response = options.length
    ? (['MCM_R','MCM_L'].includes(type) ? responseOptions : (responseOptions[0] || ''))
    : (['FIB','FIB_DD','FIB_L','RO','MCM_R','MCM_L','HIW'].includes(type)
      ? split(answer.answerText) : asText(answer.answerText));
  let correct = doc.correctAnswerText || doc.typeSpecific?.listeningText || '';
  if (correctOptions.length) {
    const ids = correctOptions.map(optionId);
    correct = ['MCM_R','MCM_L'].includes(type) ? ids : ids[0];
  } else if (['FIB','FIB_DD','FIB_L','RO','MCM_R','MCM_L','HIW'].includes(type)) correct = split(correct);
  else if (options.length && correct) {
    const match = options.findIndex((o, i) => [optionId(o, i), o.label, o.text].includes(String(correct)));
    if (match >= 0) correct = optionId(options[match], match);
  }

  const prompt = [doc.stimulus, doc.questionText].filter(Boolean).join('\n\n');
  const reference = type === 'RA'
    ? (doc.correctAnswerText || doc.stimulus || doc.questionText)
    : (doc.correctAnswerText || doc.typeSpecific?.listeningText || doc.questionText || doc.stimulus);
  const question = {
    id, type, prompt, reference:asText(reference), response,
    ...(options.length ? { options:options.map(optionId) } : {}),
    ...(correct && (Array.isArray(correct) ? correct.length : true) ? { correct } : {}),
    ...(doc.typeSpecific?.keyPoints ? { key_points:doc.typeSpecific.keyPoints } : {}),
  };

  if (SPEAKING.has(type)) {
    const stored = asText(answer.answerText);
    const url = /^https?:\/\//.test(stored) ? stored : `${AUDIO_BASE.replace(/\/$/, '')}/${stored.replace(/^\/+/, '')}`;
    const audioRes = await fetch(url);
    if (!audioRes.ok) throw new Error(`Audio download failed: ${audioRes.status}`);
    const audio = Buffer.from(await audioRes.arrayBuffer());
    if (!audio.length || audio.length > 10_000_000) throw new Error('Audio is empty or exceeds 10 MB');
    const scored = await pte('/v1/score-audio', {
      question:{ id, type, prompt, reference:question.reference },
      audio_base64:audio.toString('base64'), allow_proxy_scores:true,
    });
    question.response = scored.audio?.transcript || '';
    const traits = scored.traits || {};
    if (traits.pronunciation && traits.oral_fluency) question.speech = {
      source:'uncalibrated_local_asr_and_timing_proxy',
      pronunciation:traits.pronunciation.score,
      oral_fluency:traits.oral_fluency.score,
      words:(scored.details?.pronunciation_words || []).map(w => ({
        word:w.word, pronunciation:w.score, pause_after_seconds:w.pause_seconds || 0,
      })),
    };
  }
  return question;
}

async function scoreAttempt(attempt) {
  const questions = [];
  const answersById = new Map();
  for (const section of attempt.sections || []) for (const answer of section.questions || []) {
    if (!answer.isAnswered) continue;
    const doc = await Question.findById(answer.question).lean();
    if (!doc) continue;
    const question = await makeQuestion(answer, doc);
    if (!question) continue; // This service scores PTE types, not GRE/GMAT/SAT.
    questions.push(question);
    answersById.set(question.id, { answer, doc });
  }
  if (!questions.length) return false;

  const report = await pte('/v1/score-attempt', { attempt_id:String(attempt._id), questions });
  for (const result of report.questions) {
    const row = answersById.get(result.id);
    if (!row) continue;
    row.answer.isCorrect = result.status === 'scored' && result.correctness >= 99.999;
    row.answer.marksAwarded = result.status === 'scored'
      ? Number(row.doc.marks ?? 1) * Number(result.correctness || 0) / 100 : 0;
    row.answer.evaluationMeta = {
      transcript:result.response, accuracy:result.correctness,
      scoreInfo:{ score:result.score, max_score:result.max_score, status:result.status },
      traitScores:result.traits, feedback:result.feedback, details:result.details,
      evaluatedAt:new Date(), scoringSource:'local_pte_service',
    };
  }
  attempt.pteScoreReport = report; // Add pteScoreReport: Schema.Types.Mixed to attemptSchema.
  attempt.overallStats = {
    ...(attempt.overallStats?.toObject?.() || attempt.overallStats || {}),
    pteOverallCorrectness:report.report?.overall?.correctness ?? null,
    ptePartialCorrectness:report.report?.overall?.partial_correctness ?? null,
    pteCoverage:report.report?.overall?.coverage_percent ?? 0,
  };
  attempt.analysisStatus = true;
  await attempt.save();
  console.log(`[PTE] ${attempt._id}: overall ${report.report?.overall?.correctness ?? 'pending'}%`);
  return true;
}

let busy = false;
cron.schedule(process.env.PTE_SCORE_CRON || '*/1 * * * *', async () => {
  if (busy) return;
  busy = true;
  try {
    const attempts = await TestAttempt.find({ status:'completed', analysisStatus:{ $ne:true } })
      .sort({ createdAt:1 }).limit(Number(process.env.PTE_SCORE_BATCH_SIZE || 5));
    for (const attempt of attempts) {
      try { await scoreAttempt(attempt); }
      catch (error) { console.error(`[PTE] ${attempt._id}: ${error.message}`); }
    }
  } catch (error) { console.error('[PTE] Cron error:', error); }
  finally { busy = false; }
});
