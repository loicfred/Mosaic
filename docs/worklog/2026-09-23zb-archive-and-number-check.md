# 2026-09-23 — Archive rebuild and small financial claims

Author: Codex

- Updated `Java/OpportunityImpl/pom.xml` so Maven removes `mosaic-python.zip` before rebuilding it during `generate-resources`. This prevents deleted `AI/app/**/*.py` files from lingering in the packaged archive. Ran `generate-resources` twice and compared Python paths: 70 source paths, 70 archive paths, zero stale paths; the second run rebuilt the archive even without a source change.
- Updated `Java/OpportunityImpl/src/main/java/mu/mosaic/opportunity/service/ai/NumberCheck.java` so small explicit money and percentage claims need evidence, including units before or after the number. Ordinary small counts in prose remain allowed. Added regression cases in `Java/OpportunityImpl/src/test/java/mu/mosaic/opportunity/service/ai/NumberCheckTest.java`; confirmed the new case failed before the implementation and passed afterward.
- Verified `Java/OpportunityImpl` with `mvnw.cmd -q test`, then installed the module with `mvnw.cmd -q -DskipTests install`; verified `Java/OpportunityApp` with `mvnw.cmd -q test`. All commands exited successfully.
- Verified `AI` with `python -m pytest tests -q --tb=short --basetemp=.codex-test-tmp -p no:cacheprovider`: 170 passed, with two dependency deprecation warnings. Removed the temporary test directory afterward.
- Updated `docs/requirements.md` to remove the stale archive-deletion and small-number tasks. The desktop browser check recorded in `docs/worklog/2026-09-23za-browser-test-and-fixes.md` rendered overview suggestion and caveat charts; the remaining chart check is at phone width after the latest fixes.

The packaged JAR still needs an autostart smoke run with its own Python process and configured interpreter. The prior standalone run used `autostart=false` because an existing API occupies port 8000. Live Google sign-in, reset email, Groq/LM Studio tool calls, and phone-width browser checks remain open in `docs/requirements.md`.