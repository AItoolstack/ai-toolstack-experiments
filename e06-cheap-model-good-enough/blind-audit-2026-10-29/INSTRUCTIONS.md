# Blind audit, stage one

Read only this folder's INSTRUCTIONS.md, requests.jsonl and tools.json. Do not read parent files, source code, results, keys, labels, other chats or environment credentials. All people and policies are fictional.

Answer every one of the 102 requests using its exact system and user messages. Do not execute any tool or send anything. For tool items, write the selected action as an object with call (tool name or null) and args (an object when a tool is selected). Invoice answers use the ten requested keys. Rules answers use amount and rules_used.

Save answers.jsonl in this folder, one object per request, with id, answer, ambiguous (boolean), and reason (one line for any ambiguity). Solve from the supplied text; do not infer an intended key. Do not invent missing facts. At completion report the number answered and ambiguous IDs. Label/trap audit is a separate second stage after these answers are saved.
