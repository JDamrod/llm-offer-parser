# llm-offer-parser

LLM-based extraction of casino offer terms from free-form advertiser messages into a ready-to-send Telegram message.

Python · Gemini API (OpenAI-compatible client) · Pydantic · pytest · evaluation set

## Why I built it

I work in affiliate marketing. Advertisers send offer conditions (GEO, CPA, cap, baseline, wager, KPI, ...) in many different formats, and I used to copy the values into a form by hand (my other tool, Offer Generator). Here an LLM reads the raw message and extracts the fields. If a required field is missing, it asks a clarification question instead of guessing.

## How it works

```
raw message ──► LLM ──► JSON ──► Pydantic validation ──► action

new_offer              ──► build_offer_text ──► Telegram message
need_more_information  ──► question to the user ──► the answer goes back to the LLM
not_new_offer          ──► ignored
```

- **System prompt** (`offer_parser/prompts/system_prompt.txt`) with rules for every field: CPA currency format, allowed traffic sources, baseline vs. mindep, what belongs to KPI or comment, and so on.
- **Validation:** the model's JSON is checked with Pydantic (`extra="forbid"`, `Literal` actions). A wrong answer gives a clear error instead of a crash.
- **Clarification loop:** the whole conversation history is kept, so the model sees the original message and the user's answer.
- **Formatter:** `offer_formatter.py` builds the Telegram HTML text and sends it to my chat.

Example input:

```
Royal Casino | IT | CPA 140 EUR | Min dep 25 EUR | FTD cap 20 | ASO
```

Result (in Telegram the title and the cap are bold):

```
🇮🇹 Royal Casino | IT [ASO] Slot — CPA 140 EUR (mindep 25 EUR, 20ftd)
```

## Evaluation

`eval/cases.json` has 37 invented messages (no real advertiser data): 27 new offers, 5 offers with missing required fields and 5 messages that are not offers. They include tricky cases: baseline vs. mindep, "not paid" lists that must not become KPI, `$`/`€`/`£` symbols, several GEOs, abbreviations like `BL`.

Run it with `python -m eval.run` (it calls the API and takes a few minutes).

Result of the first run (JSON mode, `gemini-3.5-flash-lite`, 2026-11-13):

| Metric | Result |
|---|---|
| Cases with every field correct | **35 / 37** (94.6%) |
| Correct action | 36 / 37 (97.3%) |
| Correct non-empty fields | 135 / 139 (97.1%) |
| Invented values (expected empty, got a value) | 0 |

Scoring rules: a case counts only if all fields are correct. Empty fields are not counted as "correct for free", so the model cannot score by returning nothing. Small differences (letter case, a final period, list order) are ignored. The raw result is in `eval/results/`.

Two failures in that run:

- `c12`: for `Mindep 10 EUR` the model returned `10 USD`, apparently taking the currency from the CPA.
- `c27`: `GEO` written as `NO` (Norway) gave a wrong action. I have not checked the reason; my guess is that the model read it as the word "no".

Limits of this number: one run at the default temperature, 37 cases that I wrote together with the prompt (a development set, not an independent test), English messages only.

## Tests

```
pytest
```

8 tests that need no API key: response parsing, JSON cleaning and the clarification loop with a fake LLM. The formatter comes from my Offer Generator tool, where it has its own tests.

## Setup

Python 3.10 or newer.

```
git clone https://github.com/JDamrod/llm-offer-parser.git
cd llm-offer-parser
python -m venv .venv
.venv\Scripts\activate          # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:

```
GEMINI_API_KEY=...
TELEGRAM_TOKEN=...
OWNER_ID=...
```

Run from the project root:

```
python -m offer_parser.main
```

Paste the message and finish the input with Ctrl+Z, Enter (Windows) or Ctrl+D (Linux/macOS). The offer is sent to the Telegram chat from `OWNER_ID`.

## Project structure

```
offer_parser/
  main.py              LLM call, Pydantic models, clarification loop
  offer_formatter.py   Telegram message builder and sender
  prompts/system_prompt.txt
eval/
  cases.json           37 test messages with expected answers
  run.py               evaluation script
  results/             saved results
tests/test_main.py
```

## Why it is built this way

- **Pydantic for validation:** the LLM can return anything, so the answer is checked before it reaches the formatter.
- **Evaluation separate from pytest:** model output is not deterministic and calls cost money, so unit tests use a fake LLM and the real model is measured by `eval/run.py` with a percentage instead of pass/fail.
- **A clarification question instead of a guess:** the prompt forbids inventing missing name, GEO or CPA.

## Limitations and next steps

- The model currently answers in JSON text. Next I plan to switch to tool calling and run the same 37 cases to compare both approaches.
- Fix the two known failures and add messages closer to real ones (written separately from the prompt) as an independent test set.
- The sender uses my own Telegram chat; it is a personal tool, not a service.

## AI assistance

I used an AI assistant (Claude) as a coding reviewer: discussing the structure and drafting the prompt, test cases and evaluation script, which I then ran, checked and adjusted. All results above come from my own runs.

## License

MIT
