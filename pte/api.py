import os, secrets
from pathlib import Path
from types import SimpleNamespace
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .models import Attempt, Question, GREAnalyticalWritingRequest, ChatRequest
from .config import WEIGHTS, TARGETS, RUBRICS, ALIASES
from .engine import build_report, score_question
from .llm import OllamaAssessor
from .audio import AudioQuestion, AudioProcessor

app=FastAPI(title='PTE practice scoring service',version='1.0.0')
root=Path(__file__).resolve().parents[1]
app.mount('/ui',StaticFiles(directory=root/'ui'),name='ui')
assessor=OllamaAssessor()
audio_processor=AudioProcessor()

@app.get('/',include_in_schema=False)
def upload_ui(): return FileResponse(root/'ui/index.html')

@app.get('/sample-audio',include_in_schema=False)
def sample_audio(): return FileResponse(root/'examples/read-aloud.wav',media_type='audio/wav')

def authorize(x_service_key: str | None = Header(default=None)):
    key=os.getenv('PTE_SERVICE_KEY')
    if key and not secrets.compare_digest(key,x_service_key or ''): raise HTTPException(401,'Invalid service key')

@app.get('/health')
def health():
    return {'status':'ok','llm_enabled':assessor.enabled,'llm_provider':assessor.provider,'llm_loaded':assessor._local is not None,'whisper_model':audio_processor.model_name,'speech_assessor':'local_uncalibrated_proxy_or_external_evidence'}

@app.get('/v1/question-types',dependencies=[Depends(authorize)])
def question_types(): return {'types':list(TARGETS),'aliases':ALIASES,'weights':WEIGHTS,'targets':TARGETS,'rubrics':RUBRICS,
    'scoring_standard':'Pearson PTE Academic published item-level scoring rules where available',
    'score_limitations':'This service does not reproduce Pearson’s proprietary calibrated 10–90 score engine. Local AI and acoustic marks are estimates; attempt weights and targets are practice assumptions.'}

@app.post('/v1/score-question',dependencies=[Depends(authorize)])
def question(body: Question): return score_question(body,assessor)

@app.post('/v1/score-attempt',dependencies=[Depends(authorize)])
def attempt(body: Attempt): return build_report(body,assessor)

@app.post('/v1/gre/analytical-writing',dependencies=[Depends(authorize)])
def gre_analytical_writing(body: GREAnalyticalWritingRequest):
    if not body.response.strip():
        return {'status':'no_score','score':None,'scale':'0-6 in 0.5 increments','feedback':['No response was provided.']}
    question=SimpleNamespace(type='GRE_AW',prompt=body.prompt + ('\n\nTask instructions:\n'+body.instructions if body.instructions else ''),
        reference='',key_points=[],response=body.response)
    try:
        assessment=assessor.assess(question,{'overall_quality':12})
        band=assessment['traits']['overall_quality']
        return {'status':'scored','question_type':'GRE Analyze an Issue','score':band/2,'max_score':6,
            'score_scale':'0-6 in 0.5 increments','feedback':assessment['feedback'],
            'limitation':'Practice estimate from a local language model; not an official GRE score.'}
    except Exception as e:
        raise HTTPException(503,'GRE writing assessor unavailable: '+type(e).__name__) from e

@app.post('/v1/chat',dependencies=[Depends(authorize)])
def chat(body: ChatRequest):
    try:
        answer=assessor.chat(body.message,[turn.model_dump() for turn in body.history],body.prompt)
        return {'answer':answer,'provider':assessor.provider,'model':assessor.model}
    except Exception as e:
        raise HTTPException(503,'Chat model unavailable: '+type(e).__name__) from e

@app.post('/v1/score-audio',dependencies=[Depends(authorize)])
def audio(body: AudioQuestion):
    try: return audio_processor.process(body,assessor)
    except ValueError as e: raise HTTPException(422,str(e)) from e
    except (ImportError,RuntimeError,OSError) as e: raise HTTPException(503,'Local audio model unavailable: '+type(e).__name__) from e
