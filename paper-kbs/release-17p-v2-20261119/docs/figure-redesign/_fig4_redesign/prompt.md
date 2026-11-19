{
  "type": "Academic journal figure — vertical single-column tiered retrieval workflow flowchart (portrait 2:3)",
  "goal": "A beautiful, decorated but publication-grade vertical flowchart for a Knowledge-Based Systems journal paper. Single-column portrait layout, top-to-bottom main flow with a short parallel fork, decision diamonds, and three distinct terminal outcomes. Clean vector look, crisp text, modern flat design with subtle decorations (small line icons inside nodes, stage number badges, soft drop shadows).",
  "canvas": {
    "aspect_ratio": "2:3 (portrait, tall)",
    "background": "pure white #FFFFFF",
    "outer_padding": "40px",
    "render_quality": "vector-clean, anti-aliased, sharp sans-serif labels (Helvetica/Inter), no blurry text"
  },
  "color_system": {
    "process_nodes": "soft blue fill #EAF2FB with 1.5px border #2C5F8A, bold dark-slate label #1E293B",
    "decision_diamonds": "soft rose fill #FDEEF2 with border #B5537A",
    "terminal_outcomes": "warm amber pill fill #FDF3E3 with border #C8963E",
    "exception_path": "dashed gray border #94A3B8, no fill",
    "arrows": "solid slate #475569 with small triangular heads; the exception arrow is dashed",
    "accents": "tiny line-icons in a single ink color #334155 (magnifier, database stack, funnel, document, checkmark, question mark, warning triangle)"
  },
  "flow_specification": {
    "top_start": "rounded pill 'Question / query rewrite' with a small magnifier icon",
    "stage1": "process box 'Select path(s): one or both' with badge 1, then a two-way parallel fork: left branch box 'Pinned collections: vector / two-stage search' (database icon), right branch box 'Catalogue / shelf: select documents' (book icon); both branches converge with merge arrows into",
    "stage2": "data box 'Candidate references (optional merge / cap)' with badge 2, tinted pale yellow #FEF9C3",
    "stage3": "decision diamond 'Use Laya gate?' — YES branch goes right into process box 'Fetch and score segments (Laya gate)' with funnel icon and badge 3, then rejoins; NO branch bypasses directly to",
    "stage4": "process box 'Read selected evidence' with document icon and badge 4, then decision diamond 'Review complete?' — NO goes right to terminal; YES continues to decision diamond 'Support found?'",
    "terminals": "three amber terminal pills at the bottom in a row: 'Answer with source references' (checkmark icon), 'Scoped not-found + blind spots' (question-mark icon), 'Incomplete review: scope + available evidence' (warning icon)",
    "exception": "a dashed gray rounded box on the side 'Any stage: failure / timeout' with a dashed arrow pointing into the incomplete-review terminal"
  },
  "layout_rules": "main flow centered vertically as a spine; forks/decisions branch to the right and rejoin; terminal pills bottom row evenly spaced; generous whitespace; all node text in English, 10-12pt equivalent, never truncated; stage badges are small circled numbers 1-4 in the top-left corner of their nodes",
  "style_keywords": "flat design, subtle drop shadow (2px, 10% opacity), rounded corners 8px, geometric precision, journal figure, minimal but decorated, high readability at 85mm column width"
}
