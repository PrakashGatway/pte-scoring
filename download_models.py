"""One-time downloads of free model weights. Subsequent inference is local."""
from pathlib import Path
from huggingface_hub import hf_hub_download
from faster_whisper import WhisperModel
root=Path(__file__).resolve().parent/'models'
hf_hub_download('Qwen/Qwen2.5-0.5B-Instruct-GGUF','qwen2.5-0.5b-instruct-q5_k_m.gguf',local_dir=root/'qwen')
WhisperModel('tiny.en',device='cpu',compute_type='int8',download_root=str(root))
print('Local models ready.')
