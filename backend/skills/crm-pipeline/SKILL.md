# CRM Pipeline

Score leads, log touches, and move deals with CRM tools.

## How to work
1. Read `crm_board` and `crm_overdue` before recommending work.
2. Search with `crm_search`. Upsert contacts, accounts, and deals.
3. Score leads with `crm_score_contact`. Log every touch with `crm_log_activity`.
4. Move deals through signal → qualify → propose → commit → won/lost.
5. Post a markdown artifact the board can approve.
6. Request approval before anything live (publish, spend, outreach).

## Output
- Title the artifact clearly
- Include owners, timing, and next action
- Stay in brand voice
