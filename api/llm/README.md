# api/llm

The OpenAI integration. Today it does one thing: routes each chat query to a
single tool, and confirms which entity candidates the query names.

```
rag_search -> filter_entity_matches -> classify_intent -> IntentResult -> api.paper_search
```

## Files

| File | Purpose |
|---|---|
| `tools.py` | Pydantic argument models for `paper_search`, `paper_analysis`, `no_match`, and their tool schemas |
| `client.py` | `LlmClient`: the Responses API call, forced to exactly one tool call |
| `intent.py` | The prompt, candidate payload, and joining the model's entities back to candidates |
| `models.py` | `IntentResult` / `IntentEntity`, returned on `RagSearchResponse.intent` |

## Decisions worth knowing

**Pydantic is the schema.** `openai.pydantic_function_tool` emits each tool as
strict JSON schema, and `responses.parse` validates the arguments back into the
same class. Never hand-write a tool schema.

**One call does both jobs.** Every tool carries `entities`, and
`tool_choice="required"` with `parallel_tool_calls=False` forces exactly one
call — so the intent and the entities arrive together.

**Entities are ids, checked on return.** Candidates go out as
`{id, name, type, matched_text}`; the model answers with `{entity_id, phrase}`.
Ids that were never offered are dropped.

**Failure never breaks chat.** No key, a timeout, or a malformed answer leaves
`intent` null and explains itself in `intent_error`; paper search still
answers from the query's noun phrases.

## Dependencies

`openai` (Responses API), `pydantic`, `api.entity_matching`, `api.app.config`
(`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_REASONING_EFFORT`,
`OPENAI_TIMEOUT_SECONDS`).
