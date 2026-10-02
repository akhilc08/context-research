# E9 results (n = 216 events, model stealth/space-bunny-alpha)

Strict harmful label: 116/216; lenient: 190/216; gold-wrong: 109/216.

| signal | family | AUROC all [95% CI] | AUROC eval [95% CI] | thr (cal) | eval precision [CI] | eval recall [CI] | flag rate | calls | tokens/event | token ratio vs expensive |
|---|---|---|---|---|---|---|---|---|---|---|
| draft_agree_llm | drafts | 0.59 [0.52, 0.66] | 0.54 [0.43, 0.65] | 2.000 | 0.54 [0.45, 0.63] | 1.00 [0.94, 1.00] | 0.99 | 3 | 8524 | 0.210 |
| draft_agree_count | drafts | 0.54 [0.47, 0.62] | 0.48 [0.38, 0.58] | 5.000 | 0.54 [0.44, 0.64] | 0.86 [0.75, 0.93] | 0.86 | 3 | 8524 | 0.210 |
| draft_lexical | drafts_nocmp | 0.68 [0.61, 0.75] | 0.64 [0.53, 0.75] | 0.568 | 0.57 [0.46, 0.67] | 0.81 [0.69, 0.89] | 0.77 | 2 | 6837 | 0.168 |
| roundtrip_llm | roundtrip | 0.76 [0.70, 0.82] | 0.74 [0.65, 0.83] | 6.000 | 0.76 [0.61, 0.87] | 0.55 [0.42, 0.67] | 0.39 | 3 | 5879 | 0.145 |
| roundtrip_count | roundtrip | 0.61 [0.54, 0.68] | 0.62 [0.52, 0.72] | 2.000 | 0.54 [0.45, 0.63] | 0.98 [0.91, 1.00] | 0.97 | 3 | 5879 | 0.145 |
| self_report_risk | self | 0.62 [0.54, 0.68] | 0.59 [0.49, 0.70] | 4.000 | 0.53 [0.44, 0.63] | 0.97 [0.88, 0.99] | 0.97 | 1 | 3817 | 0.094 |
| self_report_count | self | 0.52 [0.49, 0.55] | 0.48 [0.45, 0.52] | 8.000 | 0.53 [0.43, 0.62] | 0.95 [0.86, 0.98] | 0.96 | 1 | 3817 | 0.094 |
| compression_ratio | free | 0.69 [0.62, 0.76] | 0.64 [0.53, 0.74] | 6.094 | 0.58 [0.47, 0.68] | 0.84 [0.73, 0.92] | 0.79 | 0 | 0 | 0.000 |
| summary_words_neg | free | 0.70 [0.63, 0.77] | 0.69 [0.58, 0.79] | -245.000 | 0.63 [0.52, 0.73] | 0.86 [0.75, 0.93] | 0.73 | 0 | 0 | 0.000 |
| kw_overlap_miss_mean | free | 0.73 [0.66, 0.79] | 0.71 [0.60, 0.81] | 0.314 | 0.54 [0.45, 0.63] | 0.98 [0.91, 1.00] | 0.97 | 0 | 0 | 0.000 |
| kw_overlap_miss_min | free | 0.50 [0.47, 0.53] | 0.49 [0.44, 0.53] | 0.833 | 0.54 [0.44, 0.63] | 0.97 [0.88, 0.99] | 0.96 | 0 | 0 | 0.000 |

Expensive check: 21 calls, 40608 tokens per event.
Always-flag baseline on eval split: precision 0.54, recall 1.00.

| signal | AUROC lenient | AUROC half-2 label | AUROC gold-wrong | Spearman with divergence score |
|---|---|---|---|---|
| draft_agree_llm | 0.61 | 0.56 | 0.62 | 0.24 |
| draft_agree_count | 0.43 | 0.47 | 0.56 | 0.10 |
| draft_lexical | 0.62 | 0.64 | 0.70 | 0.35 |
| roundtrip_llm | 0.65 | 0.68 | 0.77 | 0.50 |
| roundtrip_count | 0.49 | 0.53 | 0.62 | 0.21 |
| self_report_risk | 0.69 | 0.59 | 0.61 | 0.30 |
| self_report_count | 0.53 | 0.54 | 0.52 | 0.10 |
| compression_ratio | 0.64 | 0.68 | 0.69 | 0.40 |
| summary_words_neg | 0.67 | 0.68 | 0.70 | 0.41 |
| kw_overlap_miss_mean | 0.65 | 0.65 | 0.74 | 0.48 |
| kw_overlap_miss_min | 0.51 | 0.51 | 0.49 | -0.01 |

Exploratory: condition-only prior (style and budget rate from calibration split), eval AUROC 0.75 [0.65, 0.83].

Exploratory: within-condition AUROC (pair-weighted over style x budget cells): {"draft_agree_llm": 0.56, "draft_agree_count": 0.53, "draft_lexical": 0.56, "roundtrip_llm": 0.68, "roundtrip_count": 0.56, "self_report_risk": 0.54, "self_report_count": 0.51, "compression_ratio": 0.54, "summary_words_neg": 0.5, "kw_overlap_miss_mean": 0.54, "kw_overlap_miss_min": 0.47}

Noise: {"full_vs_full_disagree_by_probe": {"rule0": 32, "rule1": 36, "fact": 0, "approach": 14, "goal": 33}, "summ_vs_summ_disagree_by_probe": {"rule0": 52, "rule1": 57, "fact": 2, "approach": 33, "goal": 11}, "events_any_full_self_disagree": 98, "half_label_kappa": 0.3333333333333334, "half_label_agree": 163, "ceiling_auc_h1_predicts_h2": 0.7775995246583481, "ceiling_auc_h1_predicts_h2_ci": [0.7175925925925926, 0.8371651785714286], "h2_base_rate": 165}

Per-probe TV=1 counts: {"rule0": 46, "rule1": 47, "fact": 23, "approach": 52, "goal": 48}

Strict by condition: {"narrative/w60": [36, 36], "narrative/w120": [27, 36], "narrative/w250": [14, 36], "structured/w60": [15, 36], "structured/w120": [15, 36], "structured/w250": [9, 36]}

Spearman among primary signals: {"draft_agree_llm~roundtrip_llm": 0.23, "draft_agree_llm~self_report_risk": 0.2, "draft_agree_llm~compression_ratio": 0.34, "draft_agree_llm~kw_overlap_miss_mean": 0.23, "roundtrip_llm~self_report_risk": 0.28, "roundtrip_llm~compression_ratio": 0.36, "roundtrip_llm~kw_overlap_miss_mean": 0.45, "self_report_risk~compression_ratio": 0.47, "self_report_risk~kw_overlap_miss_mean": 0.39, "compression_ratio~kw_overlap_miss_mean": 0.61}
