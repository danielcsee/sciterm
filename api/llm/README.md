# api/llm

The OpenAI integration. It routes each chat query to a single tool, confirms
which entity candidates the query names, writes `paper_analysis` answers, and
defines phrases a reader highlights.

```
rag_search -> filter_entity_matches -> classify_intent -> IntentResult -> api.paper_search
```

## Files

| File | Purpose |
|---|---|
| `tools.py` | Pydantic argument models for `paper_search`, `paper_analysis`, `no_match`, and their tool schemas |
| `client.py` | `LlmClient`: a forced single tool call (`choose_tool`), or free text, whole (`complete_text`) or streamed (`stream_text`) |
| `analysis.py` | The answer prompt: numbered passages in, prose citing `[n]` out |
| `definition.py` | The definition prompt: a phrase and its paragraph in, plain language out |
| `intent.py` | The prompt, candidate payload, and joining the model's entities back to candidates |
| `answer_entities.py` | Its own tool: every phrase naming each candidate in a generated answer |
| `models.py` | `IntentResult` / `IntentEntity`, returned on `RagSearchResponse.intent` |

## Decisions worth knowing

**Pydantic is the schema.** `openai.pydantic_function_tool` emits each tool as
strict JSON schema, and `responses.parse` validates the arguments back into the
same class. Never hand-write a tool schema.

**One call does both jobs.** Every tool carries `entities`, and
`tool_choice="required"` with `parallel_tool_calls=False` forces exactly one
call — so the intent and the entities arrive together.

**Answers get their own entity tool.** Routing returns one phrase per entity,
because `api.paper_search` makes each distinct phrase one ranking term, and a
list would change ranking. `answer_entities` returns a phrase list instead, and
drops any phrase the answer does not contain.

**Entities are ids, checked on return.** Candidates go out as
`{id, name, type, matched_text}`; the model answers with `{entity_id, phrase}`.
Ids that were never offered are dropped.

**Failure never breaks chat.** No key, a timeout, or a malformed answer leaves
`intent` null and explains itself in `intent_error`; paper search still
answers from the query's noun phrases.

**Answers stream, on their own budget.** `stream_text` yields the text as the
model writes it, so the reader starts before it is finished. It uses
`OPENAI_ANALYSIS_TIMEOUT_SECONDS` (60s, per read) and no retry: generation is
slow, and a retry would double the wait — or repeat text already shown.

## Dependencies

`openai` (Responses API), `pydantic`, `api.entity_matching`, `api.app.config`
(`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_REASONING_EFFORT`,
`OPENAI_TIMEOUT_SECONDS`, `OPENAI_ANALYSIS_TIMEOUT_SECONDS`).
