# E9b methods that need your PC. Run one step at a time; each ends by rescoring with improve.py.
# Needs: pip install -r requirements.txt, and OPENAI_API_KEY in .env for the LLM steps.
# Replace <chat-model> with the chat model id you want to use (a small, cheap one is fine).

# Step 1, free: re-ranker (downloads ~90 MB once)
python pc_methods.py rerank
python improve.py

# Step 2, free: hybrid (needs E9's local embedding run from RUN-DENSE.ps1 first)
python pc_methods.py hybrid --dense local
python improve.py

# Step 3, a few cents: an LLM writes the search words (10 calls)
python pc_methods.py rewrite --llm <chat-model>
python improve.py

# Step 4, about $5-8 before caching: Anthropic's contextual retrieval on the 40 test contracts
python pc_methods.py contextual --llm <chat-model> --price <USD per million input tokens> --estimate
python pc_methods.py contextual --llm <chat-model> --price <USD per million input tokens> --yes
python improve.py

# Then commit results/*/rankings.jsonl, results/*/manifest.json, results/rewrite/rewrites.json and analysis/.
