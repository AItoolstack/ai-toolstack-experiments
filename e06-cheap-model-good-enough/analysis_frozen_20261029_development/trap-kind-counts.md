# E06 development: kind and trap counts, 29 October 2026

Cells show correct calls / observed calls, followed by distinct items. Repeats are correlated.

## Difficulty

| Group | oss-20b | luna | oss-120b | sol | glm-flash | glm-flash-t0 |
| --- | --- | --- | --- | --- | --- | --- |
| clear | 9/9 (3 items) | 9/9 (3 items) | 9/9 (3 items) | 3/3 (3 items) | 9/9 (3 items) | 3/3 (3 items) |
| contested | 3/6 (2 items) | 5/6 (2 items) | 5/6 (2 items) | 1/2 (2 items) | 3/6 (2 items) | 1/2 (2 items) |
| hard | 43/48 (16 items) | 45/48 (16 items) | 41/48 (16 items) | 16/16 (16 items) | 44/48 (16 items) | 15/16 (16 items) |

## Named traps

| Group | oss-20b | luna | oss-120b | sol | glm-flash | glm-flash-t0 |
| --- | --- | --- | --- | --- | --- | --- |
| amount_due_differs | 5/6 (2 items) | 6/6 (2 items) | 3/6 (2 items) | 2/2 (2 items) | 6/6 (2 items) | 2/2 (2 items) |
| computed_due_date | 8/9 (3 items) | 9/9 (3 items) | 6/9 (3 items) | 3/3 (3 items) | 9/9 (3 items) | 3/3 (3 items) |
| credit_note | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| date_format | 8/9 (3 items) | 8/9 (3 items) | 9/9 (3 items) | 2/3 (3 items) | 6/9 (3 items) | 2/3 (3 items) |
| decoy_reference | 6/6 (2 items) | 6/6 (2 items) | 6/6 (2 items) | 2/2 (2 items) | 6/6 (2 items) | 2/2 (2 items) |
| default_attendee | 1/3 (1 items) | 3/3 (1 items) | 2/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| derived_base | 5/6 (2 items) | 6/6 (2 items) | 6/6 (2 items) | 2/2 (2 items) | 6/6 (2 items) | 2/2 (2 items) |
| distractor_numbers | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| enum_mapping | 3/3 (1 items) | 3/3 (1 items) | 0/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| exception_tier | 3/3 (1 items) | 3/3 (1 items) | 2/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| exclusion | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| first_step_only | 0/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| foreign_language | 6/6 (2 items) | 6/6 (2 items) | 6/6 (2 items) | 2/2 (2 items) | 6/6 (2 items) | 2/2 (2 items) |
| format_conversion | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| missing_argument | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| missing_field | 2/3 (1 items) | 2/3 (1 items) | 3/3 (1 items) | 0/1 (1 items) | 0/3 (1 items) | 0/1 (1 items) |
| number_format | 6/6 (2 items) | 6/6 (2 items) | 6/6 (2 items) | 2/2 (2 items) | 6/6 (2 items) | 2/2 (2 items) |
| ocr_noise | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| order_of_operations | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| party_confusion | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| policy_override | 3/3 (1 items) | 0/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 0/3 (1 items) | 0/1 (1 items) |
| relative_date | 1/3 (1 items) | 3/3 (1 items) | 2/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| rounding | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 3/3 (1 items) | 1/1 (1 items) |
| threshold_minimum | 3/3 (1 items) | 3/3 (1 items) | 3/3 (1 items) | 1/1 (1 items) | 2/3 (1 items) | 1/1 (1 items) |
