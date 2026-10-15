"""Local transcription and transparent, uncalibrated acoustic proxies."""
import base64, io, os, threading
from pathlib import Path
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from .models import Question, SpeechEvidence, SpeechWord
from .config import SPOKEN
from .engine import score_question
from .stress import estimate_stress

class AudioQuestion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question: Question
    audio_base64: str = Field(min_length=1,max_length=14000000)
    allow_proxy_scores: bool = False

def read_aloud_skills(confidence, fluency, pace, wpm, has_speech, enabled):
    """Expose measurable audio diagnostics without presenting ASR confidence as pronunciation."""
    available=has_speech
    reason='No speech detected.'
    def metric(label, value, explanation):
        return {'label':label, 'percent':round(min(100,max(0,value)),1) if available else None,
                'status':'estimated' if available else 'unavailable',
                'explanation':explanation if available else reason}
    return {'score_kind':'uncalibrated_audio_diagnostics',
            'description':'Audio diagnostics are experimental. Recognition confidence is not pronunciation accuracy, and only trusted acoustic evidence can complete spoken trait points.',
            'metrics':{
                'pronunciation_accuracy':{'label':'Pronunciation accuracy','percent':None,'status':'unavailable',
                    'explanation':'No phoneme-level pronunciation assessor is installed. Speech recognition confidence cannot measure pronunciation.'},
                'recognition_confidence':metric('Speech recognition confidence',100*confidence,
                    'How confidently the speech recognizer identified the words; this does not measure pronunciation quality.'),
                'fluency':metric('Fluency estimate',20*fluency,
                    'Timing estimate combining speaking pace and the proportion of pauses lasting at least 0.5 seconds.'),
                'stress':{'label':'Stress','percent':None,'status':'unavailable',
                    'explanation':'The current model does not assess syllable or word stress. A dedicated stress assessor is required.'},
                'speed':{**metric('Speed',100*pace,
                    'Pace fit: 100% at 100–230 words/min, reduced outside that range. This is a practice heuristic, not a Pearson target.'),
                    'words_per_minute':round(wpm,2) if has_speech else None}}}

class AudioProcessor:
    def __init__(self):
        self._model=None; self._lock=threading.Lock()
        self.model_name=os.getenv('PTE_WHISPER_MODEL','base.en')

    def process(self,body,assessor=None):
        if body.question.type not in SPOKEN|{'ASQ'}: raise ValueError('Audio response only allowed for speaking questions')
        from faster_whisper import WhisperModel
        from faster_whisper.audio import decode_audio
        try: data=base64.b64decode(body.audio_base64,validate=True)
        except Exception as e: raise ValueError('Invalid base64 audio') from e
        if len(data)>10000000: raise ValueError('Audio exceeds 10MB')
        try: waveform=decode_audio(io.BytesIO(data),sampling_rate=16000)
        except Exception as e: raise ValueError('Cannot decode audio') from e
        duration=len(waveform)/16000
        if not 0.25<=duration<=240: raise ValueError('Audio duration must be 0.25–240 seconds')
        # Silence is checked before inference to avoid hallucinated silent transcripts.
        rms=float(np.sqrt(np.mean(waveform**2)))
        if rms<0.001:
            transcript=''; words=[]
        else:
            with self._lock:
                if self._model is None:
                    self._model=WhisperModel(self.model_name,device='cpu',compute_type='int8',download_root=str(Path(__file__).resolve().parents[1]/'models'))
                segments,_=self._model.transcribe(waveform,language='en',word_timestamps=True,vad_filter=True,beam_size=5,condition_on_previous_text=False)
                segments=list(segments)
            transcript=' '.join(s.text.strip() for s in segments)
            words=[w for s in segments for w in (s.words or [])]
        gaps=[max(0,words[i+1].start-w.end) if i+1<len(words) else 0 for i,w in enumerate(words)]
        confidence=float(np.mean([w.probability for w in words])) if words else 0
        speech_span=max(0.1,words[-1].end-words[0].start) if words else duration
        wpm=len(words)*60/speech_span
        pause_ratio=sum(g for g in gaps if g>=0.5)/speech_span
        # ASR confidence is a recognition proxy, NOT phoneme-level pronunciation.
        pronunciation=round(5*confidence,2)
        pace=min(1,wpm/100,230/max(wpm,1))
        fluency=round(5*pace*max(0,1-pause_ratio),2) if words else 0
        q=body.question.model_copy(update={'response':transcript,'speech':None,'skipped':False})
        if body.allow_proxy_scores and q.type in SPOKEN:
            q.speech=SpeechEvidence(source='uncalibrated_local_asr_and_timing_proxy',pronunciation=pronunciation,oral_fluency=fluency,
                words=[SpeechWord(word=w.word.strip(),pronunciation=round(100*w.probability,2),pause_after_seconds=gaps[i]) for i,w in enumerate(words)])
        result=score_question(q,assessor)
        result['audio']={'transcript':transcript,'duration_seconds':round(duration,2),'rms':round(rms,5),
            'words_per_minute':round(wpm,2),'pause_ratio':round(pause_ratio,3),'recognition_confidence':round(confidence,3),
            'model':self.model_name,'proxy_scores_used':body.allow_proxy_scores,
            'words':[{'word':w.word.strip(),'start':w.start,'end':w.end,'recognition_confidence':w.probability} for w in words],
            'limitation':'Recognition confidence is not a pronunciation measurement; timing fluency and proxy scores need validation with human-rated recordings.'}
        if q.type=='RA':
            result['skill_analysis']=read_aloud_skills(confidence,fluency,pace,wpm,bool(words),body.allow_proxy_scores)
            stress=result['skill_analysis']['metrics']['stress']
            if words:
                result['skill_analysis']['metrics']['stress']=estimate_stress(waveform,words)
            else:
                stress['label']='Stress (estimate)'
        if body.allow_proxy_scores:
            result['method']='uncalibrated_audio_practice_proxy'
            result['feedback'].append('Audio trait scores and colors are uncalibrated ASR/timing proxies.')
        return result
