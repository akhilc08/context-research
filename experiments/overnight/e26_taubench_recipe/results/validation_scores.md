## Pre-registered detectors

| domain | flagged sampled | flagged and labeled violation | unflagged sampled | unflagged but labeled violation | precision | recall in sample | recall weighted to population | kappa (sample) |
|---|---|---|---|---|---|---|---|---|
| retail | 16 | 15 | 16 | 2 | 0.938 | 0.882 | 0.535 | 0.812 |
| airline | 8 | 8 | 8 | 2 | 1.000 | 0.800 | 0.640 | 0.750 |
| all | 24 | 23 | 24 | 4 | 0.958 | 0.852 | 0.572 | 0.792 |

Per-detector precision (flagged items carrying that flag): basic_economy_change 2/2, book_limits 1/1, cancel_ineligible 2/2, confirm 8/9, insurance_not_offered 1/1, once 8/8, precond_reject 5/5

## Post-hoc corrected confirmation detector (exploratory; same sample, so population weights use the pre-registered strata and the recall estimate is approximate)

| domain | flagged sampled | flagged and labeled violation | unflagged sampled | unflagged but labeled violation | precision | recall in sample | recall weighted to population | kappa (sample) |
|---|---|---|---|---|---|---|---|---|
| retail | 15 | 15 | 17 | 2 | 1.000 | 0.882 | 0.566 | 0.875 |
| airline | 8 | 8 | 8 | 2 | 1.000 | 0.800 | 0.640 | 0.750 |
| all | 23 | 23 | 25 | 4 | 1.000 | 0.852 | 0.592 | 0.834 |

Per-detector precision (flagged items carrying that flag): basic_economy_change 2/2, book_limits 1/1, cancel_ineligible 2/2, confirm 7/7, insurance_not_offered 1/1, once 8/8, precond_reject 5/5
