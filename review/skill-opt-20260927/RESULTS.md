# Agent-first split + ICD retrieval demo — 2026-09-27

```
[scan] source_chars=20033 units=3 chapter_start_units=3
[plan] planner=agent strategy=agent_semantic warnings=[]
[icd] part 1: grade=icd-ok score=6/6 len=111 chars=6863 stored=6863
[icd] part 2: grade=icd-ok score=6/6 len=116 chars=6306 stored=6306
[icd] part 3: grade=icd-ok score=6/6 len=117 chars=6942 stored=6942
[cli] success=True planner=agent parts=3 source_deleted=False
[retrieve] query=台风夜灯船救援 -> picked=['part3', 'part1', 'part2'] overlaps=[('part3', 3), ('part1', 1), ('part2', 1), ('noise1', 0), ('noise2', 0)]
[verdict] PASS
```

原文为本次演示原创（《灯塔守望者》），计划 JSON 与拆分产物在本目录：agent_plan.json、mini_novel (part * of 3).md。
