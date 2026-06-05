# The Story Behind llm-zip

## Where it came from

Early 2026, I kept seeing the same discussion everywhere — posts, threads, articles: teams running through their AI budgets faster than expected, subscriptions being reconsidered, inference costs becoming a harder conversation to avoid.

I'm not naive enough to think llm-zip solves that problem. It doesn't. If an organization is spending unsustainably on AI inference, compressing context is a band-aid, not a cure. But it does attack a real and specific pain point: tokens are the unit of cost, and a significant portion of the tokens sent to any LLM in a RAG or agentic workflow are redundant.

That observation, plus my own interest in keeping my internal LLM usage costs under control, is where llm-zip came from.

## What I actually built and tested

llm-zip is an HTTP sidecar. You call it before calling your LLM API. It compresses the text, scores how much meaning was preserved, and tells you roughly how much you saved. Your API keys and model calls never touch it.

I built and validated the compression pipeline locally — against real documents, real text. The architecture works. The API contracts work. The CLI works.

What I haven't done is run it end-to-end against live API billing across multiple providers. The USD savings estimates are calculated algorithmically: exact token counts via tiktoken for OpenAI models, character-ratio heuristics for others. The math is documented and the margin of error is honest (±10% for non-OpenAI models). But I haven't personally validated those numbers against a real Anthropic or Gemini invoice, because I don't have active spending on those platforms right now.

That's a real limitation, and I'd rather say it clearly than pretend otherwise.

## Why I'm releasing it now

Because the core concept is useful and the code is solid enough to share. Waiting for perfect production coverage across every provider would mean waiting indefinitely.

The most useful thing that could happen from here is someone running llm-zip in a real production pipeline and submitting benchmark numbers — actual compression ratios, actual preservation scores, actual cost deltas. That data would make this tool more trustworthy than anything I can produce alone.

## What comes next

Honestly, I don't have a fixed roadmap. I'll keep improving llm-zip as I use it in my own internal workflows, and as inference costs continue to be a topic worth paying attention to. If a feature makes sense based on real usage, it'll get built.

If the community engages with the repo — benchmark contributions, bug reports, ideas — that'll shape where it goes too. I'm open to that.

But I won't promise a roadmap I haven't committed to. What I can promise is that the project is maintained with care, and that honesty about what it does and doesn't do will always be part of it.

— FinkTech
