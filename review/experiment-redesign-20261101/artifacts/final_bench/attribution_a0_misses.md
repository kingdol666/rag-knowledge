# A0 未命中归因（35 qids）

| qid | class | routed KB | volume | char_offset | line | detail |
|---|---|---|---|---|---|---|
| G-gwr-2 | judge-miss | gov-zh | 政府工作报告2024 (part 1 of 1).md | 6738 | 42 |  |
| G-fyp-1 | judge-miss | gov-zh | 十四五规划纲要 (part 1 of 3).md | 3757 | 49 |  |
| F-hlm-2 | judge-miss | literature-zh | 红楼梦第03回.md | 6805 | 23 |  |
| F-hlm-3 | judge-miss | literature-zh | 红楼梦第05回.md | 3661 | 55 |  |
| F-pp-1 | window-truncation-miss | literature-en | pride_and_prejudice (part 24 of 27).md | 11994 | 262 | line>200_limit |
| F-md-1 | window-truncation-miss | literature-en | jane_eyre (part 25 of 37).md | 18608 | 339 | line>200_limit |
| S-bert-1 | window-truncation-miss | science-en | instructgpt.md | 90452 | 461 | char_offset>40000 |
| A-literature-en-metamorphosis | judge-miss | literature-en | metamorphosis (part 1 of 5).md | 212 | 12 |  |
| A-literature-en-war_of_the_worlds | judge-miss | literature-en | war_of_the_worlds (part 1 of 13).md | 5839 | 144 |  |
| A-literature-en-great_expectations | judge-miss | literature-en | great_expectations (part 1 of 37).md | 1262 | 173 |  |
| A-literature-en-huckleberry_finn | judge-miss | literature-en | huckleberry_finn (part 1 of 22).md | 45 | 1 |  |
| A-literature-en-odyssey | judge-miss | literature-en | odyssey (part 1 of 26).md | 35 | 1 |  |
| A-literature-en-sense_and_sensibility | judge-miss | literature-en | sense_and_sensibility (part 1 of 26).md | 31 | 1 |  |
| A-literature-en-anna_karenina | judge-miss | literature-en | anna_karenina (part 1 of 73).md | 31 | 1 |  |
| A-science-en-gpt3.pdf | judge-miss | science-en | gpt3.md | 22 | 1 |  |
| A-science-en-instructgpt.pdf | window-truncation-miss | science-en | gpt3.md | 123873 | 648 | char_offset>40000 |
| A-science-en-llama.pdf | judge-miss | science-en | llama.md | 2 | 1 |  |
| A-science-en-resnet.pdf | judge-miss | science-en | resnet.md | 2 | 1 |  |
| A-science-en-roberta.pdf | judge-miss | science-en | gpt3.md | 27979 | 147 |  |
| A-science-en-swin_transformer.pdf | judge-miss | science-en | swin_transformer.md | 2 | 1 |  |
| A-science-en-t5.pdf | judge-miss | science-en | t5.md | 59 | 1 |  |
| A-science-en-vae.pdf | judge-miss | science-en | vae.md | 16 | 1 |  |
| A-science-en-word2vec.pdf | window-truncation-miss | science-en | bert_pretraining.md | 45983 | 286 | char_offset>40000 |
| A-medicine-en-diabetes_management_revi | judge-miss | medicine-en | diabetes_management_review_oa (part 1 of 3).md | 1796 | 4 |  |
| A-medicine-en-alzheimer_biomarkers_rev | judge-miss | medicine-en | alzheimer_biomarkers_review_oa (part 1 of 3).md | 845 | 1 |  |
| A-medicine-en-cardiovascular_imaging_r | judge-miss | medicine-en | cardiovascular_imaging_review_oa (part 1 of 2).md | 1796 | 4 |  |
| A-medicine-en-mrna_vaccine_review | judge-miss | medicine-en | mrna_vaccine_review_oa (part 1 of 8).md | 803 | 1 |  |
| A-medicine-en-obesity_pharmacotherapy_ | judge-miss | medicine-en | obesity_pharmacotherapy_review_oa (part 1 of 2).md | 799 | 1 |  |
| A-medicine-en-telemedicine_outcomes_re | judge-miss | medicine-en | telemedicine_outcomes_review_oa (part 1 of 7).md | 2406 | 4 |  |
| A-medicine-en-tuberculosis_treatment_r | judge-miss | medicine-en | tuberculosis_treatment_review_oa (part 1 of 9).md | 803 | 1 |  |
| A-medicine-en-malaria_vaccine_review | judge-miss | medicine-en | malaria_vaccine_review_oa (part 1 of 4).md | 1808 | 4 |  |
| A-medicine-en-asthma_biologics_review | judge-miss | medicine-en | asthma_biologics_review_oa (part 1 of 6).md | 2258 | 4 |  |
| A-medicine-en-stroke_thrombolysis_revi | judge-miss | medicine-en | stroke_thrombolysis_review_oa (part 1 of 2).md | 766 | 1 |  |
| A-philosophy-en-walden | judge-miss | philosophy-en | walden (part 1 of 23).md | 116 | 12 |  |
| A-economics-en-on_liberty | judge-miss | economics-en | on_liberty (part 1 of 11).md | 55 | 6 |  |

## 计数

- routing-miss: 0
- window-truncation-miss: 5
- judge-miss: 30
- format-mismatch: 0
- not-found-on-disk: 0