"""Portal weights transcribed from slides 3–6 and 29, not official score conversion."""
WEIGHTS = {
 'speaking': {'DI':31,'SGD':19,'RS':16,'RTS':13,'RL':13,'RA':9},
 'writing': {'WE':31,'SWT':28,'WFD':23,'SST':18},
 'reading': {'FIB':25,'SWT':23,'FIB_DD':20,'HIW':13,'RO':9,'MCM_R':5,'HCS':3,'MCS_R':3},
 'listening': {'SGD':20,'RS':17,'WFD':13,'RL':13,'SST':10,'FIB_L':8,'HIW':8,'ASQ':4,'MCM_L':3,'MCS_L':2,'HCS':2,'SMW':1},
 # Slide 29 says <1 for MCS_R, MCS_L and HCS. 0.5 is an explicit assumption.
 'overall': {'RA':4,'RS':7,'DI':15,'RL':6,'ASQ':2,'SGD':9,'RTS':6,'SWT':7,'WE':7,'FIB':7,'MCM_R':1,'RO':3,'FIB_DD':6,'MCS_R':0.5,'SST':4,'MCM_L':1,'FIB_L':3,'HCS':0.5,'MCS_L':0.5,'SMW':1,'HIW':4,'WFD':5}
}
TARGETS = {t:86 if t in {'RA','RS','DI','RL','SGD','RTS'} else 95 if t=='SWT' else 90 if t in {'WE','WFD','SST','FIB','FIB_DD','FIB_L','HIW'} else 50 for t in WEIGHTS['overall']}
SECTIONS = {t:'Speaking' if t in {'RA','RS','DI','RL','ASQ','SGD','RTS'} else 'Writing' if t in {'WE','SWT'} else 'Reading' if t in {'FIB','FIB_DD','RO','MCM_R','MCS_R'} else 'Listening' for t in TARGETS}
SPOKEN = {'RA','RS','DI','RL','SGD','RTS'}
RUBRICS = {
 'RA':{'content':5,'pronunciation':5,'oral_fluency':5},
 'DI':{'content':6,'pronunciation':5,'oral_fluency':5},
 'RL':{'content':6,'pronunciation':5,'oral_fluency':5},
 'SGD':{'content':6,'pronunciation':5,'oral_fluency':5},
 'RTS':{'content':6,'pronunciation':5,'oral_fluency':5},
 'RS':{'content':3,'pronunciation':5,'oral_fluency':5},
 'SWT':{'content':4,'form':1,'grammar':2,'vocabulary':2},
 'SST':{'content':4,'form':2,'grammar':2,'vocabulary':2,'spelling':2},
 'WE':{'content':6,'form':2,'development_structure_coherence':6,'grammar':2,'general_linguistic_range':6,'vocabulary_range':2,'spelling':2},
 'ASQ':{'vocabulary':1}
}
ALIASES = {'pte_reorder':'RO','pte_fill_in_blanks':'FIB','pte_fill_drag':'FIB_DD',
 'pte_mcq_multiple':'MCM_R','pte_mcq_single':'MCS_R',
 'read_aloud':'RA','repeat_sentence':'RS','describe_image':'DI','retell_lecture':'RL',
 'summarize_group_discussion':'SGD','respond_to_a_situation':'RTS','answer_short_question':'ASQ',
 'summarize_written_text':'SWT','write_essay':'WE','summarize_spoken_text':'SST',
 'write_from_dictation':'WFD','highlight_incorrect_words':'HIW','highlight_correct_summary':'HCS',
 'reading_fill_dropdown':'FIB','reading_fill_drag_drop':'FIB_DD','listening_fill_type_in':'FIB_L',
 'reading_mcq_multiple':'MCM_R','reading_mcq_single':'MCS_R','listening_mcq_multiple':'MCM_L',
 'listening_mcq_single':'MCS_L','select_missing_word':'SMW','reorder_paragraphs':'RO'}
