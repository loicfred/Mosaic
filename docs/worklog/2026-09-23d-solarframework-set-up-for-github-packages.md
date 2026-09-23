# 2026-09-23d — SolarFramework set up for GitHub Packages

Author: Claude

## Why

The website builds on SolarFramework, which each teammate had to install locally from a checkout. Maven Central
was ruled out: SolarFramework's licence is proprietary and anything on Central is public and permanent. GitHub
Packages lets Maven download it like any dependency. The package takes the repository's visibility, and
`SolarFlare-mu/SolarFramework` is public, so the package is public too; readers still need a token.

The first deploy failed with `422 Unprocessable Entity`: GitHub Packages rejects capital letters in an
artifactId, and every SolarFramework module but `core` had them. No package existed under the org or the user,
so it was not a name clash. The artifactIds were renamed to kebab case.

## What changed

- SolarFramework root `pom.xml`: `<distributionManagement>` pointing at
  `https://maven.pkg.github.com/solarflare-mu/solarframework`, server id `github`.
- Every artifactId under `org.solarframework.mu` is kebab case: parent `solar-framework`, `database-impl`,
  `ai-api`, `web-utils`, `python-runner` and so on. Folder names are unchanged. Renamed in 48 POMs: SolarFramework
  (30), SolarERP (13), MauDonate, Inazuma Competitive, InazumaElevenLibraries, and here `Java/OpportunityApp` and
  `Java/OpportunityImpl`. Only an artifactId with the `org.solarframework.mu` groupId beside it was touched.
  `AuthenticationImpl`, `AuthenticationAPI`, `StaffAuthenticationAPI` and `CustomerAuthenticationAPI` stay as they
  are: they are managed in SolarFramework's root POM but are not its modules.
- `Java/OpportunityApp/pom.xml`: the GitHub Packages repository under `<repositories>`.
- `Java/setup-github-packages.ps1`: a teammate's whole setup in one command. It opens the token page, takes the
  pasted token, checks it can download `solar-framework-1.0.pom`, saves `GITHUB_ACTOR`/`GITHUB_TOKEN` and adds the
  `github` server to `~/.m2/settings.xml`. Tested on scratch settings files (none, with and without `<servers>`,
  namespaced, run twice), and Maven parses the result; the token checks were run with this machine's token.
- `~/.m2/settings.xml` (this machine): a `github` server reading `GITHUB_ACTOR` and `GITHUB_TOKEN` from the
  environment; both are set as user environment variables.
- Docs: `Java/OpportunityApp/README.md` (token setup, local install kept as the alternative), SolarFramework
  `README.md` (install section and module list with the new names), SolarFramework `CLAUDE.md` (Publishing
  section and the kebab-case rule), `docs/requirements.md` (deploy, commits and token rotation as open items).

## Verification

- `help:evaluate` shows the root deploy URL.
- SolarFramework `.\mvnw.cmd -o clean install -DskipTests`: all 30 modules build and install under the new names.
  Tests were skipped; only POMs changed.
- Offline `compile -DskipTests` against the installed artifacts passes in `Java/OpportunityImpl`,
  `Java/OpportunityApp`, MauDonate, Inazuma Competitive, InazumaElevenLibraries and SolarERP. SolarERP first failed
  on missing versions: its modules find their parent through `<relativePath/>`, so Maven read the stale root POM in
  the local repository; `-N install` of SolarERP's root POM fixed it. No tests were run in the consumers.
- The deploy after the rename got past the `422` and failed with `401 Unauthorized`, from a terminal opened
  before the token variables were set. Run again from a fresh terminal, it published: the GitHub API lists the
  `org.solarframework.mu.*` packages on `SolarFramework`, and `solar-framework-1.0.pom` downloads with the token.
- IntelliJ then reported the same `401` resolving the parent: it was started before `setx`, so it has no token.
  A full restart of IntelliJ is the fix; not yet confirmed.
