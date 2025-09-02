import os
import time
import yaml
from typing import List
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Page, Locator

from app.get_dashboard_data import get_dashboard_ids

# -------- Selectors (tolerant defaults) --------
# Container for each viz tile
CHART_SELECTORS = [
    '[data-test-viz="chart-container"]',      # common data-test on viz container
    '[data-test="chart-container"]',          # alt
    '[data-test="slice-container"]',          # older/alt
]
# Things that indicate "still loading"
LOADING_HINTS = [
    '[role="progressbar"]',
    '.ant-skeleton',                          # antd skeleton loader
    '.loading', '.is-loading',                # generic loading classes
    '[data-test="loading"]',
    'svg[aria-label="loading"]',
]
# Things that indicate an error
ERROR_HINTS_TEXT = ["error", "failed", "timeout", "traceback"]
ERROR_HINTS_SELECTORS = [
    '[data-test="alert"]',
    '.ant-alert-error',
    '.chart-overlay > .error',
    '[data-test="chart-error"]',
]
# Per-chart refresh affordances (try in order)
CHART_REFRESH_SELECTORS = [
    '[aria-label="Refresh chart"]',                     # explicit refresh btn
    '[data-test="refresh-chart-button"]',               # data-test
    '[data-test="refresh-chart-menu-item"]',            # menu item
    'button:has-text("Refresh chart")',
    'button:has-text("Refresh")',                       # fallback within tile
]

def parse_ids(ids_env: str) -> List[str]:
    raw = [x.strip() for x in ids_env.replace(";", ",").split(",") if x.strip()]
    seen, out = set(), []
    for x in raw:
        if x not in seen:
            out.append(x); seen.add(x)
    return out

def build_dashboard_url(config: dict, dash_id: str) -> str:
    base = f"{config['url']}{config['dashboard_base_path']}/{dash_id}/"
    extra_qs = config.get("dashboard_querystring", "standalone=1")
    return base + ("?" + extra_qs if extra_qs else "")

def login_if_needed(config: dict, page: Page):
    page.goto(f"{config['url']}/", wait_until="domcontentloaded", timeout=config['page_timeout_ms'])
    if "login" in page.url and config['user'] and config['password']:
        page.fill('input[name="username"]', config['user'])
        page.fill('input[name="password"]', config['password'])
        # Try clicking the sign in button if present, but don't block if not
        try:
            page.click('input[type="submit"][value="Sign In"], button:has-text("Sign in"), button:has-text("Sign In")', timeout=2000)
        except PWTimeout:
            pass
        except Exception:
            pass
        page.wait_for_url(f"{config['url']}/superset/welcome/", timeout=10000)

def ensure_context(config: dict, pw):
    browser = pw.chromium.launch(headless=config["headless"])
    context = browser.new_context(
        storage_state=config.get("storage_state_path", "superset_storage.json") if os.path.exists(config.get("storage_state_path", "superset_storage.json")) else None
    )
    page = context.new_page()
    page.set_default_timeout(config['page_timeout_ms'])
    page.goto(f"{config['url']}/", wait_until="domcontentloaded")
    if "login" in page.url:
        login_if_needed(config, page)
        context.storage_state(path=config.get("storage_state_path", "superset_storage.json"))
    return browser, context, page

def chart_has_loading(page: Page, tile: Locator) -> bool:
    # If any loading hint exists inside the tile, mark as loading
    for hint in LOADING_HINTS:
        if tile.locator(hint).count():
            return True
    # Also detect common "Loading..." text
    try:
        text = tile.inner_text(timeout=500).lower()
        if "loading" in text and "no data" not in text:
            return True
    except Exception:
        pass
    return False

def chart_has_error(page: Page, tile: Locator) -> bool:
    for sel in ERROR_HINTS_SELECTORS:
        if tile.locator(sel).count():
            return True
    try:
        text = (tile.inner_text(timeout=500) or "").lower()
        if any(k in text for k in ERROR_HINTS_TEXT):
            return True
    except Exception:
        pass
    return False

def chart_is_ready(page: Page, tile: Locator) -> bool:
    if chart_has_loading(page, tile):
        return False
    if chart_has_error(page, tile):
        return False
    # Also require the visualization SVG/canvas/table to be present
    viz_ready = tile.locator("svg, canvas, table, [data-test='deckgl-container']").count() > 0
    return viz_ready

def refresh_chart_tile(tile: Locator) -> bool:
    """
    Try to refresh an individual chart tile by clicking a refresh control within the tile.
    Returns True if a click was performed.
    """
    tile.hover()
    for sel in CHART_REFRESH_SELECTORS:
        btn = tile.locator(sel)
        if btn.count():
            try:
                btn.first.click()
                return True
            except Exception:
                continue
    # Sometimes refresh is inside a "more" menu in the tile
    more_btn = tile.locator('[aria-label="More options"], [data-test="chart-controls"] button')
    if more_btn.count():
        try:
            more_btn.first.click()
            # try again to find a refresh entry in the opened menu
            for sel in CHART_REFRESH_SELECTORS:
                menu_item = tile.page.locator(sel)
                if menu_item.count():
                    menu_item.first.click()
                    return True
        except Exception:
            pass
    return False

def wait_for_tile_to_settle(tile: Locator, timeout_ms: int) -> bool:
    """
    Wait until the tile is not loading and not erroring, within timeout_ms.
    """
    deadline = time.time() + (timeout_ms / 1000.0)
    last_state = ""
    while time.time() < deadline:
        ready = chart_is_ready(tile.page, tile)
        state = "ready" if ready else ("error" if chart_has_error(tile.page, tile) else ("loading" if chart_has_loading(tile.page, tile) else "unknown"))
        if state != last_state:
            # print state transitions if you want verbosity
            last_state = state
        if ready:
            return True
        time.sleep(0.5)
    return chart_is_ready(tile.page, tile)

def refresh_dashboard(page: Page):
    # First, click the "more" button to reveal dashboard actions
    more_btn = page.locator('button[aria-label="Menu actions trigger"].ant-dropdown-trigger, button:has(.anticon[aria-label="more-horiz"])')
    if more_btn.count():
        try:
            more_btn.first.click()
            time.sleep(0.5)  # Give time for menu to open
            # After dropdown appears, click "Refresh dashboard" menu item
            refresh_item = page.locator('li.ant-dropdown-menu-item:has-text("Refresh dashboard")')
            if refresh_item.count():
                refresh_item.first.click()
                return
        except Exception:
            pass
    # Fallback: try direct refresh button
    btn = page.locator(
        '[aria-label="Refresh dashboard"], [data-test="refresh-dashboard-button"], button:has-text("Refresh")'
    )
    if btn.count():
        btn.first.click()
    else:
        page.keyboard.press("r")
    if btn.count():
        btn.first.click()
    else:
        page.keyboard.press("r")

def warm_dashboard(config: dict, page: Page, dash_id: str):
    url = build_dashboard_url(config, dash_id)
    print(f"→ warming dashboard {dash_id} @ {url}")
    page.goto(url, wait_until="domcontentloaded")

    # Initial dashboard refresh to pull latest
    refresh_dashboard(page)
    try:
        page.wait_for_load_state("networkidle", timeout=config["page_timeout_ms"])
    except PWTimeout:
        print("ERROR: Chart timeout")
        pass

    # Verify every chart tile; refresh tiles that fail
    # ensure_all_charts_loaded(page)
    print(f"✓ dashboard {dash_id} warm complete")


def get_config():
    with open("config/secrets.yaml") as f:
        cfg = yaml.safe_load(f)["superset"]
    return cfg

def main():
    config = get_config()
    ids = get_dashboard_ids(config)
    # ids = ["77", "88"]
    if not ids:
        raise SystemExit("No dashboard IDs configured.")
    dashboard_delay_sec = int(config["total_allocated_running_sec"])/len(ids)
    with sync_playwright() as pw:
        browser, context, page = ensure_context(config, pw)
        for i, dash_id in enumerate(ids, 1):
            attempts = 0
            while True:
                try:
                    print("starting the warming the dashboards")
                    warm_dashboard(config, page, dash_id)
                    break
                except Exception as e:
                    attempts += 1
                    if attempts > config["retry_on_fail"]:
                        print(f"✗ failed {dash_id} after {attempts} attempt(s): {e}")
                        break
                    print(f"… retrying {dash_id} due to: {e}")
                    time.sleep(2)
            if i < len(ids):
                print(f"Sleeping for {dashboard_delay_sec} seconds")
                time.sleep(dashboard_delay_sec)
        context.close()
        browser.close()
