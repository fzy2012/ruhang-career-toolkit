# Ruhang Career Toolkit

[中文使用说明](README.zh.md) · [Skill entry point](SKILL.md) · [Attribution](NOTICE.md)

A local, conversational toolkit covering job discovery, JD analysis, resume preparation, interview preparation, offer comparison and salary negotiation. An application tracker connects drafts, confirmed submissions, immutable submitted materials and outcome reflection. Start by asking Codex to read `SKILL.md`. Keep the complete bundle together.

**Status: locally usable version, closed out on 2026-10-20.** Ready for personal use with Codex assistance and explicit user confirmation of key facts. This is not unattended automation or proof of real hiring outcomes. This version is authorized for synchronization to the GitHub project branch; no PR, website deployment or Release is included.

For a first real case, ask Codex to read `SKILL.md`, use `.career-data/personal/` as the data directory, exclude synthetic trial materials, and begin with your resume and one target JD. Reuse that same directory and application ID throughout the workflow. This instruction does not itself create an application or confirm a submission.

Personal data defaults to the Git-ignored `.career-data/` directory, or an external local directory chosen by the user. No automatic applications, Gmail, Notion, standalone website or publishing is included. Generated materials remain drafts until the user explicitly confirms an actual submission. Unknown facts remain unknown. Upstream examples are never candidate facts.

Python 3.10+ standard library commands (run from the project root):

```sh
python3 application-tracker-skill/scripts/tracker.py read
python3 application-tracker-skill/scripts/tracker.py report
python3 application-tracker-skill/scripts/tracker.py verify
python3 tools/migrate_legacy.py --dry-run
python3 tools/check_upstreams.py --verify-local
python3 tools/check_upstreams.py
python3 -m unittest discover -s tests -v
```

See [tracker instructions](application-tracker-skill/SKILL.md) for revision checks, idempotent writes, confirmation requirements, statuses and archival. Migration copies and verifies without deleting sources or replacing conflicting files. The 12 current resume templates and legacy Tech Compact remain available. Existing HTML/PDF outputs remain intact.

`upstreams.lock.json` pins Offer Toolkit at `f66c4b75dd68da409197ffc06c9807209037ce41` and ai-job-search v1.7.3 at `84808eebc13fa7b781b2ede034120c092776668d`, with original and installed checksums, selected files and adaptation scope. The read-only updater requires `gh`, reports additions/deletions/modifications/conflicts and never merges. Network errors are incomplete checks. Future updates require module-by-module adaptation and compatibility validation; automatic compatibility is not promised.

## Local acceptance results

As of 2026-10-20:

- 30 data/upgrade tests passed; 33 initial browser checks and follow-up checks exercised filtering, language switching, archived links, editing, Markdown download, PDF generation and clipboard fallback.
- An independent subagent completed six stages with a new synthetic Chinese product-manager profile, two fictional JDs and two fictional offers, executing 44 tracker CLI calls including reads and validation. The parent agent independently inspected files, hashes, links and browser behavior.
- Submitted snapshots stayed unchanged after editing the current resume. Interview preparation used the submitted version. Replayed requests returned the original record, stale revisions were rejected, and reapplication created a separate ID.
- Final trial state: two offers and one reapplication draft; historical funnel: two applications, one interview, two offers, zero acceptances. Missing interview history was not inferred, and negotiation drafts did not mark an offer accepted.
- Original checksums for 145 imported files and two legacy files were verified. Read-only upstream checking changed no source files. Acceptance data remains Git-ignored; source and archive checks passed before closeout.

Existing local artifacts (ignored by Git; absent from a fresh clone):

- [Initial acceptance](.career-data/acceptance/index.html) and [verification limits](.career-data/acceptance/verification.json): synthetic candidate, public JD sample, simulated outcomes.
- [Independent subagent trial](.career-data/subagent-flow-20261020/index.html), [walkthrough and findings](.career-data/subagent-flow-20261020/walkthrough.md), [CLI receipts](.career-data/subagent-flow-20261020/commands/execution-log.json), and [independent review](.career-data/subagent-flow-20261020/review/independent-check.json): fully synthetic candidate, jobs, offers and feedback; no public search.

Reuse flows from profile and jobs to JD analysis, targeted resume, confirmed-submission snapshots, interview preparation and feedback, offer comparison, then negotiation drafts and reflection. Final-inventory hashes describe final files; historical evidence comes from readbacks, snapshots and CLI receipts.

## Remaining operating limits

- Keep real data separate from examples and trials. Only explicit user reports justify application/outcome state changes.
- Offer state is not automatically bound to an existing terms file. The trial recorded one simulated offer before its terms file existed, then appended a source-completion note without rewriting history. Save complete terms and verify the application association before comparison or negotiation.
- Trial scoring and footer-generation mistakes were corrected, but no automatic gate guarantees every future report follows the rubric or states its sources accurately. Review facts, figures, scoring, sources and compensation terms before external use.
- Codex still orchestrates file reuse; the tracker does not generate or connect all six reports automatically. Browser edits do not update the structured profile, and tracker reports need regeneration after record changes.
- Other hosts' discovery/execution, real hiring outcomes, and all PDF readers/ATS systems remain unverified. Public discovery was limited to one employer board and two roles in the first run; restricted-access fallback was simulated. Future upstream releases still require manual adaptation and validation.

No global Skill installation is changed. Close out this local scope without further feature expansion; external submission, sending or publishing still requires authorization for that action.

Methods and templates: Dreameryanyan / yanliudesign, Offer Toolkit. Tracking workflow reference: Mads Lorentzen, ai-job-search. Both MIT license notices are retained; see [NOTICE.md](NOTICE.md).
