## Main Flow: Create a New Skill

### Step 0: Confirm the character family

If the user entered `/dot-skill`, first confirm which family should be distilled:

1. `colleague`
2. `relationship`
3. `celebrity`

If the host already passed an explicit family, lock the character family immediately.

If the current family is `celebrity`, also confirm the research profile:

1. `budget-friendly`
2. `budget-unfriendly`

Default to `budget-friendly`. Only switch to `budget-unfriendly` when the user explicitly wants deeper research, higher confidence, or accepts a slower and more expensive distillation pass.

### Step 1: Basic Info Collection

Choose the intake prompt by character family:

- `colleague` → `prompts/intake.md`
- `relationship` → `prompts/relationship/intake.md`
- `celebrity` → `prompts/celebrity/intake.md`

For `colleague` and `relationship`, ask only 3 questions.
For `celebrity`, use the 4-question intake in `prompts/celebrity/intake.md`; the fourth question must confirm `research_profile`.

The default 3 base questions are:

1. **Alias / Codename** (required)
2. **Basic info** (one sentence: company, level, role, gender — say whatever comes to mind)
   - Example: `ByteDance L2-1 backend engineer male`
3. **Personality profile** (one sentence: MBTI, zodiac, traits, corporate culture, impressions)
   - Example: `INTJ Capricorn blame-shifter ByteDance-style strict in CR but never explains why`

Everything except the alias can be skipped. Summarize and confirm before moving to the next step.

### Step 2: Source Material Import

Ask the user how they'd like to provide materials:

```
How would you like to provide source materials?

  [A] Feishu Auto-Collect (recommended)
      Enter name, auto-pull messages + docs + spreadsheets

  [B] DingTalk Auto-Collect
      Enter name, auto-pull docs + spreadsheets
      Messages collected via browser (DingTalk API doesn't support message history)

  [C] Feishu Link
      Provide doc/Wiki link (browser session or MCP)

  [D] Upload Files
      PDF / images / exported JSON / email .eml

  [E] Paste Text
      Copy-paste text directly

Can mix and match, or skip entirely (generate from manual info only).
```

---

#### Option A: Feishu Auto-Collect (Recommended)

First-time setup:
```bash
python3 tools/feishu_auto_collector.py --setup
```

**Group chat collection** (uses tenant_access_token, bot must be in the group):
```bash
python3 tools/feishu_auto_collector.py \
  --name "{name}" \
  --output-dir ./knowledge/{slug} \
  --msg-limit 1000 \
  --doc-limit 20
```

**Private chat (P2P) collection** (requires user_access_token + p2p chat_id):

Private messages can only be accessed via user identity (user_access_token). App identity cannot access private chats.

**Prerequisites**:

The user needs to provide:
1. **Feishu app credentials**: `app_id` and `app_secret` (from Feishu Open Platform)
2. **User scopes**: The app must have these user scopes enabled:
   - `im:message` — read/send messages as user
   - `im:chat` — read chat list as user
3. **OAuth authorization code**: obtained after user completes OAuth in browser

If the user is missing any of these, guide them through setup. Don't assume anything is pre-configured.

**Getting user_access_token**:

Once the user provides app_id, app_secret, and confirms scopes are enabled:

1. Generate the OAuth URL for them:
   ```
   https://open.feishu.cn/open-apis/authen/v1/authorize?app_id={APP_ID}&redirect_uri=http://www.example.com&scope=im:message%20im:chat
   ```
   > ⚠️ The redirect_uri must be added in the app's "Security Settings → Redirect URLs"

2. User opens URL, logs in, authorizes
3. Page redirects to `http://www.example.com?code=xxx`, user copies the code
4. Exchange code for token:
   ```bash
   python3 tools/feishu_auto_collector.py --exchange-code {CODE}
   ```
   Or write a Python script to call the Feishu API directly:
   ```python
   # 1. Get app_access_token
   POST https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal
   Body: {"app_id": "xxx", "app_secret": "xxx"}
   
   # 2. Exchange code for user_access_token
   POST https://open.feishu.cn/open-apis/authen/v1/oidc/access_token
   Header: Authorization: Bearer {app_access_token}
   Body: {"grant_type": "authorization_code", "code": "xxx"}
   ```

**Getting the p2p chat_id**:

Users typically don't know their chat_id. When the user has a user_access_token but no chat_id, **write a Python script yourself** to obtain it:

- **Method**: Send a message to the other user's open_id — the response includes the chat_id
  ```python
  POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id
  Header: Authorization: Bearer {user_access_token}
  Body: {"receive_id": "{target_open_id}", "msg_type": "text", "content": "{\"text\":\"hello\"}"}
  # The chat_id in the response is the p2p chat ID
  ```
- **Important**: `GET /im/v1/chats` does NOT return p2p chats — this is a Feishu API limitation, not a permission issue. Do not try to use it for finding private chats.
- If the user doesn't know the target's open_id, use tenant_access_token to search contacts:
  ```python
  GET https://open.feishu.cn/open-apis/contact/v3/scopes
  # Returns open_ids of all users visible to the app
  ```

**Running collection**:

Once you have user_access_token and chat_id:
```bash
python3 tools/feishu_auto_collector.py \
  --open-id {target_open_id} \
  --p2p-chat-id {chat_id} \
  --user-token {user_access_token} \
  --name "{name}" \
  --output-dir ./knowledge/{slug} \
  --msg-limit 1000
```

**Flexibility principle**: The above API calls don't have to go through the collector script. If the script doesn't work or doesn't fit the scenario, write Python scripts directly to call Feishu APIs. Key API reference:
- Get token: `POST /auth/v3/app_access_token/internal`, `POST /authen/v1/oidc/access_token`
- Send message (get chat_id): `POST /im/v1/messages?receive_id_type=open_id`
- Fetch messages: `GET /im/v1/messages?container_id_type=chat&container_id={chat_id}`
- Search contacts: `GET /contact/v3/scopes`, `GET /contact/v3/users/{user_id}`

Auto-collected content:
- Group chats: messages sent by them (system messages and stickers filtered)
- Private chats: full conversation with both parties (for context understanding)
- Feishu docs and Wikis they created/edited
- Related spreadsheets (if accessible)

After collection, `Read` the output files:
- `knowledge/{slug}/messages.txt` → messages (group + private)
- `knowledge/{slug}/docs.txt` → document content
- `knowledge/{slug}/collection_summary.json` → collection summary

If collection fails, diagnose the error and attempt to fix it. Common issues:
- Group chat: bot not added to the group
- Private chat: user_access_token expired (2-hour TTL, refresh with refresh_token)
- Insufficient permissions: guide user to enable scopes and re-authorize
- Or switch to Option B/C

---

#### Option B: DingTalk Auto-Collect

First-time setup:
```bash
python3 tools/dingtalk_auto_collector.py --setup
```

Then enter the name:
```bash
python3 tools/dingtalk_auto_collector.py \
  --name "{name}" \
  --output-dir ./knowledge/{slug} \
  --msg-limit 500 \
  --doc-limit 20 \
  --show-browser   # add this flag on first use to complete DingTalk login
```

Collected content:
- DingTalk docs and knowledge bases they created/edited
- Spreadsheets
- Messages (⚠️ DingTalk API doesn't support message history — auto-switches to browser scraping)

After collection, `Read`:
- `knowledge/{slug}/docs.txt`
- `knowledge/{slug}/bitables.txt`
- `knowledge/{slug}/messages.txt`

If message collection fails, prompt user to upload chat screenshots.

---

#### Option D: Upload Files

- **PDF / Images**: `Read` tool directly
- **Feishu message JSON export**:
  ```bash
  python3 tools/feishu_parser.py --file {path} --target "{name}" --output /tmp/feishu_out.txt
  ```
  Then `Read /tmp/feishu_out.txt`
- **Email files .eml / .mbox**:
  ```bash
  python3 tools/email_parser.py --file {path} --target "{name}" --output /tmp/email_out.txt
  ```
  Then `Read /tmp/email_out.txt`
- **Markdown / TXT**: `Read` tool directly

---

#### Option C: Feishu Link

When the user provides a Feishu doc/Wiki link, ask which method to use:

```
Feishu link detected. Choose read method:

  [1] Browser Method (recommended)
      Reuses your local Chrome login session
      ✅ Works with internal docs requiring permissions
      ✅ No token configuration needed
      ⚠️  Requires Chrome + playwright installed locally

  [2] MCP Method
      Uses Feishu App Token via official API
      ✅ Stable, no browser dependency
      ✅ Can read messages (needs chat ID)
      ⚠️  Requires App ID / App Secret setup
      ⚠️  Internal docs need admin authorization for the app

Choose [1/2]:
```

**Option 1 (Browser)**:
```bash
python3 tools/feishu_browser.py \
  --url "{feishu_url}" \
  --target "{name}" \
  --output /tmp/feishu_doc_out.txt
```
First use will open a browser window for login (one-time).

**Option 2 (MCP)**:

First-time setup:
```bash
python3 tools/feishu_mcp_client.py --setup
```

Then read directly:
```bash
python3 tools/feishu_mcp_client.py \
  --url "{feishu_url}" \
  --output /tmp/feishu_doc_out.txt
```

Read messages (needs chat ID, format `oc_xxx`):
```bash
python3 tools/feishu_mcp_client.py \
  --chat-id "oc_xxx" \
  --target "{name}" \
  --limit 500 \
  --output /tmp/feishu_msg_out.txt
```

Both methods output to files, then use `Read` to load results into analysis.

---

#### Option E: Paste Text

User-pasted content is used directly as text material. No tools needed.

---

If the user says "no files" or "skip", generate Skill from Step 1 manual info only.

### Step 3: Analyze Source Material

First resolve the execution matrix for the selected character family:

| character | intake | persona analyzer | persona builder | merger | storage root |
|-----------|--------|------------------|-----------------|--------|--------------|
| `colleague` | `prompts/intake.md` | `prompts/persona_analyzer.md` | `prompts/persona_builder.md` | `prompts/merger.md` | `./skills/colleague/{slug}` |
| `relationship` | `prompts/relationship/intake.md` | `prompts/relationship/persona_analyzer.md` | `prompts/relationship/persona_builder.md` | `prompts/relationship/merger.md` | `./skills/relationship/{slug}` |
| `celebrity` | `prompts/celebrity/intake.md` | `prompts/celebrity/persona_analyzer.md` | `prompts/celebrity/persona_builder.md` | `prompts/celebrity/merger.md` | `./skills/celebrity/{slug}` |

Shared across all families:
- Work analyzer: `prompts/work_analyzer.md`
- Work builder: `prompts/work_builder.md`
- Correction handler: `prompts/correction_handler.md`

If the current family is `celebrity`, run the research subflow before analysis.

### celebrity / budget-friendly

1. Read `prompts/celebrity/research.md` and follow its **6-dimension parallel collection strategy**
2. Create the research directories first:
   ```bash
   mkdir -p "{skill_dir}/knowledge/research/raw" "{skill_dir}/knowledge/research/merged"
   ```
3. Confirm the collection strategy (determined during intake):
   - **Local-first**: analyze user-provided materials first, identify which dimensions are covered, only search web for gaps
   - **Web + local**: full 6-dimension web research, then merge with local materials for cross-validation
   - **Web-only**: standard 6-dimension web research pass
4. If the user explicitly provided a processable video URL or subtitle source, and the result will not be stored as a long transcript:
   ```bash
   bash tools/research/download_subtitles.sh "{url}" "{skill_dir}/knowledge/subtitles"
   python3 tools/research/srt_to_transcript.py "{subtitle_file}" "{skill_dir}/knowledge/transcripts/{name}.txt"
   ```
5. Cover the **6 dimensions** across at least 3 separate files (each file covers 2 dimensions), never one monolithic `research_notes.md`:
   - `knowledge/research/raw/01_core_profile.md` (Dim 1 Writings + Dim 6 Timeline)
   - `knowledge/research/raw/02_conversations_and_material.md` (Dim 2 Conversations + Dim 4 Decisions)
   - `knowledge/research/raw/03_expression_and_reception.md` (Dim 3 Expression DNA + Dim 5 External Views)
6. Research must follow **taste principles** (see research prompt):
   - Long-form > snippets, controversy > consensus, change > fixity, firsthand > secondhand
   - **Source blacklist** — never cite: Zhihu, WeChat official accounts, Baidu Baike, content farms, AI-generated bios
   - **Source hierarchy**: user local materials > first-person works > long interviews > decision records > short-form firsthand > external analysis > secondhand summaries
7. Merge the research notes:
   ```bash
   python3 tools/research/merge_research.py "{skill_dir}"
   ```
   Output: `knowledge/research/merged/summary.md`
8. Read `knowledge/research/merged/summary.md` and confirm:
   - `Files scanned >= 3`
   - `Unique URLs >= 2`
   - `Potential long quote lines = 0`
   - URLs in notes are actual inspected pages, not platform roots, search/topic pages, or placeholder paths
   If these do not hold, extend the research notes before continuing or explicitly record the collection limits.
9. **Quality checkpoint (Phase 1.5)**: before entering analysis, show the user a structured collection summary:
   ```
   ┌──────────────────────────────┬──────────┬─────────────────────────────┐
   │ Dimension                    │ Sources  │ Key Finding                 │
   ├──────────────────────────────┼──────────┼─────────────────────────────┤
   │ 1 Writings                   │ N        │ [core thesis / gap]         │
   │ 2 Conversations              │ N        │ [key pattern / gap]         │
   │ 3 Expression DNA             │ N        │ [style marker / gap]        │
   │ 4 Decisions                  │ N        │ [decision pattern / gap]    │
   │ 5 External Views             │ N        │ [outside view / gap]        │
   │ 6 Timeline                   │ N        │ [trajectory / gap]          │
   ├──────────────────────────────┼──────────┼─────────────────────────────┤
   │ Contradictions               │ N        │ [summary]                   │
   │ Thin dimensions              │ [list]   │ Backfill plan: [plan]       │
   │ Cold figure?                 │ yes/no   │                             │
   └──────────────────────────────┴──────────┴─────────────────────────────┘
   ```
   Wait for user confirmation before continuing. If the user flags issues or wants more depth, extend research first.
10. **Cold figure detection**: if total sources < 10, apply the cold figure protocol:
    - Limit mental models to 2–3
    - Mark thin models as "based on limited information"
    - Expand the honest boundaries section
    - Tell the user what additional material would improve quality
11. Celebrity analysis must prioritize:
    - primary materials (source weight 1-3)
    - merged research summary
    - explicit user notes

### celebrity / budget-unfriendly

1. First read:
   - `prompts/celebrity/budget_unfriendly/research.md`
   - `references/celebrity_budget_unfriendly_framework.md`
2. Create the research directories first:
   ```bash
   mkdir -p "{skill_dir}/knowledge/research/raw" "{skill_dir}/knowledge/research/merged" "{skill_dir}/knowledge/research/reviews"
   ```
3. Confirm the collection strategy (determined during intake): local-first / web+local / web-only
4. Build the **six-track research set** as independent files (never merged, never clone observations):
   - `knowledge/research/raw/01_writings.md` (Dim 1: Writings / systematic thought)
   - `knowledge/research/raw/02_conversations.md` (Dim 2: Conversations under pressure)
   - `knowledge/research/raw/03_expression_dna.md` (Dim 3: Linguistic fingerprint)
   - `knowledge/research/raw/04_decisions.md` (Dim 4: Behavior and choices)
   - `knowledge/research/raw/05_external_views.md` (Dim 5: External views and criticism)
   - `knowledge/research/raw/06_timeline.md` (Dim 6: Cognitive trajectory)
5. Research must follow **taste principles + source blacklist + source hierarchy** (see research prompt). Every evidence item must carry a source weight (1-7) annotation.
6. Merge the research notes:
   ```bash
   python3 tools/research/merge_research.py "{skill_dir}"
   ```
7. Read `knowledge/research/merged/summary.md` and confirm the minimum floor:
   - `Files scanned >= 6`
   - `Unique URLs >= 8`
   - `Primary-source markers >= 3`
   - `Source metadata blocks >= 6`
   - `Contradiction bullets >= 6`
   - `Inference bullets >= 6`
   - `Potential long quote lines = 0`
   - `Track coverage count = 6`
   - URLs in notes are actual inspected pages, not platform roots, search/topic pages, or placeholder paths
   If these do not hold, keep filling the weak tracks before continuing to any review stage.
8. **Quality checkpoint (Phase 1.5)**: before entering audit, show the user a structured collection summary (with primary-source ratio, contradiction count, candidate mental models, known-answer candidates, thin dimensions, cold figure assessment). Wait for user confirmation before continuing.
9. Then read:
   - `prompts/celebrity/budget_unfriendly/audit.md`
   - `prompts/celebrity/budget_unfriendly/synthesis.md`
   - `references/celebrity_budget_unfriendly_template.md`
10. First write `knowledge/research/reviews/research_audit.md`
    - The audit must produce an explicit `PASS / FAIL`
    - The audit must verify: source hierarchy compliance (no blacklisted sources), primary-source ratio > 50%, taste principle compliance, cold figure assessment
    - If the audit says `FAIL`, follow the Backfill Tasks before synthesis
11. **Extraction checkpoint (Phase 2.5)**: after audit PASS, show the user a summary of candidate mental models (with triple-gate verdict, evidence anchors, failure modes). Confirm reasonableness before synthesis.
12. Then write `knowledge/research/reviews/synthesis.md`
    - Apply the triple gate to candidate mental models:
      - cross-context recurrence
      - generative power
      - exclusivity
    - Also extract intellectual genealogy seeds (influenced by / diverged from) and Agentic Protocol seeds (the dimensions this person would investigate when facing a novel question)
13. Then use `prompts/celebrity/budget_unfriendly/validation.md` to write:
    - `knowledge/research/reviews/validation.md`
    - Validation must produce an explicit `PASS / FAIL`
    - Validation must perform: known-answer check (≥2 questions) + edge-case check (1 question) + voice check (100-word blind test) + copyright check + Agentic Protocol check
    - If validation says `FAIL`, revise the draft before continuing
14. Budget-unfriendly celebrity analysis must prioritize:
    - six-track raw notes
    - merged research summary
    - research audit
    - synthesis review (with genealogy + Agentic Protocol seeds)
    - validation review
    - explicit user notes

Shared rules for both celebrity profiles:

- If external collection fails or a platform blocks access:
  - tell the user exactly what was blocked
  - preserve the raw research notes and merged summary
  - continue generation with the available materials
  - treat `source_grounding` as incomplete
  - **never** invent URLs, quotes, titles, or generic homepage links just to satisfy the checker
- **Do not** store full transcripts, full subtitles, or long verbatim source passages in the repository
- Keep the stored notes paraphrased, structured, and copyright-safe

Once the family is resolved, analyze along two tracks:

**Track A (Work Skill)**:
- Refer to `prompts/work_analyzer.md`
- Extract: responsible systems, technical standards, workflow, output preferences, experience
- For `celebrity`, interpret `work` as methods, judgment frameworks, and decision patterns rather than literal job scope

**Track B (Persona)**:
- Use the family-specific persona analyzer
- If `celebrity` with `research_profile=budget-unfriendly`, use:
  - `prompts/celebrity/budget_unfriendly/persona_analyzer.md`
- Translate user-provided tags into concrete behavior rules
- Extract from materials: communication style, decision patterns, interpersonal behavior
- For `celebrity`, retain:
  - mental models
  - decision heuristics
  - expression DNA
  - contradictions
  - honest boundaries

### Step 4: Generate and Preview

Use `prompts/work_builder.md` to generate Work content.
Use the family-specific persona builder to generate Persona content.

Mapping:
- `colleague` → `prompts/persona_builder.md`
- `relationship` → `prompts/relationship/persona_builder.md`
- `celebrity` → `prompts/celebrity/persona_builder.md`
- `celebrity` + `budget-unfriendly` → `prompts/celebrity/budget_unfriendly/persona_builder.md`

Show the user a summary (5-8 lines each), ask:
```
Work Skill Summary:
  - Responsible for: {xxx}
  - Tech stack: {xxx}
  - CR focus: {xxx}
  ...

Persona Summary:
  - Core personality: {xxx}
  - Communication style: {xxx}
  - Decision pattern: {xxx}
  ...

Confirm generation? Or need adjustments?
```

### Step 5: Write Files

After user confirmation, do not hand-build a `skills/colleague/{slug}`-style tree. Always go through the writer:

1. Resolve the current storage root:
   - `colleague` → `./skills/colleague`
   - `relationship` → `./skills/relationship`
   - `celebrity` → `./skills/celebrity`
2. Use the `Write` tool to create three temporary files:
   - `/tmp/dot_skill_{slug}_meta.json`
   - `/tmp/dot_skill_{slug}_work.md`
   - `/tmp/dot_skill_{slug}_persona.md`
3. The temporary meta file must include at least:
   - `name`
   - `display_name`
   - `character`
   - `research_profile` (required when `character=celebrity`)
   - `classification.language` (must match the user's language, for example `zh-CN` or `en`)
   - `profile`
   - `tags`
   - `knowledge_sources`
4. Then call:
   ```bash
   python3 tools/skill_writer.py \
     --action create \
     --character {character} \
     --research-profile {research_profile} \
     --slug {slug} \
     --name "{name}" \
     --meta /tmp/dot_skill_{slug}_meta.json \
     --work /tmp/dot_skill_{slug}_work.md \
     --persona /tmp/dot_skill_{slug}_persona.md \
     --base-dir {resolved_base_dir}
   ```
5. This command will generate:
   - `SKILL.md`
   - `work.md`
   - `persona.md`
   - `work_skill.md`
   - `persona_skill.md`
   - `manifest.json`
   - `meta.json`
   - To install the generated role skill into a host, append the relevant flag:
     - Claude Code: `--install-claude-skill`
     - OpenClaw: `--install-openclaw-skill`
     - Codex: `--install-codex-skill`
     - Claude Code on Windows: optionally add `--install-claude-command-shim`
6. If the current family is `celebrity`, run a quality check after creation:
   ```bash
   python3 tools/research/quality_check.py "{resolved_base_dir}/{slug}/SKILL.md" --profile {research_profile}
   ```
7. If `source_grounding` still fails for a `celebrity` skill:
   - you may add honest limitation notes and a grounded source summary
   - only add URLs when they are real, specific, and traceable sources
   - **never** use site roots, topic pages, search pages, or other generic links as fake grounding
   - if no verified external sources exist, keep the FAIL state and explain what source material is still missing

When reporting success, return the correct family-specific location instead of assuming colleague storage.

---

