import os, secrets
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .models import Attempt, Question
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
def question_types(): return {'types':list(TARGETS),'aliases':ALIASES,'weights':WEIGHTS,'targets':TARGETS,'rubrics':RUBRICS}

@app.post('/v1/score-question',dependencies=[Depends(authorize)])
def question(body: Question): return score_question(body,assessor)

@app.post('/v1/score-attempt',dependencies=[Depends(authorize)])
def attempt(body: Attempt): return build_report(body,assessor)

@app.post('/v1/score-audio',dependencies=[Depends(authorize)])
def audio(body: AudioQuestion):
    try: return audio_processor.process(body,assessor)
    except ValueError as e: raise HTTPException(422,str(e)) from e
    except (ImportError,RuntimeError,OSError) as e: raise HTTPException(503,'Local audio model unavailable: '+type(e).__name__) from e
