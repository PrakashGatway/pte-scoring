export class PteClient {
  constructor({ baseUrl = process.env.PTE_SERVICE_URL || 'http://127.0.0.1:8765', serviceKey = process.env.PTE_SERVICE_KEY, timeoutMs = 180000 } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); this.serviceKey = serviceKey; this.timeoutMs = timeoutMs;
  }
  async request(path, body) {
    const response = await fetch(this.baseUrl + path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { 'Content-Type': 'application/json', ...(this.serviceKey ? { 'X-Service-Key': this.serviceKey } : {}) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: AbortSignal.timeout(this.timeoutMs),
    });
    const data = await response.json();
    if (!response.ok) { const error = new Error(`PTE service returned ${response.status}`); error.status = response.status; error.details = data; throw error; }
    return data;
  }
  scoreQuestion(question) { return this.request('/v1/score-question', question); }
  scoreAudio(question, audioBuffer, { allowProxyScores = false } = {}) {
    return this.request('/v1/score-audio', { question, audio_base64: audioBuffer.toString('base64'), allow_proxy_scores: allowProxyScores });
  }
  scoreAttempt(attempt) { return this.request('/v1/score-attempt', attempt); }
  questionTypes() { return this.request('/v1/question-types'); }
}
