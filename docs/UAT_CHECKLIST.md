# User Acceptance Testing (UAT) Checklist

This is a stand-in for the Phase 6 task "Test with actual NGO staff;
simplify confusing screens." That testing needs real NGO staff using the
real deployed app and hasn't happened yet — this checklist is what to
run with them when it does. Until it's completed, don't mark that Phase
6 item done in [`ROADMAP.md`](ROADMAP.md)/[`TASKS.md`](TASKS.md).

**How to use this:** sit with one or two non-technical NGO staff (ideally
someone who does outreach day-to-day, not someone technical) at the
*deployed* app (not local dev), hand them each task below one at a time
with no extra hints, and write down: did they complete it, how long did
it take, where did they hesitate or click the wrong thing, what did they
say out loud. Confusion is the finding — the point isn't whether they
eventually succeed, it's whether the screen made them stop and think.

## Setup

- [ ] Real NGO Profile filled in via the NGO Profile screen (not the
      env-var defaults).
- [ ] A handful (5-10) of real or realistic companies already loaded,
      so the dashboard/list isn't empty on first look.

## Tasks to hand a staff member, one at a time

1. [ ] "Find companies in [a specific city] that focus on [a specific
       CSR area]." — tests company search/filters.
2. [ ] "Open one of those companies and tell me if it looks like a good
       lead." — tests the company detail page and the lead score badge
       (do they notice it? do they understand what it means without
       being told?).
3. [ ] "Find someone at this company we could contact." — tests the
       "Scan website" / discovery panel discoverability and the
       add-contact flow.
4. [ ] "Write a first-outreach email to that contact." — tests the AI
       email generator (Generate → edit → Copy). Ask afterward: did they
       understand this is a draft, not something the app sends for
       them?
5. [ ] "Mark this company as Contacted and set a follow-up for next
       week." — tests the status panel and follow-up date field.
6. [ ] "Add a note about a call you just had." — tests notes.
7. [ ] "Upload this proposal document to the company." — tests document
       upload.
8. [ ] "Add a tag to this company." — tests tags, including whether
       they understand tags are freeform/reusable.
9. [ ] Without prompting which screen: "Show me how many companies
       you've contacted this month and what's overdue for follow-up." —
       tests dashboard discoverability, not just correctness.
10. [ ] "Export your company list to a spreadsheet." — tests CSV
        export.
11. [ ] Give them an existing NGO spreadsheet (a real one, if
        available) and ask them to bring it into the app. — tests CSV
        import end-to-end, including whether the column-name
        requirement is a real friction point for non-technical staff.

## After each session, record

- [ ] Which tasks needed a hint or got stuck — those screens are
      candidates for "simplify" work per the Phase 6 goal.
- [ ] Any vocabulary staff didn't recognize ("lead score," "proposal
      stage," "CSR focus," etc.) — the app should use the NGO's own
      language where it doesn't match.
- [ ] Anything they tried to do that the app doesn't support at all —
      candidate for `ROADMAP.md`, not a bug.
- [ ] Whether they ever seemed unsure if an email had actually been
      *sent* vs. just drafted — this is a correctness-of-understanding
      issue given the app's "never auto-send" rule, and worth taking
      seriously if it comes up.

## Exit criteria

Only mark the Phase 6 "test with actual NGO staff" task done once this
has been run with real staff (not the developer) against the deployed
app, and any high-friction findings from it have either been fixed or
explicitly deferred with a reason in `ROADMAP.md`.
