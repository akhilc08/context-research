## Pre-registered detectors

| domain | flagged sampled | flagged and labeled violation | unflagged sampled | unflagged but labeled violation | precision | recall in sample | recall weighted to population | kappa (sample) |
|---|---|---|---|---|---|---|---|---|
| retail | 40 | 31 | 40 | 2 | 0.775 | 0.939 | 0.761 | 0.725 |
| airline | 20 | 16 | 20 | 3 | 0.800 | 0.842 | 0.747 | 0.650 |
| all | 60 | 47 | 60 | 5 | 0.783 | 0.904 | 0.755 | 0.700 |

Per-detector precision (flagged items carrying that flag): auth 4/4, bag_remove 1/1, book_limits 2/2, cancel_flown 3/3, cancel_ineligible 4/4, confirm 24/36, insurance_not_offered 3/3, od_change 1/1, once 10/10, precond_reject 5/6

## Post-hoc corrected confirmation detector (exploratory; same sample, so population weights use the pre-registered strata and the recall estimate is approximate)

| domain | flagged sampled | flagged and labeled violation | unflagged sampled | unflagged but labeled violation | precision | recall in sample | recall weighted to population | kappa (sample) |
|---|---|---|---|---|---|---|---|---|
| retail | 33 | 29 | 47 | 4 | 0.879 | 0.879 | 0.679 | 0.794 |
| airline | 20 | 16 | 20 | 3 | 0.800 | 0.842 | 0.747 | 0.650 |
| all | 53 | 45 | 67 | 7 | 0.849 | 0.865 | 0.702 | 0.746 |

Per-detector precision (flagged items carrying that flag): auth 4/4, bag_remove 1/1, book_limits 2/2, cancel_flown 3/3, cancel_ineligible 4/4, confirm 22/29, insurance_not_offered 3/3, od_change 1/1, once 10/10, precond_reject 5/6
