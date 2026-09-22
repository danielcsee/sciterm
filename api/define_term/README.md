# api/define_term

Defines a phrase the reader highlighted in a chat answer or a paper, in
simpler language, using the paragraph it came from.

```
POST /define {"phrase": "...", "surrounding_context": "..." | null,
              "annotation": { ...source and selector... }}
          -> {"definition": "...", "annotation": { ...durable row... }}
```

## Files

| File | Purpose |
|---|---|
| `routes.py` | The route: finds the OpenAI client, maps failures to 503/502 |
| `models.py` | `DefineTermRequest` / `DefineTermResponse`, with length caps |

The prompt itself lives in [`api/llm/definition.py`](../llm/definition.py),
beside the other prompts; this package is only the HTTP surface.

## Decisions worth knowing

**Gated.** Each call spends OpenAI tokens, so the router carries
`require_user`, like `rag_search`.

**The UI decides the context.** A highlight over 12 words is sent with
`surrounding_context: null` — a long highlight carries its own context. The
server does not re-check the word count; it only caps lengths, so one click
cannot send a whole paper.

**Saved first.** The route validates the owner-scoped chat or paper source and
commits the annotation before asking OpenAI, then stores the definition. A
reload mid-request, or a 502, still leaves the annotation saved.

**One whole answer, not a stream.** Definitions are about 100 words, so
`LlmClient.complete_text` returns them whole on the routing timeout
(`OPENAI_TIMEOUT_SECONDS`).

## Dependencies

`fastapi`, `pydantic`, `api.annotations`, `api.auth`, `api.llm`.
