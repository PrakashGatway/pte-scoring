from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .config import ALIASES, TARGETS, SPOKEN

class SpeechWord(BaseModel):
    model_config = ConfigDict(extra='forbid')
    word: str = Field(min_length=1, max_length=100)
    pronunciation: float = Field(ge=0,le=100)
    pause_after_seconds: float = Field(default=0,ge=0,le=300)

class SpeechEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source: str = Field(min_length=1,max_length=100)
    pronunciation: float = Field(ge=0,le=5)
    oral_fluency: float = Field(ge=0,le=5)
    words: list[SpeechWord] = Field(default_factory=list,max_length=2000)

class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1,max_length=100)
    type: str
    prompt: str = Field(default='',max_length=50000)
    reference: str = Field(default='',max_length=50000)
    response: str | list[str] = Field(default='')
    correct: str | list[str] | None = None
    options: list[str] = Field(default_factory=list,max_length=500)
    key_points: list[str] = Field(default_factory=list,max_length=100)
    speech: SpeechEvidence | None = None
    skipped: bool = False

    @field_validator('type')
    @classmethod
    def canonical(cls,v):
        v=ALIASES.get(v,v.upper())
        if v not in TARGETS: raise ValueError('Unsupported question type')
        return v

    @model_validator(mode='after')
    def validate_answer(self):
        arrays={'FIB','FIB_DD','FIB_L','RO','MCM_R','MCM_L','HIW'}
        scalar={'MCS_R','MCS_L','HCS','SMW','ASQ'}
        if isinstance(self.response,str) and len(self.response)>50000: raise ValueError('Response too long')
        if isinstance(self.response,list) and (len(self.response)>500 or any(len(s)>1000 for s in self.response)): raise ValueError('Response too long')
        if self.type in arrays:
            if not isinstance(self.correct,list) or not self.correct: raise ValueError('Nonempty correct array required')
            if not isinstance(self.response,list): raise ValueError('Response must be an array (use [] for skipped)')
            if any(not x.strip() for x in self.correct): raise ValueError('Answer key entries cannot be empty')
            if self.type in {'RO','MCM_R','MCM_L','HIW'}:
                if len(set(self.correct))!=len(self.correct) or len(set(self.response))!=len(self.response): raise ValueError('Duplicate IDs are not allowed')
            if self.type=='RO' and (len(self.correct)<2 or (self.response and set(self.response)!=set(self.correct))): raise ValueError('Reorder response must be a permutation of the key')
            if self.type in {'FIB','FIB_DD','FIB_L'} and len(self.response)>len(self.correct): raise ValueError('Too many blank responses')
        elif self.type in scalar:
            if not self.correct or (isinstance(self.correct,str) and not self.correct.strip()): raise ValueError('Answer key required')
            if not isinstance(self.response,str): raise ValueError('Response must be text')
        else:
            if not isinstance(self.response,str): raise ValueError('Response must be text or transcript')
            if self.type in {'RA','RS','WFD'} and not self.reference.strip(): raise ValueError('Reference text required')
            if self.type not in {'RA','RS','WFD'} and not (self.prompt.strip() or self.reference.strip() or self.key_points): raise ValueError('Prompt, reference or key points required')
        if self.options and self.type in scalar|{'MCM_R','MCM_L','HIW'}:
            keys=self.correct if isinstance(self.correct,list) else [self.correct]
            answers=self.response if isinstance(self.response,list) else [self.response]
            if any(x not in self.options for x in keys+answers if x): raise ValueError('Unknown option ID')
        if self.speech and self.type not in SPOKEN: raise ValueError('Speech evidence is only used for spoken tasks')
        return self

class Attempt(BaseModel):
    model_config = ConfigDict(extra='forbid')
    attempt_id: str = Field(min_length=1,max_length=100)
    questions: list[Question] = Field(min_length=1,max_length=200)
    targets: dict[str,float] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_attempt(self):
        if len({q.id for q in self.questions})!=len(self.questions): raise ValueError('Question IDs must be unique')
        if any(k not in TARGETS or not 0<=v<=100 for k,v in self.targets.items()): raise ValueError('Targets must use canonical types and percentages 0–100')
        return self
