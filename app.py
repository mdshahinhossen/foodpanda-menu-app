import json
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bs4 import BeautifulSoup
from curl_cffi import requests
from playwright.async_api import async_playwright


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("foodpanda-menu-app")

app = FastAPI(title="Foodpanda Menu Extractor")


class MenuRequest(BaseModel):
    url: str


# ---------------------------------------------------------
# HTML MENU EXTRACTION
# ---------------------------------------------------------

def extract_menu_from_html(html: str):
    soup = BeautifulSoup(html, "html.parser")

    restaurant_name = "Unknown"

    # Restaurant schema
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
                "Schema parsing failed: %s",
                e
            )

    items = []

    # -----------------------------------------------------
    # Method 1: aria-label
    # -----------------------------------------------------

    nodes = soup.find_all(
        attrs={"aria-label": True}
    )

    logger.info(
        "aria-label nodes found: %s",
        len(nodes)
    )

    for node in nodes:

        label = node.get(
            "aria-label",
            ""
        )

        label_lower = label.lower()

        if (
            "add to cart" in label_lower
            and "tk" in label_lower
        ):

            item_name = (
                label
                .split(",")[0]
                .strip()
            )

            if (
                item_name
                and item_name not in items
                and len(item_name) < 200
            ):
                items.append(item_name)

    # -----------------------------------------------------
    # Method 2: buttons
    # -----------------------------------------------------

    if not items:

        logger.info(
            "aria-label method found 0 items. "
            "Trying button fallback."
        )

        for button in soup.find_all("button"):

            text = button.get_text(
                " ",
                strip=True
            )

            if "Add to cart" in text:

                possible_name = (
                    text
                    .replace("Add to cart", "")
                    .strip()
                )

                if (
                    possible_name
                    and len(possible_name) < 200
                    and possible_name not in items
                ):
                    items.append(
                        possible_name
                    )

    # -----------------------------------------------------
    # Method 3: text fallback
    # -----------------------------------------------------

    if not items:

        logger.info(
            "Button method found 0 items. "
            "Trying text fallback."
        )

        for element in soup.find_all(
            ["div", "span"]
        ):

            text = element.get_text(
                " ",
                strip=True
            )

            if (
                "Add to cart" in text
                and len(text) > 10
            ):

                possible_name = (
                    text
                    .split("Add to cart")[0]
                    .strip()
                )

                if (
                    possible_name
                    and len(possible_name) < 200
                    and possible_name not in items
                ):
                    items.append(
                        possible_name
                    )

    return {
        "restaurant_name": restaurant_name,
        "total_items": len(items),
        "items": items
    }


# ---------------------------------------------------------
# PLAYWRIGHT
# ---------------------------------------------------------

async def extract_with_playwright(url: str):

    logger.info(
        "PLAYWRIGHT START | url=%s",
        url
    )

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        context = await browser.new_context(
            viewport={
                "width": 1366,
                "height": 768
            },
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 "
                "Safari/537.36"
            ),
            locale="bn-BD",
            timezone_id="Asia/Dhaka"
        )

        page = await context.new_page()

        try:

            await page.set_extra_http_headers({
                "Accept-Language":
                    "bn-BD,bn;q=0.9,en-US;q=0.8,en;q=0.7"
            })

            # Hide webdriver flag
            await page.add_init_script("""
                Object.defineProperty(
                    navigator,
                    'webdriver',
                    {
                        get: () => undefined
                    }
                );
            """)

            logger.info(
                "Opening Foodpanda page..."
            )

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
                "PLAYWRIGHT RESPONSE | status=%s | final_url=%s",
                status,
                page.url
            )

            # Give JavaScript time to load
            await page.wait_for_timeout(
                7000
            )

            # Scroll several times
            for _ in range(5):

                await page.evaluate("""
                    window.scrollBy(
                        0,
                        window.innerHeight
                    );
                """)

                await page.wait_for_timeout(
                    1500
                )

            html = await page.content()

            logger.info(
                "PLAYWRIGHT HTML LENGTH | %s",
                len(html)
            )

            # -------------------------------------------------
            # Check if Foodpanda blocked the browser
            # -------------------------------------------------

            lower_html = html.lower()

            blocked_words = [
                "access denied",
                "forbidden",
                "captcha",
                "verify you are human",
                "request blocked",
                "security check"
            ]

            blocked_word = None

            for word in blocked_words:

                if word in lower_html:
                    blocked_word = word
                    break

            if blocked_word:

                logger.warning(
                    "FOODPANDA BLOCK DETECTED | %s",
                    blocked_word
                )

                raise RuntimeError(
                    "Foodpanda blocked browser request"
                )

            # -------------------------------------------------
            # Extract
            # -------------------------------------------------

            result = extract_menu_from_html(
                html
            )

            logger.info(
                "PLAYWRIGHT RESULT | restaurant=%s | items=%s",
                result["restaurant_name"],
                result["total_items"]
            )

            return result

        finally:

            await browser.close()


# ---------------------------------------------------------
# CURL CFFI FALLBACK
# ---------------------------------------------------------

def extract_with_curl(url: str):

    logger.info(
        "CURL FALLBACK START | url=%s",
        url
    )

    response = requests.get(
        url,
        impersonate="chrome",
        timeout=30
    )

    response.encoding = "utf-8"

    logger.info(
        "CURL RESPONSE | status=%s | length=%s",
        response.status_code,
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


# ---------------------------------------------------------
# API
# ---------------------------------------------------------

@app.post("/api/extract_menu")
async def extract_menu(request: MenuRequest):

    url = request.url.strip()

    if not url:

        raise HTTPException(
            status_code=400,
            detail="URL is required."
        )

    if not url.startswith(
        "https://www.foodpanda.com.bd/"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Only Foodpanda Bangladesh URLs "
                "are supported."
            )
        )

    logger.info(
        "EXTRACTION REQUEST | url=%s",
        url
    )

    # -----------------------------------------------------
    # PLAYWRIGHT FIRST
    # -----------------------------------------------------

    try:

        result = await extract_with_playwright(
            url
        )

        if result["total_items"] > 0:

            logger.info(
                "SUCCESS USING PLAYWRIGHT | items=%s",
                result["total_items"]
            )

            return {
                "success": True,
                "method": "playwright",
                **result
            }

        logger.warning(
            "Playwright returned 0 items."
        )

    except Exception as e:

        logger.exception(
            "PLAYWRIGHT FAILED | type=%s | error=%s",
            type(e).__name__,
            e
        )

    # -----------------------------------------------------
    # CURL FALLBACK
    # -----------------------------------------------------

    try:

        result = extract_with_curl(
            url
        )

        logger.info(
            "CURL RESULT | restaurant=%s | items=%s",
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

    except requests.exceptions.Timeout:

        raise HTTPException(
            status_code=504,
            detail=(
                "Foodpanda request timed out."
            )
        )

    except requests.exceptions.RequestException as e:

        logger.exception(
            "CURL REQUEST ERROR"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                f"Foodpanda request failed: "
                f"{type(e).__name__}: {e}"
            )
        )

    except Exception as e:

        logger.exception(
            "EXTRACTION FAILED"
        )

        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {e}"
        )


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/")
def root():

    return {
        "status": "ok",
        "service": "foodpanda-menu-app",
        "playwright": True
    }