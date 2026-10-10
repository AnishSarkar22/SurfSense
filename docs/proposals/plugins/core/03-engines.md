# Engines

> Owns: `surfsense_local/backend/modules/agent/plugin_tools/`, the `@` mention in the agent composer, plugin steps in agent threads, Save to Sources.
> Later: the chat engine's router step, [below](#the-chat-engine-later), decided by [ADR 0052](../../../adr/0052-the-chat-model-never-calls-tools.md). Gateway: [`01-architecture.md`](01-architecture.md).

Plugins reach agent threads first. A thread opened in Agentic mode is opencode's, and opencode already calls tools natively, so plugins need only an MCP endpoint in front of the gateway. A thread in Basic mode is the chat engine's, which never calls tools; it gets plugins later, through a router step of its own ([below](#the-chat-engine-later)). The two engines stay as they are ([agent](../../../architecture/agent.md#which-threads-get-it), [chat](../../../architecture/chat.md)).

Agentic mode is offered only for models tested with opencode, so a user on a chat-only model has no plugins until the chat engine gets them. Settings → Plugins says so: "Plugins work in Agentic threads."

## opencode

- Before each turn, [`registration.py`](../../../../surfsense_local/backend/modules/agent/tool_endpoint/registration.py) registers a second MCP server, `plugins`, beside `surfsense`, at `/agent/plugin-tools/workspaces/{workspace}/threads/{thread}`, with the same launch key, `Origin` refusal and 200-second limit.
- The endpoint works like [`tool_endpoint/`](../../../../surfsense_local/backend/modules/agent/tool_endpoint/). `tools/list` is the gateway's `list_tools`, with schemas flattened as SurfSense's own tools are, so small models do not send nested arguments as strings. `tools/call` is `call_tool` with `caller: agent` and a 190-second deadline.
- opencode never connects to a plugin server itself. The endpoint is an MCP server in front of the gateway, which forwards each call to the plugin's server through the MCP client, so approval, egress consent and the record of calls apply to every call. Both sides are plain MCP.
- SurfSense's own tool list, and the test that pins its order, do not change.
- A plugin connected or a tool switched on mid-thread appears at the next turn, which misses the prompt cache once.
- Only `direct` tools are listed, at most 24 per thread, the plugins connected first winning.
- A call shows as a step. [`step-label.tsx`](../../../../surfsense_local/frontend/src/features/agent/step-label.tsx) already labels an unknown tool "Used {tool}"; it gains the plugin's name and the tool's title.
- A call that needs approval waits for it inside its deadline ([`04-trust.md`](04-trust.md#approval)).

## `@` mentions

The user can name a tool rather than leave the choice to the agent.

- Typing `@` in the agent composer lists ready tools as `@<plugin> <tool>`.
- A mention makes that tool offered for the turn, even beyond the 24 a thread lists, and tells the agent the user asked for it: "The user asked you to use Notion's Search for this."
- The agent fills the inputs and makes the call, as with any tool, so a mention needs no form and no model call of its own.
- Approval is unchanged: the agent chose the inputs, not the user, so the call asks as [`04-trust.md`](04-trust.md#approval) says.

## Results

- A call is a step in the agent's message: the tool's title, the plugin's name, a one-line summary, and the result when expanded.
- The model gets the result trimmed to 20 KB ([`01-architecture.md`](01-architecture.md#results)); the step shows all of it.
- Reopening a thread shows its steps from `plugin_calls`, without calling anything again.

## Save to Sources

- A step has "Save to Sources". It writes a note with the result as markdown and `document_metadata` naming `plugin_id`, `tool`, `call_id` and `fetched_at` ([documents](../../../architecture/documents.md)).
- Saving the result of the same tool with the same arguments again updates that note in place and its `fetched_at`, rather than adding a copy.
- Nothing is saved without the user asking.

## Acceptance

- An agent thread with a test plugin connected: the agent calls its tool, the step shows the plugin and title, and SurfSense's own tool list is unchanged.
- A plugin tool switched off disappears from the next turn's `tools/list`.
- `@test search` in an agent thread offers `test__search` that turn and the agent calls it; a call that needs approval still asks.
- A thread in Basic mode lists no plugin tools, and Settings → Plugins says plugins work in Agentic threads.
- Save to Sources twice on the same call leaves one note, with the later `fetched_at`.

## The chat engine (later)

Not built until plugins reach Basic threads. The design is kept here so it can be picked up as it stands.

The chat model never calls a tool ([ADR 0052](../../../adr/0052-the-chat-model-never-calls-tools.md)). Before the answer, SurfSense asks it two small questions, each held to a JSON schema, then makes the call itself. Every text route the chat engine uses already takes a schema, ChatGPT plans included, so plugins add nothing model-specific.

The router runs when the thread is a chat thread, the workspace has a ready `direct` tool with a flat input schema that is not `destructiveHint: true`, and the router is on for the selected model ([below](#when-the-router-is-on)). In `modules/chat/plugin_router/`:

1. **Choose.** One call with the user's message, the last exchange, and each candidate tool's name, title and description, held to `{"tool": <enum of the candidates, plus "none">}`, thinking off. `none` ends the router.
2. **Fill.** One call held to the chosen tool's input schema. A required field it cannot fill ends the router.
3. **Call.** `call_tool` with `caller: chat_router`, a 60-second deadline, and the same approval as the agent.
4. **Answer.** The result joins the final user message as a labelled block after the retrieved passages, so the prompt grows only at its end ([ADR 0049](../../../adr/0049-prompts-grow-at-the-end.md)). Then the normal answer call runs.

A schema is not a guarantee: llama-server rejects one for some chat templates, and some endpoints ignore it. So each reply is validated before anything is called: a choose reply that does not match counts as `none`, a fill reply that does not match ends the router. A router call that fails skips the router. Whenever the router ends early, the turn answers as it does today.

Router calls are model requests like any other: they go through the same route and admission ([ADR 0048](../../../adr/0048-the-api-is-the-only-path-to-a-text-model.md)), and on a ChatGPT plan they count against the user's plan. Each costs one or two model calls when tools are ready, and how well small models choose is unmeasured.

### When the router is on

The [chat eval](../../chat-eval.md) gains a router test: questions with the right tool or `none` and the right inputs, run on every curated model. The first row that matches the selected model wins.

| The selected model | Router |
|---|---|
| `structured_output: false` in the catalog | Never |
| Three router replies in a row that did not match their schema | Off, with a notice; the user can turn it back on |
| Failed the router test | Off by default |
| Passed the router test | On by default |
| Remote, with `structured_output: true` in the catalog, or a ChatGPT plan's model | On by default |
| Anything else: local and not yet measured, unknown to the catalog, or a custom connection's model | Off by default |

Where it is off by default, Settings → Plugins offers "Let the chat use plugins on its own" for that model.

### `@` mentions in chat threads

A mention skips choose. Where the router is on for the model, the model fills the inputs; where it is off, or a fill reply fails its schema, the composer shows the tool's inputs as a form, filled from the message where it can be, for the user to complete, so a mention works on every model. The call's result joins the answer as in step 4. A mention whose inputs the user completed in the form is the user's approval for that one call, unless the tool is `destructiveHint: true`.

### Acceptance, when built

- A chat thread with the router on: a question that fits the test tool calls it and answers from its result; a question that does not gets `none` and a normal answer, with one extra model call.
- A model with `structured_output: false` never runs the router, and `@` on it opens the input form.
- A local model whose template rejects the schema, and an endpoint that ignores `response_format`, both end with no tool call and a normal answer.
- Three mismatched router replies in a row switch the router off for that model, with a notice.
- `@test search cats` in a chat thread on Qwen3-0.6B, with the router off, opens the form with `cats` filled in; sending it calls the tool without asking for approval.
