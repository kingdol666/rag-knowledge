# KB capability live probe (management + retrieval full flow)

- Timestamp UTC: `2026-10-21T03:07:38.677759+00:00`
- Parent/child KB: `ZZ-Cap-Parent-20261021-110738` / `ZZ-Cap-Child-20261021-110738` (deleted afterwards)
- Overall: **PASS**

| Step | Result | Note |
|---|---|---|
| kb_project_status | PASS |  |
| fs_get_tree | PASS |  |
| kb_create_parent | PASS |  |
| kb_create_child_with_parent | PASS |  |
| kb_list_shows_tree | PASS |  |
| kb_doc_create | PASS |  |
| doc_visible_in_catalog | PASS |  |
| kb_index_document | PASS |  |
| kb_doc_update_meta | PASS |  |
| kb_doc_update_content | PASS |  |
| kb_doc_update_tags | PASS |  |
| kb_doc_get_by_tag | PASS |  |
| vector_child_direct | PASS |  |
| vector_parent_recursive | PASS |  |
| two_stage_parent | PASS |  |
| keyword_metadata_scan | PASS |  |
| laya_judge_reference_mode | PASS |  |
| vector_negative_control | PASS |  |
| kb_find_duplicates | PASS |  |
| kb_doc_move_with_hygiene | PASS |  |
| moved_doc_visible_in_parent | PASS |  |
| post_move_vector_clean | PASS |  |
| catalog_grouped_view | PASS |  |
| kb_graph_build_task | PASS |  |
| kb_graph_document | PASS |  |
| experience_create | PASS |  |
| experience_search_global | PASS |  |
| kb_reindex_force | PASS |  |
| experience_delete | PASS |  |
| kb_doc_delete | PASS |  |
| kb_delete_child | PASS |  |
| kb_delete_parent | PASS |  |
| cleanup_verified | PASS |  |

Full trace: `result.json`.
