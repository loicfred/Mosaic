"""End-to-end walkthrough of the live demo in a real browser (Playwright).

Prerequisites: API on :8000 and web app on :5173 (see README), freshly seeded demo
(`python scripts/seed_demo.py`). Then:

    pip install playwright && python -m playwright install chromium
    python tests/e2e/demo_flow.py [--base http://127.0.0.1:5173] [--shots out_dir]

Exits non-zero on the first failed step.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from pathlib import Path

from playwright.async_api import Page, async_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "data" / "demo" / "coastal_petty_cash_sep2026.csv"
PASSWORD = "Coastal-Demo-2026!"
GREETING = re.compile(r"^Good (morning|afternoon|evening), ")


async def login(page: Page, base: str, email: str) -> None:
    await page.goto(f"{base}/login")
    await page.get_by_label("Email").fill(email)
    await page.get_by_label("Password", exact=True).fill(PASSWORD)
    await page.get_by_role("button", name="Sign in").click()
    await expect(page.get_by_role("heading", name=GREETING)).to_be_visible(timeout=15_000)


async def step(name: str, coro, shots: Path | None, page: Page) -> None:
    print(f"- {name} ...", end=" ", flush=True)
    await coro
    if shots:
        await page.screenshot(path=str(shots / f"{name.replace(' ', '_')}.png"), full_page=True)
    print("ok")


async def run(base: str, shots: Path | None) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        await step("1 sign in as owner", login(page, base, "owner@coastal.demo"), shots, page)

        async def overview() -> None:
            await expect(page.get_by_text("Needs attention", exact=True)).to_be_visible()
            await expect(page.get_by_role("link", name="See what to do")).to_be_visible()
            await expect(page.get_by_text("Synthetic demo data")).to_be_visible()
            # The detailed forecast and the model's estimate live one click away.
            await page.get_by_role("link", name="View detailed forecast").click()
            await expect(page.get_by_text("30-day cash pressure")).to_be_visible(timeout=15_000)
            await expect(page.get_by_text("High risk")).to_be_visible()
        await step("2 overview shows position and prediction", overview(), shots, page)

        async def import_data() -> None:
            await page.goto(f"{base}/data-health")
            await page.get_by_role("tab", name="Import data").click()
            async with page.expect_file_chooser() as fc:
                await page.get_by_role("button", name="Choose CSV file").click()
            await (await fc.value).set_files(str(CSV))
            await expect(page.get_by_text("4 rows with errors (will be skipped)")).to_be_visible(timeout=20_000)
            commit = page.get_by_role("button", name="Commit 16 rows")
            await expect(commit).to_be_disabled()
            pending_dups = page.locator("li").filter(has=page.get_by_text("Possible duplicate")).filter(
                has=page.get_by_role("button", name="Approve"))
            while await pending_dups.count():
                btn = pending_dups.first.get_by_role("button", name="Approve")
                # The previous approval may still be saving; wait for the button before clicking.
                try:
                    await expect(btn).to_be_enabled(timeout=10_000)
                    await btn.click(timeout=5_000)
                except Exception:  # noqa: BLE001 - the row can be replaced while it re-renders
                    pass
                await page.wait_for_timeout(800)
            await expect(commit).to_be_enabled(timeout=10_000)
            await commit.click()
            await expect(page.get_by_text("16 rows added")).to_be_visible(timeout=30_000)
        await step("3 import messy CSV, approve duplicates, commit", import_data(), shots, page)

        async def act_on_opportunity() -> None:
            await page.goto(f"{base}/opportunities")
            card = page.locator("article", has=page.get_by_text("Customers paying", exact=False)).first
            await card.get_by_role("button", name="View evidence").click()
            dialog = page.get_by_role("dialog")
            await expect(dialog.get_by_text("Evidence - why this was flagged")).to_be_visible()
            await dialog.get_by_label("Note").fill("Call Coral Crest finance team on Monday")
            await dialog.get_by_role("button", name="Start action").click()
            await expect(dialog.get_by_text("Measuring - too early")).to_be_visible(timeout=15_000)
            await page.keyboard.press("Escape")
        await step("4 open evidence and start an action", act_on_opportunity(), shots, page)

        async def simulate() -> None:
            await page.goto(f"{base}/scenarios")
            await page.get_by_role("button", name="Combined plan").click()
            await expect(page.get_by_text("Supplier prices: -8%")).to_be_visible(timeout=10_000)
            await expect(page.get_by_text("SIMULATED", exact=False).first).to_be_visible()
        await step("5 simulate a combined plan", simulate(), shots, page)

        async def outcome() -> None:
            await page.goto(f"{base}/opportunities")
            await page.get_by_role("tab", name="Acting on").click()
            await expect(page.get_by_text("Outcome achieved").first).to_be_visible()
        await step("6 completed action shows measured outcome", outcome(), shots, page)

        async def security() -> None:
            await page.goto(f"{base}/security")
            await expect(page.get_by_text("Tenant isolation enforced in the database")).to_be_visible()
            await expect(page.get_by_text("data.import_committed").first).to_be_visible()
            await expect(page.get_by_text("opportunity.status_changed").first).to_be_visible()
        await step("7 security page and audit trail", security(), shots, page)

        async def insight() -> None:
            await page.goto(f"{base}/")
            await page.get_by_role("button", name="Ask Valora").click()
            panel = page.get_by_role("dialog", name="Valora Insight")
            await panel.get_by_role("button", name="How much cash do we have?").click()
            await expect(panel.get_by_text("Source:").first).to_be_visible(timeout=10_000)
            await expect(panel.get_by_text("Ledger, actual", exact=False).first).to_be_visible()
            await panel.get_by_label("Ask Valora about your business data").fill("Predict our revenue for next year")
            await panel.get_by_label("Ask Valora about your business data").press("Enter")
            await expect(panel.get_by_text("I don't have forecasting data for that in the current Valora dataset.")) \
                .to_be_visible(timeout=10_000)
            await page.keyboard.press("Escape")
        await step("8 Valora Insight answers from data and refuses a forecast", insight(), shots, page)

        viewer = await (await browser.new_context()).new_page()
        async def viewer_checks() -> None:
            await login(viewer, base, "viewer@coastal.demo")
            await viewer.goto(f"{base}/data-health")
            await expect(viewer.get_by_text("Needs an owner or accountant").first).to_be_visible()
        await step("9 viewer is read-only", viewer_checks(), None, viewer)

        other = await (await browser.new_context()).new_page()
        async def other_tenant() -> None:
            await login(other, base, "owner@tamarind.demo")
            await expect(other.get_by_text("Tamarind Cafe").first).to_be_visible()
            await other.goto(f"{base}/transactions?counterparty=Coral%20Crest%20Hotels%20Ltd")
            await expect(other.get_by_text("No transactions match these filters")).to_be_visible()
        await step("10 another tenant sees none of Coastal's data", other_tenant(), None, other)

        fresh = await (await browser.new_context()).new_page()
        async def register() -> None:
            await fresh.goto(f"{base}/register")
            await fresh.get_by_label("Full name").fill("E2E Owner")
            await fresh.get_by_label("Work email").fill(f"e2e-{int(time.time())}@example.com")
            await fresh.get_by_label("Password", exact=True).fill("Harbour-Lights-2026")
            await fresh.get_by_label("Business name").fill("E2E Test Kitchen")
            await fresh.get_by_label("Sector").fill("Food & beverage")
            await fresh.get_by_label("Opening cash (MUR)").fill("85000")
            await fresh.get_by_label("Balance date").fill("2026-01-01")
            await fresh.get_by_role("button", name="Create account").click()
            await expect(fresh.get_by_role("heading", name=GREETING)).to_be_visible(timeout=15_000)
            await expect(fresh.get_by_text("Import your transactions")).to_be_visible()
            await expect(fresh.get_by_text("Synthetic demo data")).to_have_count(0)
        await step("11 register a new, empty business", register(), None, fresh)

        await browser.close()
        if errors:
            raise SystemExit(f"page errors: {errors}")
        print("Demo flow passed.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5173")
    ap.add_argument("--shots", type=Path)
    a = ap.parse_args()
    if a.shots:
        a.shots.mkdir(parents=True, exist_ok=True)
    try:
        asyncio.run(run(a.base, a.shots))
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
