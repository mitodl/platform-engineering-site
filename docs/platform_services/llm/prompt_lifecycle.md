# LLM prompt lifecycle

Open Learning LLM call sites are moving onto
[ol-llm](https://github.com/mitodl/ol-llm), and apps on it fetch their prompts from Opik through it.
Production runs the prompt version an app's repository points at: a pull request moves the
pointer, and merging it moves the `production` label in Opik.

The runbook lives with the library, so it changes with the code it describes:
[Prompt promotion](https://github.com/mitodl/ol-llm/blob/main/docs/prompt-promotion.md). It
covers moving production, what running apps see after a label moves (up to five minutes of
cache), rolling back, what to do while Opik is down, and what to check after a promotion.

The decisions behind it are in
[`llm-opik-lifecycle-spec.md`](https://github.com/mitodl/ol-infrastructure/blob/main/docs/plans/llm-opik-lifecycle-spec.md)
(section 1.2 item 5 for the drift report, 2.3 for promotion, 3 for the runtime
policy, and 5.1 item 9 for online scoring).
