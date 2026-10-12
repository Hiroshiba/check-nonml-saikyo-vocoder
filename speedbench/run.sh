#!/usr/bin/env bash
set -uo pipefail
ROOT="$PWD"
mkdir -p speed-results
export HF_HUB_DISABLE_XET=1
export MPLBACKEND=Agg
export NUMBA_NUM_THREADS=1
python -m pip install -q uv
python -m uv venv --python 3.10 /tmp/vspeed
PY=/tmp/vspeed/bin/python
python -m uv pip install --python "$PY" 'torch==2.5.1+cpu' 'torchaudio==2.5.1+cpu' --index-url https://download.pytorch.org/whl/cpu
python -m uv pip install --python "$PY" 'numpy==1.26.4' 'scipy==1.13.1' soundfile 'librosa==0.10.2.post1' einops 'huggingface_hub<1' safetensors pyworld pysptk hydra-core joblib scikit-learn tensorboardX 'setuptools<81' future gdown requests pyyaml matplotlib descript-audiotools argbind tqdm tensorboard
python -m uv pip install --python "$PY" diffsptk 'lightning==2.1.3' jsonargparse torchlpc kazane torch_fftconv praat-parselmouth
python -m uv pip install --python "$PY" --no-deps -e /tmp/speed-src/dac -e /tmp/speed-src/facodec -e /tmp/speed-src/sifigan
"$PY" - <<'PYCODE'
import os,json,traceback,pathlib,hashlib,subprocess
from huggingface_hub import HfApi,hf_hub_download
root=pathlib.Path('/tmp/speed-models');root.mkdir(exist_ok=True)
records=[]
for repo,patterns in [('amphion/naturalspeech3_facodec',['ns3_facodec_encoder.bin','ns3_facodec_decoder.bin']),('Aalto-Speech-Synthesis/HiFi-Glot',None)]:
 try:
  files=HfApi().list_repo_files(repo);print('HF_FILES',repo,files,flush=True)
  selected=patterns or [f for f in files if f.endswith(('.safetensors','.json'))]
  for name in selected:
   p=hf_hub_download(repo,name,local_dir=root/repo.split('/')[-1]); records.append({'repo':repo,'name':name,'path':p,'size':os.path.getsize(p),'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest()})
 except Exception:
  traceback.print_exc();records.append({'repo':repo,'error':traceback.format_exc()})
try:
 import dac
 p=dac.utils.download(model_type='44khz');records.append({'repo':'official-dac','path':str(p),'size':os.path.getsize(p),'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest()})
except Exception:
 traceback.print_exc();records.append({'repo':'official-dac','error':traceback.format_exc()})
try:
 import gdown
 p=gdown.download(id='1uzqTeumvkPQpfdK_D4U41MDL5-s-hs0l',output=str(root/'sifigan.tar.gz'),quiet=False)
 if p is None:raise RuntimeError('gdown returned None')
 records.append({'repo':'official-sifigan','path':p,'size':os.path.getsize(p),'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest()})
 subprocess.run(['tar','xf',p,'-C',str(root)],check=True)
except Exception:
 traceback.print_exc();records.append({'repo':'official-sifigan','error':traceback.format_exc()})
for p in pathlib.Path('/tmp/speed-src/golf/ckpts/interspeech24').rglob('*.ckpt'):
 records.append({'repo':'official-golf','path':str(p),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
pathlib.Path('speed-results/model_manifest.json').write_text(json.dumps(records,indent=2))
for r in records:print('MODEL_RECORD',json.dumps(r),flush=True)
for base in [root,pathlib.Path('/tmp/speed-src/golf/ckpts')]:
 for p in base.rglob('*'):
  if p.is_file(): print('MODEL_FILE',p,p.stat().st_size,flush=True)
PYCODE
"$PY" -m pip freeze > speed-results/pip-freeze.txt 2>&1 || python -m uv pip freeze --python "$PY" > speed-results/pip-freeze.txt
if [ -f speedbench/benchmark.py ]; then
  "$PY" speedbench/benchmark.py
fi
