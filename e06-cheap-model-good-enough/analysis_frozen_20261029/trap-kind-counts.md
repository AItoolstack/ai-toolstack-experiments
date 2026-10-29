# E06 all: kind and trap counts, 29 October 2026

Cells show correct calls / observed calls, followed by distinct items. Repeats are correlated.

## Difficulty

| Group | oss-20b | luna | oss-120b | sol | glm-flash | glm-flash-t0 |
| --- | --- | --- | --- | --- | --- | --- |
| clear | 102/102 (34 items) | 99/102 (34 items) | 102/102 (34 items) | 34/34 (34 items) | 101/102 (34 items) | 34/34 (34 items) |
| contested | 15/24 (8 items) | 23/24 (8 items) | 19/24 (8 items) | 7/8 (8 items) | 19/24 (8 items) | 7/8 (8 items) |
| hard | 161/180 (60 items) | 172/180 (60 items) | 167/180 (60 items) | 58/60 (60 items) | 159/180 (60 items) | 54/60 (60 items) |

## Named traps

| Group | oss-20b | luna | oss-120b | sol | glm-flash | glm-flash-t0 |
| --- | --- | --- | --- | --- | --- | --- |
| amount_due_differs | 14/15 (5 items) | 15/15 (5 items) | 12/15 (5 items) | 5/5 (5 items) | 15/15 (5 items) | 5/5 (5 items) |
| computed_due_date | 20/21 (7 items) | 21/21 (7 items) | 18/21 (7 items) | 7/7 (7 items) | 17/21 (7 items) | 6/7 (7 items) |
| credit_note | 12/12 (4 items) | 12/12 (4 items) | 12/12 (4 items) | 4/4 (4 items) | 12/12 (4 items) | 4/4 (4 items) |
| date_format | 20/21 (7 items) | 20/21 (7 items) | 21/21 (7 items) | 6/7 (7 items) | 14/21 (7 items) | 5/7 (7 items) |
| decoy_reference | 15/15 (5 items) | 15/15 (5 items) | 15/15 (5 items) | 5/5 (5 items) | 15/15 (5 items) | 5/5 (5 items) |
| default_attendee | 7/12 (4 items) | 12/12 (4 items) | 10/12 (4 items) | 4/4 (4 items) | 11/12 (4 items) | 4/4 (4 items) |
| derived_base | 17/18 (6 items) | 18/18 (6 items) | 18/18 (6 items) | 6/6 (6 items) | 17/18 (6 items) | 5/6 (6 items) |
| distractor_numbers | 12/12 (4 items) | 12/12 (4 items) | 12/12 (4 items) | 4/4 (4 items) | 12/12 (4 items) | 4/4 (4 items) |
| enum_mapping | 9/9 (3 items) | 9/9 (3 items) | 6/9 (3 items) | 3/3 (3 items) | 9/9 (3 items) | 3/3 (3 items) |
| exception_tier | 9/9 (3 items) | 9/9 (3 items) | 8/9 (3 items) | 3/3 (3 items) | 9/9 (3 items) | 3/3 (3 items) |
| exclusion | 9/9 (3 items) | 9/9 (3 items) | 9/9 (3 items) | 3/3 (3 items) | 9/9 (3 items) | 3/3 (3 items) |
| first_step_only | 5/9 (3 items) | 9/9 (3 items) | 9/9 (3 items) | 3/3 (3 items) | 9/9 (3 items) | 3/3 (3 items) |
| foreign_language | 15/15 (5 items) | 15/15 (5 items) | 15/15 (5 items) | 5/5 (5 items) | 15/15 (5 items) | 5/5 (5 items) |
| format_conversion | 9/9 (3 items) | 9/9 (3 items) | 9/9 (3 items) | 3/3 (3 items) | 9/9 (3 items) | 3/3 (3 items) |
| missing_argument | 9/12 (4 items) | 10/12 (4 items) | 9/12 (4 items) | 3/4 (4 items) | 9/12 (4 items) | 3/4 (4 items) |
| missing_field | 17/18 (6 items) | 17/18 (6 items) | 18/18 (6 items) | 4/6 (6 items) | 12/18 (6 items) | 4/6 (6 items) |
| number_format | 18/18 (6 items) | 18/18 (6 items) | 18/18 (6 items) | 6/6 (6 items) | 18/18 (6 items) | 6/6 (6 items) |
| ocr_noise | 12/12 (4 items) | 12/12 (4 items) | 12/12 (4 items) | 4/4 (4 items) | 12/12 (4 items) | 4/4 (4 items) |
| order_of_operations | 7/9 (3 items) | 9/9 (3 items) | 9/9 (3 items) | 3/3 (3 items) | 6/9 (3 items) | 2/3 (3 items) |
| party_confusion | 12/12 (4 items) | 12/12 (4 items) | 12/12 (4 items) | 4/4 (4 items) | 12/12 (4 items) | 4/4 (4 items) |
| policy_override | 8/12 (4 items) | 7/12 (4 items) | 9/12 (4 items) | 4/4 (4 items) | 9/12 (4 items) | 3/4 (4 items) |
| relative_date | 7/18 (6 items) | 16/18 (6 items) | 10/18 (6 items) | 5/6 (6 items) | 15/18 (6 items) | 5/6 (6 items) |
| rounding | 10/12 (4 items) | 12/12 (4 items) | 12/12 (4 items) | 4/4 (4 items) | 8/12 (4 items) | 2/4 (4 items) |
| similar_tools | 9/9 (3 items) | 9/9 (3 items) | 9/9 (3 items) | 3/3 (3 items) | 9/9 (3 items) | 3/3 (3 items) |
| threshold_minimum | 5/9 (3 items) | 8/9 (3 items) | 9/9 (3 items) | 3/3 (3 items) | 5/9 (3 items) | 3/3 (3 items) |
