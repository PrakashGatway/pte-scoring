import re
from collections import Counter
from difflib import SequenceMatcher
from .config import RUBRICS, WEIGHTS, TARGETS, SECTIONS, SPOKEN
from .llm import OllamaAssessor, AssessmentUnavailable

def tokens(text):
    return re.findall(r"[\w]+(?:['’][\w]+)*",text.casefold())

def alignment(reference,response):
    a,b=tokens(reference),tokens(response)
    rows=[]; errors=0; matches=0
    # SequenceMatcher supplies ordered feedback; autojunk disabled for repeated words.
    for tag,i,j,k,l in SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if tag=='equal':
            matches+=j-i
            rows.extend({'word':w,'status':'correct'} for w in a[i:j])
        else:
            errors+=max(j-i,l-k)
            rows.extend({'word':w,'status':'missed','color':'red'} for w in a[i:j])
            rows.extend({'word':w,'status':'extra','strikethrough':True} for w in b[k:l])
    # Exact edit distance for RA scoring, independent of display alignment.
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1): current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=current
    return rows,previous[-1],matches

def form_score(t,text):
    n=len(tokens(text)); punct=bool(re.search(r'[.!?]',text)); allcaps=text.isupper()
    if t=='SWT':
        sentences=[s for s in re.split(r'[.!?]+(?:\s+|$)',text.strip()) if s.strip()]
        return int(5<=n<=75 and len(sentences)==1 and punct and not allcaps)
    sentences=[s.strip() for s in re.split(r'[.!?]+',text) if s.strip()]
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    bullet_only=bool(lines) and all(line.startswith(('-', '*','•')) for line in lines)
    very_short_only=bool(sentences) and all(len(tokens(s))<=4 for s in sentences)
    if allcaps or not punct or bullet_only or very_short_only: return 0
    if t=='WE': return 2 if 200<=n<=300 else 1 if 120<=n<=380 else 0
    return 2 if 50<=n<=70 else 1 if 40<=n<=100 else 0

def score_question(q,assessor=None):
    assessor=assessor or OllamaAssessor(); t=q.type
    traits={}; details={}; feedback=[]; pending=[]; method='normalized_read_aloud_practice_scale' if t=='RA' else 'answer_key'
    def trait(name,value,maximum): traits[name]={'score':value,'max':maximum}
    empty=not q.response or (isinstance(q.response,str) and not q.response.strip())
    maxima=RUBRICS.get(t,{'content':len(tokens(q.reference)),'pronunciation':5,'oral_fluency':5} if t=='RA' else {})
    if q.skipped or empty:
        if maxima:
            for name,m in maxima.items(): trait(name,0,m)
        else: trait('content',0,len(q.correct) if isinstance(q.correct,list) and t not in {'ASQ','RO'} else len(q.correct)-1 if t=='RO' else len(tokens(q.reference)) if t=='WFD' else 1)
        feedback=['Question skipped or no response provided.']
    elif t in {'MCM_R','MCM_L','HIW'}:
        good=set(q.response)&set(q.correct); bad=set(q.response)-set(q.correct)
        trait('content',max(0,len(good)-len(bad)),len(q.correct))
        details={'correct_selected':sorted(good),'incorrect_selected':sorted(bad),'missed':sorted(set(q.correct)-set(q.response)),'penalty':len(bad)}
    elif t in {'MCS_R','MCS_L','HCS','SMW','ASQ'}:
        keys=q.correct if isinstance(q.correct,list) else [q.correct]
        normalize=(lambda s:' '.join(tokens(s))) if t=='ASQ' else (lambda s:s)
        trait('vocabulary' if t=='ASQ' else 'content',int(normalize(q.response) in [normalize(s) for s in keys]),1)
    elif t in {'FIB','FIB_DD','FIB_L'}:
        details['blanks']=[{'index':i,'expected':w,'actual':q.response[i] if i<len(q.response) else '',
            'correct':i<len(q.response) and w.strip().casefold()==q.response[i].strip().casefold()} for i,w in enumerate(q.correct)]
        trait('content',sum(x['correct'] for x in details['blanks']),len(q.correct))
    elif t=='RO':
        pairs=set(zip(q.correct,q.correct[1:])); actual=list(zip(q.response,q.response[1:]))
        details['pairs']=[{'pair':list(p),'correct':p in pairs} for p in actual]
        trait('content',sum(p in pairs for p in actual),len(q.correct)-1)
    elif t=='WFD':
        remaining=Counter(tokens(q.reference)); rows=[]; score=0
        for w in tokens(q.response):
            correct=remaining[w]>0
            if correct: remaining[w]-=1; score+=1
            rows.append({'word':w,'status':'correct' if correct else 'extra','strikethrough':not correct})
        rows.extend({'word':w,'status':'missed','color':'red'} for w,n in remaining.items() for _ in range(n))
        details['words']=rows; trait('content',score,len(tokens(q.reference)))
    else:
        method='published_item_rubric_with_local_ai_estimates'
        if t=='RA': method='normalized_read_aloud_practice_scale'
        if t in {'RA','RS'}:
            rows,errors,matches=alignment(q.reference,q.response)
            details={'words':rows,'reference_word_count':len(tokens(q.reference)),'response_word_count':len(tokens(q.response)),'edit_errors':errors}
            if t=='RA':
                prompt_words=len(tokens(q.reference))
                credited_words=max(0,prompt_words-errors)
                content_score=round(5*credited_words/prompt_words,2) if prompt_words else 0
                trait('content',content_score,maxima['content'])
                details.update({'content_credited_words':credited_words,'content_raw_max':prompt_words,
                                'content_scale':'proportional_0_to_5_practice_score'})
            else:
                ratio=matches/len(tokens(q.reference))
                trait('content',3 if tokens(q.reference)==tokens(q.response) else 2 if ratio>=0.5 else 1 if matches else 0,3)
        if 'form' in maxima:
            trait('form',form_score(t,q.response),maxima['form'])
            details['word_count']=len(tokens(q.response))
        needed={k:m for k,m in maxima.items() if k not in traits and k not in {'pronunciation','oral_fluency'}}
        if traits.get('form',{}).get('score')==0:
            feedback.append('Form is zero. The response receives no points.')
            for k,m in maxima.items(): trait(k,0,m)
        else:
            if needed:
                try:
                    assessment=assessor.assess(q,needed)
                    for k,m in needed.items():
                        v=assessment['traits'][k]
                        if type(v) is not int or not 0<=v<=m: raise AssessmentUnavailable('Invalid trait score')
                        trait(k,v,m)
                    feedback.extend(assessment['feedback'])
                except AssessmentUnavailable as e:
                    pending.extend(needed); feedback.append(str(e))
            if t in SPOKEN:
                for name in ('pronunciation','oral_fluency'):
                    if q.speech: trait(name,getattr(q.speech,name),5)
                    else: pending.append(name)
                if q.speech:
                    details['speech_source']=q.speech.source
                    details['pronunciation_words']=[{'word':w.word,'score':w.pronunciation,'color':'green' if w.pronunciation>=80 else 'yellow' if w.pronunciation>=50 else 'red','pause_after': '/' if w.pause_after_seconds>=0.5 else '', 'pause_seconds':w.pause_after_seconds} for w in q.speech.words]
                else: feedback.append('Audio pronunciation and fluency evidence required; transcript accuracy is not pronunciation.')
            if traits.get('content',{}).get('score')==0:
                for k,m in maxima.items(): trait(k,0,m)
                pending=[]; feedback.append('Content is zero. The response receives no points.')
    maximum=sum(x['max'] for x in traits.values())
    total=sum(x['score'] for x in traits.values())
    correctness=round(100*total/maximum,4) if maximum and not pending else None
    result={'id':q.id,'type':t,'section':SECTIONS[t],'status':'pending' if pending else 'scored',
       'method':method,'score':round(total,4) if not pending else None,'max_score':sum(maxima.values()) if maxima else maximum,
       'correctness':correctness,'traits':traits,'pending_traits':pending,'details':details,'feedback':feedback,'response':q.response}
    if t in {'SWT','WE','SST'}:
        result['writing']={'response':q.response,'word_count':len(tokens(q.response)),
            'guidance':'Write one sentence of 5–75 words.' if t=='SWT' else 'Write an essay of 200–300 words.' if t=='WE' else 'Write a summary of 50–70 words.',
            'trait_maxima':maxima,'score_kind':'practice_estimate_using_published_rubric',
            'limitation':'Raw trait points follow Pearson’s published task rubric. This local AI estimate is not a calibrated Pearson score.'}
    return result

def build_report(attempt,assessor=None,weights=None):
    results=[score_question(q,assessor) for q in attempt.questions]
    groups={t:[r for r in results if r['type']==t] for t in TARGETS}
    reports={}
    for module,table in (weights or WEIGHTS).items():
        rows=[]; numerator=0; coverage=0; partial=0; partial_weight=0
        for t,weight in table.items():
            items=groups[t]; finished=[r for r in items if r['status']=='scored']
            complete=bool(items) and len(finished)==len(items)
            pct=sum(r['correctness'] for r in finished)/len(finished) if finished else None
            target=attempt.targets.get(t,TARGETS[t])
            if complete: numerator+=pct*weight; coverage+=weight
            if pct is not None: partial+=pct*weight; partial_weight+=weight
            rows.append({'section':SECTIONS[t],'item':t,'contribute':weight,'my_correctness':round(pct,2) if complete else None,
                'target':target,'status':('Good' if pct>=target else 'Bad') if complete else 'Pending' if items else 'Not attempted',
                'question_count':len(items),'scored_count':len(finished)})
        complete=abs(coverage-sum(table.values()))<1e-8
        pct=numerator/sum(table.values()) if complete else None
        reports[module]={'rows':rows,'complete':complete,'weight_total':sum(table.values()),
           'coverage_percent':round(100*coverage/sum(table.values()),2),
           'correctness':round(pct,2) if pct is not None else None,
           'partial_correctness':round(partial/partial_weight,2) if partial_weight else None}
    return {'attempt_id':attempt.attempt_id,'score_kind':'practice_weighted_correctness_not_pearson_score',
       'report':reports,'questions':results,'assumptions':[
       'Module and overall weights come from the supplied deck, not Pearson’s scoring engine. Reading totals 101%; normalized by its weight total.',
       'Overall is calculated independently from question-type weights, never averaged from modules.',
       'Three <1% overall weights use 0.5%. Overall weights are normalized; these are approximate.',
       'No 10–90 score is derived: Pearson’s calibrated reporting model is proprietary and cannot be reconstructed from a local rubric.',
       'Type correctness averages per-question percentages. Missing types and pending assessments prevent a complete score.',
       'Speech evidence must come from a trusted acoustic assessor, not the learner client.']}
