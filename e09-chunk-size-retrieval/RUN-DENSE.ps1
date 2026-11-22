# E09 embedding runs. Run from this folder in PowerShell.
# The local run is free (downloads all-MiniLM-L6-v2, about 90 MB, once).
# The OpenAI run costs about $0.22 and needs OPENAI_API_KEY in .env (git-ignored).
$ErrorActionPreference = 'Stop'
python -m pip install -r requirements.txt
python -m unittest -v test_e09
python retrieve_dense.py --model local
python retrieve_dense.py --model openai --estimate
Read-Host 'Check the estimate above, then press Enter to run OpenAI (Ctrl+C to stop)'
python retrieve_dense.py --model openai --yes
python analyse.py
Write-Host 'Done. Commit results/*/rankings.jsonl, results/*/manifest.json and analysis/ (caches stay ignored).'
