from types import SimpleNamespace
import numpy as np
import pytest
from pte.stress import estimate_stress


def recording(vary=False):
    words=[]; segments=[]; start=0
    for i in range(8):
        duration=0.4
        time=np.arange(int(16000*duration))/16000
        frequency=(120+25*i) if vary else 180
        amplitude=(0.15+0.08*i) if vary else 0.5
        # Harmonics make the generated signal a repeatable voiced test fixture.
        samples=amplitude*(np.sin(2*np.pi*frequency*time)+0.2*np.sin(4*np.pi*frequency*time))
        segments.append(samples)
        words.append(SimpleNamespace(word=f'word{i}',start=start,end=start+duration,probability=.95))
        start+=duration
    return np.concatenate(segments),words


def test_stress_variation_and_gain_invariance():
    steady,words=recording()
    expressive,_=recording(True)
    flat=estimate_stress(steady,words)
    varied=estimate_stress(expressive,words)
    quiet=estimate_stress(expressive*.1,words)
    assert flat['status']==varied['status']=='estimated'
    assert 0<=flat['percent']<varied['percent']<=100
    assert varied['percent']==pytest.approx(quiet['percent'],abs=.2)
    assert varied['coverage_percent']==100
    assert 'not better' in varied['explanation']


def test_stress_insufficient_speech_and_unreliable_timing():
    signal,words=recording()
    for wave,items in [(signal,words[:3]),(np.zeros_like(signal),words)]:
        assert estimate_stress(wave,items)['percent'] is None
    for item in words:
        item.probability=.1
    assert estimate_stress(signal,words)['percent'] is None
    for item in words:
        item.probability=.95
        item.end=item.start
    assert estimate_stress(signal,words)['percent'] is None


def test_stress_noise_is_unavailable():
    signal,words=recording()
    noise=np.random.default_rng(7).normal(0,.1,len(signal))
    assert estimate_stress(noise,words)['percent'] is None


def test_audio_stress_integration_and_opt_out(monkeypatch):
    import base64,io,wave
    from pte.audio import AudioProcessor,AudioQuestion
    signal,words=recording(True)
    stream=io.BytesIO()
    with wave.open(stream,'wb') as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
        audio.writeframes((signal*16000).astype('<i2').tobytes())
    processor=AudioProcessor()
    processor._model=SimpleNamespace(transcribe=lambda *a,**kw:([SimpleNamespace(text='one two three four five six seven eight',words=words)],None))
    body=AudioQuestion(question={'id':'stress','type':'RA','reference':'one two three four five six seven eight'},
        audio_base64=base64.b64encode(stream.getvalue()).decode(),allow_proxy_scores=True)
    result=processor.process(body)
    assert result['skill_analysis']['metrics']['stress']['status']=='estimated'
    original_total=result['read_aloud_score']['total']
    monkeypatch.setattr('pte.audio.estimate_stress',lambda *a: {'percent':0,'status':'estimated'})
    assert processor.process(body)['read_aloud_score']['total']==original_total
    def forbidden(*args): raise AssertionError('Stress estimator called when disabled')
    monkeypatch.setattr('pte.audio.estimate_stress',forbidden)
    body.allow_proxy_scores=False
    result=processor.process(body)
    assert result['skill_analysis']['metrics']['stress']['percent'] is None
    assert result['read_aloud_score']['total'] is None
