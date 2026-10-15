"""Small semantic smoke check, NOT a PTE accuracy benchmark. Uses real inference."""
import json,time,os
from pathlib import Path
from pte.engine import score_question
from pte.models import Question
from pte.llm import LocalAssessor

SOURCE=('Bioluminescence is the ability of certain animals to produce and emit light. '
        'Fireflies use a chemical reaction to attract mates. Marine animals including jellyfish, '
        'anglerfish and plankton use light for camouflage and survival in deep water. '
        'Squids use flashes to communicate and deter predators. Scientists study light-producing '
        'enzymes and molecules for applications in biotechnology, medicine and genetics.')
GOOD=('Bioluminescence is the natural ability of certain animals to produce light, which helps them '
      'attract mates, communicate, defend against predators, and survive in deep oceans, while '
      'scientific research on this phenomenon has also contributed to advancements in medicine, genetics, and biotechnology.')

def main():
    assessor=LocalAssessor()
    supplied=Path('examples/bioluminescence-writing.json')
    example=json.loads(supplied.read_text(encoding='utf-8')) if supplied.exists() else {'source':SOURCE,'response':GOOD}
    cases=[('relevant',example['source'],example['response'],lambda r:r['traits'].get('content',{}).get('score',-1)>=3),
           ('unrelated',SOURCE,'Football is a popular sport and bananas are delicious fruits eaten by people around the world.',lambda r:r['traits'].get('content',{}).get('score',-1)==0),
           ('contradiction','Libraries provide free books and internet access to support students and help communities learn.',
            'Libraries never provide books or internet access and prevent students from learning.',lambda r:r['traits'].get('content',{}).get('score',-1)==0),
           ('paraphrase','Regular physical activity improves cardiovascular health and reduces the risk of disease, while adequate rest supports recovery.',
            'Exercise protects the heart and lowers illness risk, while sufficient sleep helps the body recover.',lambda r:r['traits'].get('content',{}).get('score',-1)>=3)]
    essay=('Public libraries deserve continued public funding because they provide educational opportunities that many residents cannot afford privately. '
           'Although digital services have changed how people find information, they have not removed the need for shared learning spaces. '
           'First, libraries make books and reliable online resources available without charging each visitor. Students from households with limited incomes can study, borrow materials and complete assignments using public computers. '
           'For example, a student who lacks a quiet room or internet access at home can prepare for examinations in a library. These services reduce practical barriers to learning. '
           'Second, trained librarians help people find trustworthy information and develop useful digital skills. Workshops can support older adults who need assistance with online forms and job seekers who are preparing applications. '
           'This support has value beyond the simple availability of books. Critics argue that maintaining library buildings is expensive and that online subscriptions could replace them. '
           'That concern should encourage careful budgeting, but an online service cannot provide a safe study space or personal guidance to every resident. '
           'Local authorities should therefore assess community needs and combine physical facilities with digital collections. In conclusion, funding public libraries is justified because they widen access to education and offer practical support. '
           'Modernizing their services is a better response to technological change than withdrawing public investment.')
    prompt='Should governments continue funding public libraries in the digital age? Discuss your position with reasons and examples.'
    cases.extend([('essay_relevant',prompt,essay,lambda r:r['traits'].get('content',{}).get('score',-1)>=4),
                  ('essay_unrelated',prompt,' '.join(['Bananas grow in warm climates and football players train before important matches.']*18),lambda r:r['traits'].get('content',{}).get('score',-1)==0)])
    outputs=[]
    for name,source,response,check in cases:
        start=time.monotonic()
        kind='WE' if name.startswith('essay_') else 'SWT'
        context={'prompt':source} if kind=='WE' else {'reference':source}
        result=score_question(Question(id=name,type=kind,response=response,**context),assessor)
        item={'case':name,'passed':result['status']=='scored' and check(result),'seconds':round(time.monotonic()-start,2),'result':result}
        outputs.append(item)
        print(json.dumps(item),flush=True)
    Path('examples/writing-quality-check.json').write_text(json.dumps({'model':Path(os.getenv('PTE_MODEL_PATH','default')).name,'note':'Six developer smoke cases, not a human-rated accuracy benchmark.','cases':outputs},indent=2),encoding='utf-8')
    return 0 if all(x['passed'] for x in outputs) else 1

if __name__=='__main__':
    raise SystemExit(main())
