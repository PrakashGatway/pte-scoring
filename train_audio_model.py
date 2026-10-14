"""Train on real human-rated feature rows; never treat synthetic fixtures as evidence."""
import argparse, json
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupShuffleSplit

FEATURES=['recognition_confidence','words_per_minute','pause_ratio','duration_seconds','rms']

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('dataset',help='JSONL: speaker_id, features object, pronunciation and oral_fluency (0–5)')
    parser.add_argument('--output',default='models/custom_audio_estimator.joblib')
    args=parser.parse_args()
    rows=[json.loads(s) for s in Path(args.dataset).read_text().splitlines() if s.strip()]
    groups=[r['speaker_id'] for r in rows]
    if len(rows)<100 or len(set(groups))<10: raise ValueError('At least 100 real rated recordings and 10 speakers required for this prototype split')
    x=np.array([[r['features'][f] for f in FEATURES] for r in rows],dtype=float)
    y=np.array([[r['pronunciation'],r['oral_fluency']] for r in rows],dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or np.any((y<0)|(y>5)): raise ValueError('Invalid feature values or 0–5 labels')
    train,test=next(GroupShuffleSplit(n_splits=1,test_size=0.2,random_state=42).split(x,y,groups))
    model=RandomForestRegressor(n_estimators=300,min_samples_leaf=5,random_state=42,n_jobs=-1)
    model.fit(x[train],y[train]); prediction=model.predict(x[test])
    metrics={'held_out_recordings':len(test),'held_out_speakers':len({groups[i] for i in test}),
        'mae_0_5':dict(zip(['pronunciation','oral_fluency'],mean_absolute_error(y[test],prediction,multioutput='raw_values').tolist())),
        'limitation':'Feature regression needs validation across accents, noise, devices and tasks; it is not a phoneme-level pronunciation model.'}
    target=Path(args.output); target.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump({'model':model,'features':FEATURES,'metrics':metrics},target)
    target.with_suffix('.metrics.json').write_text(json.dumps(metrics,indent=2))
    print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
