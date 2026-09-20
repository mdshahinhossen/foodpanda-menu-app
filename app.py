import asyncio
import json
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bs4 import BeautifulSoup
from curl_cffi import requests
from playwright.async_api import async_playwright


# =========================================================
# Logging
# =========================================================

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("foodpanda-menu-app")


# =========================================================
# FastAPI
# =========================================================

app = FastAPI(title="Foodpanda Scraper API")


# =========================================================
# Request Model
# =========================================================

class MenuRequest(BaseModel):
    url: str


# =========================================================
# Helpers
# =========================================================

def extract_menu_from_html(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # -----------------------------------------------------
    # Restaurant name
    # -----------------------------------------------------

    restaurant_name = "Unknown"

    schema_tag = soup.find(
        "script",
        {"data-testid": "restaurant-seo-schema"}
    )

    if schema_tag:
        try:
            schema_text = (
                schema_tag.string
                or schema_tag.get_text()
            )

            data = json.loads(schema_text)

            if isinstance(data, dict):
                restaurant_name = data.get(
                    "name",
                    "Unknown"
                )

        except Exception as e:
            logger.warning(
                "Restaurant schema parsing failed: %s",
                e
            )

    # -----------------------------------------------------
    # Menu items
    # -----------------------------------------------------

    available_items = []

    nodes = soup.find_all(
        attrs={
            "aria-label": True
        }
    )

    logger.info(
        "Found aria-label nodes | count=%s",
        len(nodes)
    )

    for node in nodes:

        label = node.get(
            "aria-label",
            ""
        )

        if (
            "Tk" in label
            and "Add to cart" in label
        ):

            item_name = (
                label
                .split(",")[0]
                .strip()
            )

            if (
                item_name
                and item_name not in available_items
            ):
                available_items.append(
                    item_name
                )

    # -----------------------------------------------------
    # Additional fallback:
    # Look for buttons containing Add to cart
    # -----------------------------------------------------

    if not available_items:

        logger.info(
            "aria-label extraction returned 0 items. "
            "Trying button/text fallback."
        )

        for element in soup.find_all(
            ["button", "div", "span"]
        ):

            text = element.get_text(
                " ",
                strip=True
            )

            if (
                "Add to cart" in text
                and len(text) > 10
            ):

                parts = text.split(
                    "Add to cart"
                )

                if parts:

                    possible_name = (
                        parts[0]
                        .strip()
                    )

                    if (
                        possible_name
                        and len(possible_name) < 200
                        and possible_name
                        not in available_items
                    ):
                        available_items.append(
                            possible_name
                        )

    return {
        "restaurant_name": restaurant_name,
        "total_items": len(available_items),
        "items": available_items
    }


# =========================================================
# Playwright Browser Extraction
# =========================================================

async def extract_with_playwright(url: str):

    logger.info(
        "Playwright extraction started | url=%s",
        url
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = await browser.new_context(
            viewport={
                "width": 1366,
                "height": 768
            },
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            },
            locale="bn-BD",
            timezone_id="Asia/Dhaka"
        )

        page = await context.new_page()

        try:

            # -------------------------------------------------
            # Extra browser headers
            # -------------------------------------------------

            await page.set_extra_http_headers({
                "Accept-Language": "bn-BD,bn;q=0.9,en-US;q=0.8,en;q=0.7"
            })

            # -------------------------------------------------
            # Hide obvious automation property
            # -------------------------------------------------

            await page.add_init_script("""
                Object.defineProperty(
                    navigator,
                    'webdriver',
                    {
                        get: () => undefined
                    }
                );
            """)

            # -------------------------------------------------
            # Open Foodpanda
            # -------------------------------------------------

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            status = (
                response.status
                if response
                else None
            )

            logger.info(
                "Playwright page response | status=%s | url=%s",
                status,
                page.url
            )

            # -------------------------------------------------
            # Wait for dynamic content
            # -------------------------------------------------

            await page.wait_for_timeout(
                5000
            )

            # -------------------------------------------------
            # Small scroll
            # -------------------------------------------------

            await page.evaluate("""
                window.scrollTo(
                    0,
                    document.body.scrollHeight
                );
            """)

            await page.wait_for_timeout(
                3000
            )

            # -------------------------------------------------
            # Get rendered HTML
            # -------------------------------------------------

            html = await page.content()

            logger.info(
                "Playwright rendered HTML | length=%s",
                len(html)
            )

            # -------------------------------------------------
            # Detect obvious block page
            # -------------------------------------------------

            lower_html = html.lower()

            blocked_words = [
                "access denied",
                "forbidden",
                "captcha",
                "verify you are human",
                "request blocked"
            ]

            blocked = any(
                word in lower_html
                for word in blocked_words
            )

            if blocked:

                logger.warning(
                    "Playwright appears to be blocked by Foodpanda"
                )

                raise RuntimeError(
                    "Foodpanda browser request appears blocked"
                )

            result = extract_menu_from_html(
                html
            )

            logger.info(
                "Playwright extraction result | "
                "restaurant=%s | items=%s",
                result["restaurant_name"],
                result["total_items"]
            )

            return result

        finally:

            await browser.close()


# =========================================================
# curl_cffi Fallback
# =========================================================

def extract_with_curl(url: str):

    logger.info(
        "curl_cffi fallback started | url=%s",
        url
    )

    response = requests.get(
        url,
        impersonate="chrome",
        timeout=30
    )

    response.encoding = "utf-8"

    logger.info(
        "curl_cffi response | status=%s | final_url=%s | content_length=%s",
        response.status_code,
        response.url,
        len(response.text)
    )

    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail=(
                f"Foodpanda returned HTTP "
                f"{response.status_code}"
            )
        )

    return extract_menu_from_html(
        response.text
    )


# =========================================================
# Main API
# =========================================================

@app.post("/api/extract_menu")
async def extract_menu(request: MenuRequest):

    url = request.url.strip()

    if not url:
        raise HTTPException(
            status_code=400,
            detail="URL is required."
        )

    logger.info(
        "extract_menu started | url=%s",
        url
    )

    # =====================================================
    # Method 1: Playwright
    # =====================================================

    try:

        result = await extract_with_playwright(
            url
        )

        # -------------------------------------------------
        # If browser successfully extracted items
        # -------------------------------------------------

        if result["total_items"] > 0:

            logger.info(
                "SUCCESS via Playwright | "
                "restaurant=%s | items=%s",
                result["restaurant_name"],
                result["total_items"]
            )

            return {
                "success": True,
                "method": "playwright",
                **result
            }

        logger.warning(
            "Playwright returned 0 menu items. "
            "Trying curl_cffi fallback."
        )

    except Exception as e:

        logger.exception(
            "Playwright extraction failed | "
            "type=%s | error=%s",
            type(e).__name__,
            e
        )


    # =====================================================
    # Method 2: curl_cffi fallback
    # =====================================================

    try:

        result = extract_with_curl(
            url
        )

        logger.info(
            "SUCCESS via curl_cffi | "
            "restaurant=%s | items=%s",
            result["restaurant_name"],
            result["total_items"]
        )

        return {
            "success": True,
            "method": "curl_cffi",
            **result
        }

    except HTTPException:

        raise

    except requests.exceptions.Timeout as e:

        logger.exception(
            "Foodpanda request TIMEOUT | url=%s",
            url
        )

        raise HTTPException(
            status_code=504,
            detail=(
                "Foodpanda request timed out "
                "after 30 seconds."
            )
        ) from e

    except requests.exceptions.RequestException as e:

        logger.exception(
            "Foodpanda request ERROR | "
            "type=%s | url=%s",
            type(e).__name__,
            url
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Foodpanda request failed: "
                f"{type(e).__name__}: {e}"
            )
        ) from e

    except Exception as e:

        logger.exception(
            "UNEXPECTED extract_menu ERROR | "
            "type=%s | url=%s",
            type(e).__name__,
            url
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(e).__name__}: {e}"
            )
        ) from e


# =========================================================
# Health Check
# =========================================================

@app.get("/")
def root():

    return {
        "status": "ok",
        "service": "foodpanda-menu-app"
    }