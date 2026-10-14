import base64, io, wave
import pytest
from fastapi.testclient import TestClient
from pte.models import Question, Attempt
from pte.engine import score_question, build_report
from pte.config import TARGETS, RUBRICS, SPOKEN
from pte.llm import AssessmentUnavailable
from pte.api import app

class NoLLM:
    def assess(self,*args): raise AssessmentUnavailable('Test LLM disabled')
class FullLLM:
    def assess(self,q,traits): return {'traits':traits,'feedback':['Test fixture, not real inference.']}

def q(t,**kw): return Question(id='test',type=t,**kw)

@pytest.mark.parametrize('t',['MCM_R','MCM_L','HIW'])
def test_negative_marking(t):
    r=score_question(q(t,correct=['a','b'],response=['a','x']))
    assert r['score']==0 and r['details']['penalty']==1

@pytest.mark.parametrize('response,expected',[(['1','2','4','3','5'],4),(['1','2','3','4','5'],1),(['4','5','3','1','2'],1),(['1','2','5','3','4'],1)])
def test_order_pairs(response,expected):
    assert score_question(q('RO',correct=['1','2','4','3','5'],response=response))['score']==expected

def test_dictation_duplicate_and_extra():
    r=score_question(q('WFD',reference='the cat and the dog',response='the cat the the extra'))
    assert r['score']==3 and r['max_score']==5
    assert sum(x['status']=='extra' for x in r['details']['words'])==2

@pytest.mark.parametrize('t',['FIB','FIB_DD','FIB_L'])
def test_blanks(t):
    assert score_question(q(t,correct=['cat','dog'],response=['CAT']))['score']==1

def test_read_aloud_insertions_and_pending_audio():
    r=score_question(q('RA',reference='the cat sat',response='the big cat sat'))
    assert r['traits']['content']['score']==2 and r['correctness'] is None
    assert 'pronunciation' in r['pending_traits']

def test_repeat_sentence_partial():
    r=score_question(q('RS',reference='they have enough work to keep them going',response='they have enough work'))
    assert r['traits']['content']['score']==2

def test_invalid_form_no_llm():
    r=score_question(q('WE',prompt='Discuss education',response='too short'),NoLLM())
    assert r['score']==0 and r['status']=='scored'

def test_llm_unavailable_not_fake_score():
    r=score_question(q('DI',prompt='A chart of rising sales',response='The sales increase.'),NoLLM())
    assert r['status']=='pending' and r['score'] is None

def test_partial_attempt_never_full_score():
    a=Attempt(attempt_id='a',questions=[q('WFD',reference='a cat',response='a cat')])
    r=build_report(a,NoLLM())
    assert r['report']['overall']['practice_score_10_90'] is None
    assert r['report']['writing']['partial_correctness']==100

def test_validation():
    with pytest.raises(ValueError): q('RO',correct=['a','b'],response=['a','a'])
    with pytest.raises(ValueError): q('MCS_R',correct='a',response='unknown',options=['a','b'])
    with pytest.raises(ValueError): q('WFD',reference='',response='hello')

def test_targets_and_duplicate_ids():
    with pytest.raises(ValueError): Attempt(attempt_id='a',questions=[q('ASQ',correct='a',response='a')],targets={'ASQ':101})
    with pytest.raises(ValueError): Attempt(attempt_id='a',questions=[q('ASQ',correct='a',response='a')]*2)

def test_all_22_types_and_independent_overall():
    questions=[]
    for t in TARGETS:
        if t in {'FIB','FIB_DD','FIB_L','MCM_R','MCM_L','HIW'}: item=q(t,correct=['a','b'],response=['a','b'])
        elif t=='RO': item=q(t,correct=['1','2','3'],response=['1','2','3'])
        elif t in {'ASQ','MCS_R','MCS_L','HCS','SMW'}: item=q(t,correct='a',response='a')
        elif t in {'RA','RS','WFD'}: item=q(t,reference='they have work',response='they have work')
        elif t=='WE': item=q(t,prompt='Discuss work',response=' '.join(['Work is useful.']*70))
        elif t=='SWT': item=q(t,reference='Work helps people',response='Work helps people to earn money and learn new skills.')
        elif t=='SST': item=q(t,reference='Work helps people',response=' '.join(['Work is useful.']*20))
        else: item=q(t,prompt='Discuss work',response='Work is useful.')
        item.id=t
        if t in SPOKEN:
            from pte.models import SpeechEvidence
            item.speech=SpeechEvidence(source='test_fixture',pronunciation=5,oral_fluency=5)
        if t=='DI': item.skipped=True
        questions.append(item)
    report=build_report(Attempt(attempt_id='all',questions=questions),FullLLM())
    assert len(report['questions'])==22
    assert all(r['status']=='scored' for r in report['questions'])
    assert all(m['complete'] for m in report['report'].values())
    overall=report['report']['overall']['correctness']
    average=sum(report['report'][s]['correctness'] for s in ['speaking','writing','reading','listening'])/4
    assert abs(overall-average)>1

def test_api_auth_validation(monkeypatch):
    client=TestClient(app)
    monkeypatch.setenv('PTE_SERVICE_KEY','test-secret')
    assert client.post('/v1/score-question',json={'id':'a','type':'bad'}).status_code==401
    assert client.post('/v1/score-question',headers={'X-Service-Key':'test-secret'},json={'id':'a','type':'bad'}).status_code==422

def test_silent_audio_no_hallucination():
    client=TestClient(app); stream=io.BytesIO()
    with wave.open(stream,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b'\0\0'*16000)
    result=client.post('/v1/score-audio',json={'question':{'id':'a','type':'RA','reference':'Hello world'},'audio_base64':base64.b64encode(stream.getvalue()).decode()})
    assert result.status_code==200
    assert result.json()['audio']['transcript']=='' and result.json()['score']==0

def test_invalid_audio():
    client=TestClient(app)
    assert client.post('/v1/score-audio',json={'question':{'id':'a','type':'RA','reference':'Hi'},'audio_base64':'invalid!'}).status_code==422
