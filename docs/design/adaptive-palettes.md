# Adaptive palettes

Mate's interface is deliberately quiet: off-white surfaces, deep slate text, hairline borders and one accent colour.
The accent is not fixed. It follows the kind of system the founder is building, and it changes when the plan changes.

## How it works

1. **Source text.** The current approved plan version (product category, one-liner, target customer, title). Before
   approval: the latest proposal. Before any proposal: the founder's starting idea and latest message.
2. **Classification.** Transparent keyword matching against eight system archetypes. The matched words are shown in
   the palette chip so the founder can see why the colour changed. No model call is involved.
3. **Generation.** Tokens are produced in OKLCH (Björn Ottosson's Oklab in polar form), so equal lightness steps look
   alike across hues and every archetype gets comparable visual weight.
4. **Verification.** Each token pair has a WCAG 2.x contrast target (4.5:1 for text, 3:1 for focus rings, control
   borders and economic stripes). Colours are darkened in code until they pass; `tests/test_theme.py` checks every
   archetype in every state.
5. **State.** A stopped or pivoting venture keeps its hue but loses most of its chroma, so the workspace visibly
   rests until the founder reopens the discussion.

## Archetypes

| Archetype | Hue (OKLCH) | Why |
|---|---|---|
| No direction yet | 185 (teal) | Quiet default while the conversation does the work |
| Learning and education tools | 150 (green) | Long, repeated sessions; calm accent clearly separate from warning amber |
| Business operations software | 250 (blue) | Blue is the interactive colour in widely used business design systems such as IBM Carbon and Atlassian, so actions read as actions |
| Developer and technical tools | 278 (indigo) | Documentation-like reading; neutral surfaces with one saturated accent |
| Creative and content tools | 2 (rose) | Interface frames the user's own work; accent marks controls only |
| Digital commerce and marketplaces | 38 (coral) | Singles out the one primary step; kept below the expense amber's chroma |
| Community and social products | 212 (cyan) | Open, conversational; distinct from revenue green |
| Lifestyle and hobby products | 112 (olive) | Soft and low-chroma; avoids clinical palettes because health advice is out of scope |

## What is research and what is convention

- **Grounded:** WCAG contrast maths (computed, tested); OKLCH perceptual lightness; never relying on colour alone
  (every economic class also has an icon and a stripe pattern; every evidence class has an icon and a word).
- **Convention, not psychology:** the hue per archetype follows common practice for that kind of software. Mate
  makes no claims that a colour changes behaviour or trust. Live web research was not available when these were
  chosen; the mapping is meant to be revised with evidence (see the roadmap).

## Fixed semantic colours

Economic roles (revenue, expense, mixed, strategic, unknown) and evidence classes (VERIFIED, ESTIMATE, ASSUMPTION,
PROJECTION, MOCKED, UNKNOWN) keep the same colours in every palette, so "amber with diagonal hatching = expense"
means the same thing in every workspace.
