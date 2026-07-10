# MU-TCM v3 Synthetic Admission Report

- rule: `{'path': '/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_rule_pool.npz', 'n': 160, 'counts': {'healthy': 80, 'worn': 80}}`
- random_open_loop: `{'path': '/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_random_open_loop_pool.npz', 'n': 160, 'counts': {'healthy': 80, 'worn': 80}}`
- LLM_synthetic: `{'path': '/Users/jianyang/Desktop/学校相关课程/回所/论文/合成数据sci/breeze_full-2/breeze/results/mutcm_v3_llm_inner_2026-07-09/mutcm_v3_llm_synthetic_pool.npz', 'n': 121, 'counts': {'healthy': 60, 'worn': 61}, 'api_requests_total': 51}`

LLM_synthetic admission uses inner-train class statistics, feature-axis distance, class-identity distance, and nearest-neighbor anti-copy distance.
No-API rule/random pools are baseline generators; they are checked for shape/finite values and are not used as admission-tuning feedback.
