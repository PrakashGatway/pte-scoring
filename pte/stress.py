"""Experimental word-level prosodic variation; not lexical stress accuracy."""
import numpy as np


def estimate_stress(waveform, words, sample_rate=16000):
    result={'label':'Stress (estimate)', 'percent':None, 'status':'unavailable',
            'method':'acoustic_variation_v1', 'coverage_percent':0,
            'explanation':'Not enough reliable voiced words to estimate stress variation.'}
    if len(words)<4:
        return result
    try:
        import parselmouth
    except ImportError:
        result['explanation']='Install praat-parselmouth to enable the experimental stress estimate.'
        return result
    signal=np.asarray(waveform,dtype=np.float64)
    if not signal.size or not np.all(np.isfinite(signal)) or np.max(np.abs(signal))<0.001:
        return result
    # Normalize recording gain. Relative variation must not depend on mic volume.
    signal=signal/np.max(np.abs(signal))
    try:
        sound=parselmouth.Sound(signal,sampling_frequency=sample_rate)
        pitch=sound.to_pitch_ac(time_step=0.01,pitch_floor=60,pitch_ceiling=500)
    except parselmouth.PraatError:
        return result
    times=pitch.xs()
    frequencies=pitch.selected_array['frequency']
    strengths=pitch.selected_array['strength']
    measurements=[]
    for word in words:
        start=float(word.start); end=float(word.end)
        if not np.isfinite(start+end) or start<0 or end<=start or end>len(signal)/sample_rate+0.01:
            continue
        if float(word.probability)<0.5:
            continue
        frames=(times>=start)&(times<end)&(frequencies>0)&(strengths>=0.6)
        if np.count_nonzero(frames)<3:
            continue
        segment=signal[int(start*sample_rate):int(end*sample_rate)]
        if not segment.size:
            continue
        rms=float(np.sqrt(np.mean(segment**2)))
        if rms<0.001:
            continue
        measurements.append((float(np.median(frequencies[frames])),20*np.log10(rms),end-start))
    result['coverage_percent']=round(100*len(measurements)/len(words),1)
    result['assessed_words']=len(measurements)
    result['recognized_words']=len(words)
    if len(measurements)<4 or len(measurements)/len(words)<0.5:
        return result
    values=np.array(measurements)
    # Robust spreads across words; caps and weights are explicit unvalidated heuristics.
    pitch_spread=float(np.diff(np.percentile(12*np.log2(values[:,0]),[10,90]))[0])
    loudness_spread=float(np.diff(np.percentile(values[:,1],[10,90]))[0])
    duration_spread=float(np.diff(np.percentile(np.log2(values[:,2]),[10,90]))[0])
    variation=0.5*min(1,pitch_spread/6)+0.35*min(1,loudness_spread/12)+0.15*min(1,duration_spread/1.5)
    result.update(percent=round(100*variation,1),status='estimated',
        explanation='Experimental variation in word pitch, loudness and duration. Higher means more variation, not better or correct stress. Word length, intonation, noise and recording quality can affect it. Does not assess syllable stress or change your total.',
        features={'pitch_spread_semitones':round(pitch_spread,2),'loudness_spread_db':round(loudness_spread,2),
                  'duration_spread_log2':round(duration_spread,3)},
        weights={'pitch':0.5,'loudness':0.35,'duration':0.15},
        normalization_caps={'pitch_semitones':6,'loudness_db':12,'duration_log2':1.5})
    return result
