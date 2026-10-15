"""Download free local scoring/transcription models once; later inference is offline."""
from pathlib import Path
import shutil, subprocess
from faster_whisper import WhisperModel

root=Path(__file__).resolve().parent/'models'
model_dir=root/'qwen-semantic'
model_dir.mkdir(parents=True,exist_ok=True)
model=model_dir/'qwen2.5-3b-instruct-q4_k_m.gguf'
model_size=2_104_932_768
if not model.exists() or model.stat().st_size!=model_size:
    curl=shutil.which('curl.exe') or shutil.which('curl')
    if not curl:
        raise RuntimeError('curl is required to download the 2.1 GB Qwen GGUF model.')
    url='https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf'
    subprocess.run([curl,'-L','--fail','--retry','5','--retry-all-errors','--continue-at','-','--output',str(model),url],check=True)
    if model.stat().st_size!=model_size:
        raise RuntimeError('Qwen model download is incomplete; rerun this script to resume it.')
WhisperModel('base.en',device='cpu',compute_type='int8',download_root=str(root))
print('Local models ready.')
