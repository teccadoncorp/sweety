# Campaign Brief

Use this when a campaign is in `draft` or has no brief yet, or when the board needs a strategy to approve.

## What to produce

1. Checkout the relevant task (or create one if you are the CMO and none exists).
2. Write a campaign brief covering:
   - Audience and job-to-be-done
   - Positioning / one-line promise
   - Channel mix (email, social, search, partners) with why
   - Narrative arc for the first two weeks
   - Success metrics the analyst can measure
3. Save it with `post_artifact` using `kind` = `campaign-brief`.
4. Create delegated tasks for `copywriter`, `social`, `seo`, and `analyst` with clear outcomes.
5. Call `request_approval` with `kind` = `campaign_strategy`, `subject_type` = `campaign`, and the campaign id.

Do not pretend the work is published. You are writing the plan the board will approve.
