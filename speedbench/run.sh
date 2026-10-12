#!/usr/bin/env bash
set -uo pipefail
mkdir -p speed-results
export HF_HUB_DISABLE_XET=1 MPLBACKEND=Agg NUMBA_NUM_THREADS=1
export PYTHONPATH=/tmp/speed-src/dac:/tmp/speed-src/facodec:/tmp/speed-src/sifigan
python -m pip install -q uv
python -m uv venv --python 3.10 /tmp/vspeed
PY=/tmp/vspeed/bin/python
python -m uv pip install --python "$PY" 'torch==2.5.1+cpu' 'torchaudio==2.5.1+cpu' --index-url https://download.pytorch.org/whl/cpu
python -m uv pip install --python "$PY" 'numpy==1.26.4' 'scipy==1.13.1' soundfile 'librosa==0.10.2.post1' einops 'huggingface_hub<1' safetensors pyworld pysptk hydra-core joblib scikit-learn tensorboardX 'setuptools<81' future gdown requests pyyaml matplotlib descript-audiotools argbind tqdm tensorboard h5py nnAudio
python -m uv pip install --python "$PY" 'diffsptk==4.0.1' 'lightning==2.1.3' jsonargparse 'torchlpc==0.6' 'kazane==1.0.4' 'torch_fftconv==1.0.0' praat-parselmouth
git -C /tmp/speed-src/golf -c url.https://github.com/.insteadOf=git@github.com: submodule update --init --recursive
git -C /tmp/speed-src/golf submodule status --recursive > speed-results/golf-submodules.txt
cp speedbench/benchmark.py speed-results/benchmark_original.py
"$PY" - <<'PYCODE'
import os,json,traceback,pathlib,hashlib,subprocess,difflib
from huggingface_hub import HfApi,hf_hub_download
root=pathlib.Path('/tmp/speed-models');root.mkdir(exist_ok=True)
records=[]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
for repo,names in [('amphion/naturalspeech3_facodec',['ns3_facodec_encoder.bin','ns3_facodec_decoder.bin']),('Aalto-Speech-Synthesis/HiFi-Glot',['hifiglot/config.json','hifiglot/epoch-0175_step-1070000/model.safetensors'])]:
 try:
  rev=HfApi().model_info(repo).sha
  for name in names:
   p=hf_hub_download(repo,name,revision=rev,local_dir=root/repo.split('/')[-1]);records.append({'repo':repo,'revision':rev,'name':name,'path':p,'size':os.path.getsize(p),'sha256':sha(p)})
 except Exception:traceback.print_exc();records.append({'repo':repo,'error':traceback.format_exc()})
try:
 import dac
 p=dac.utils.download(model_type='44khz');records.append({'repo':'official-dac','path':str(p),'size':os.path.getsize(p),'sha256':sha(p)})
except Exception:traceback.print_exc();records.append({'repo':'official-dac','error':traceback.format_exc()})
try:
 import gdown
 p=gdown.download(id='1uzqTeumvkPQpfdK_D4U41MDL5-s-hs0l',output=str(root/'sifigan.tar.gz'),quiet=False)
 if p is None:raise RuntimeError('gdown returned None')
 records.append({'repo':'official-sifigan','path':p,'size':os.path.getsize(p),'sha256':sha(p)});subprocess.run(['tar','xf',p,'-C',str(root)],check=True)
except Exception:traceback.print_exc();records.append({'repo':'official-sifigan','error':traceback.format_exc()})
for p in pathlib.Path('/tmp/speed-src/golf/ckpts/interspeech24/golf-ff').rglob('*.ckpt'):
 records.append({'repo':'official-golf','path':str(p),'size':p.stat().st_size,'sha256':sha(p)})
pathlib.Path('speed-results/model_manifest.json').write_text(json.dumps(records,indent=2))
for r in records:print('MODEL_RECORD',json.dumps(r),flush=True)
p=pathlib.Path('/tmp/speed-src/golf/models/lru/recurrence.py');old=p.read_text();new='from typing import Any\n'+old.replace('torch.Any','Any');p.write_text(new)
pathlib.Path('speed-results/golf-compat.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='recurrence.py.original',tofile='recurrence.py')))
p=pathlib.Path('speed-results/benchmark_original.py');old=p.read_text();new=old
new=new.replace('model(sg(z[0]),z[1],z[2])','model(sg(z[0]).float(),z[1],z[2])')
new=new.replace("for p in pathlib.Path('/usr/lib/sptk/bin').glob('*'):","for p in [pathlib.Path(f) for f in subprocess.check_output(['dpkg','-L','sptk'],text=True).splitlines() if pathlib.Path(f).is_file() and os.access(f,os.X_OK)]:")
new=new.replace("sys.path.insert(0,'/tmp/magphase-port/src')","sys.path.insert(0,'/tmp/magphase-port');sys.path.insert(0,'/tmp/magphase-port/src')")
new=new.replace('import magphase as mp','from src import magphase as mp')
new=new.replace('resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024',"float(re.search(r'VmHWM:\\s+(\\d+)',pathlib.Path('/proc/self/status').read_text())[1])/1024")
new=new.replace("start=time.perf_counter();adapter=", "meta['rss_before_load_mib']=float(re.search(r'VmRSS:\\s+(\\d+)',pathlib.Path('/proc/self/status').read_text())[1])/1024;start=time.perf_counter();adapter=")
new=new.replace("meta.update(adapter.info)","meta.update(adapter.info);meta['rss_after_load_mib']=float(re.search(r'VmRSS:\\s+(\\d+)',pathlib.Path('/proc/self/status').read_text())[1])/1024")
# Run MagPhase first so any remaining Python2 compatibility failure is visible early in the log.
new=new.replace("NAMES=['dac','facodec','hifiglot','golf','sifigan','llsm','magphase']", "NAMES=['magphase','llsm','golf','sifigan','hifiglot','facodec','dac']")
pathlib.Path('speed-results/benchmark.py').write_text(new)
pathlib.Path('speed-results/benchmark-compat.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='benchmark_original.py',tofile='benchmark.py')))
PYCODE
python -m uv pip freeze --python "$PY" > speed-results/pip-freeze.txt
"$PY" speed-results/benchmark.py
cp speedbench/run.sh speed-results/run.sh
dpkg -L sptk > speed-results/sptk-package-files.txt
tar --exclude='*/.git' --exclude='*.pyc' --exclude='__pycache__' -czf speed-results/golf-submodule-sources.tar.gz -C /tmp/speed-src/golf models/audiotensor models/lru
if [ -d /tmp/magphase-port ]; then tar --exclude='*.wav' --exclude='*.pyc' --exclude='__pycache__' -czf speed-results/magphase-port.tar.gz -C /tmp magphase-port; fi
