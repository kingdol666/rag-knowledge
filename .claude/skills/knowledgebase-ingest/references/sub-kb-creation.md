# Sub-KB Creation Procedure (A9 / O10)

> **Core principle**: when a KB accumulates enough documents spanning multiple distinct sub-domains, create focused sub-KBs to keep the Agentic-first retrieval sharp. A parent KB with overly broad documents forces the Agent to read individual descriptions -- sub-KBs let the Agent pinpoint the right sub-domain at a glance.

---

## A9a — Threshold Assessment

Sub-KB creation is triggered when **both** conditions are met:

```
IF doc_count >= 8:
    # Check if documents fall into >= 2 distinct sub-domains
    for each doc:
        kb_doc_read(kb_id, doc.doc_path, max_chars=500)
        classify doc's sub-domain from content (not filename)

    distinct_subdomains = unique(sub-domains)
    IF distinct_subdomains >= 2:
        -> Proceed to A9b (create sub-KBs)

ELSE:
    -> "KB has [doc_count] documents -- below 8-doc sub-KB threshold.
       Flagging for re-evaluation when collection grows."
```

**Key rules:**
- Sub-domain classification must be based on **content** (read via `kb_doc_read`), not filename
- Each sub-domain must have >= 2 documents to form a sub-KB
- The 8-doc threshold is absolute -- do not create sub-KBs below this count

---

## A9b — Create Sub-KBs

For each distinct sub-domain with >= 2 documents:

```
# Create sub-KB with parent_id linking to parent
sub_kb = kb_create(
    name="<ParentDomain>-<SubDomain>",        # e.g. "Thermal-Power-Coal-Mill"
    description="<from A4b template -- focused, 2-3 sentences>",
    parent_id=parent_kb.kb_id
)
```

**Sub-KB naming convention:**

```
<Parent-Domain>-<Sub-Domain>
# Examples:
#   Thermal-Power-Monitoring -> Thermal-Power-Coal-Mill
#   AI-ML-Research -> AI-ML-Time-Series-Forecasting
#   Wind-Power -> Wind-Turbine-Gearbox-Diagnostics
```

**Sub-KB description convention** (must be more precise than the parent KB description):

```
[Equipment/Sub-domain] specific research. [Methods used].
[Scenario the sub-KB addresses].
[N documents]. [Languages].
```

---

## A9c — Move Documents to Sub-KBs

```
for each doc in parent_kb that belongs to this sub-domain:
    kb_doc_move(doc.doc_path, sub_kb.kb_id)
```

Documents remain intact -- only their KB membership changes. Content, tags, and vector index entries follow the document.

---

## A9d — Update Parent KB Description

After creating sub-KBs and moving documents, **update the parent description** to mention its sub-structure:

```
kb_update(
    kb_id=parent_kb.kb_id,
    description="[Updated description]. Sub-KBs: [Sub-KB1], [Sub-KB2], [Sub-KB3]"
)
```

This is critical -- the parent description must tell the Agent "I am organized hierarchically, look at my sub-KBs" during Search Step 1 (Agentic KB scan).

---

## A9e — Verify Sub-KB Structure

```
kb_list()                          -> confirm sub-KBs appear
kb_get_documents(parent_kb_id)     -> confirm docs were moved OUT
kb_get_documents(sub_kb_id)        -> confirm docs moved IN
fs_get_tree(include_files=False, max_depth=3)  -> tree shows hierarchy
```

**Report to user:**

```
"The [Parent-KB] KB has grown to [N] documents across [M] sub-domains, so I have
organized it into focused sub-KBs:

+-- [Sub-KB-name]: [description snippet] ([N] docs)
+-- [Sub-KB-name]: [description snippet] ([N] docs)
+-- [Sub-KB-name]: [description snippet] ([N] docs]

This means future searches can pinpoint the right sub-domain at a glance.
Parent KB description updated to reference these sub-KBs."
```

---

## A9f — Reindex for Vector Search

After moving documents, reindex affected KBs:

```
kb_batch_index(kb_id=sub_kb.kb_id, force=True)
```

This ensures the moved documents' vector indices are rebuilt under the new KB scope.
