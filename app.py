import logging
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bs4 import BeautifulSoup
from curl_cffi import requests


# =========================================================
# Logging
# =========================================================

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("foodpanda-menu-app")


# =========================================================
# FastAPI App
# =========================================================

app = FastAPI(title="Foodpanda Scraper API")


# =========================================================
# Request Model
# =========================================================

class MenuRequest(BaseModel):
    url: str


# =========================================================
# Extract Menu
# =========================================================

@app.post("/api/extract_menu")
def extract_menu(request: MenuRequest):

    url = request.url

    try:

        logger.info(
            "extract_menu started | url=%s",
            url
        )

        # -------------------------------------------------
        # Request Foodpanda
        # -------------------------------------------------

        response = requests.get(
            url,
            impersonate="chrome",
            timeout=30
        )

        response.encoding = "utf-8"

        logger.info(
            "Foodpanda response | status=%s | final_url=%s | content_length=%s",
            response.status_code,
            response.url,
            len(response.text)
        )

        # -------------------------------------------------
        # Non-200 Response
        # -------------------------------------------------

        if response.status_code != 200:

            logger.warning(
                "Foodpanda returned non-200 | status=%s | url=%s",
                response.status_code,
                url
            )

            raise HTTPException(
                status_code=response.status_code,
                detail=f"Foodpanda returned HTTP {response.status_code}"
            )

        # -------------------------------------------------
        # Parse HTML
        # -------------------------------------------------

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # -------------------------------------------------
        # Restaurant Name
        # -------------------------------------------------

        restaurant_name = "Unknown"

        schema_tag = soup.find(
            "script",
            {
                "data-testid": "restaurant-seo-schema"
            }
        )

        if schema_tag:

            try:

                schema_text = (
                    schema_tag.string
                    or schema_tag.get_text()
                )

                data = json.loads(schema_text)

                restaurant_name = data.get(
                    "name",
                    "Unknown"
                )

            except (
                json.JSONDecodeError,
                TypeError,
                AttributeError
            ) as e:

                logger.warning(
                    "Restaurant schema parsing failed | error=%s",
                    e
                )

        # -------------------------------------------------
        # Extract Menu Items
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Success Log
        # -------------------------------------------------

        logger.info(
            "extract_menu success | restaurant=%s | items=%s | url=%s",
            restaurant_name,
            len(available_items),
            url
        )

        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return {
            "success": True,
            "restaurant_name": restaurant_name,
            "total_items": len(available_items),
            "items": available_items
        }

    # =====================================================
    # HTTPException
    # =====================================================

    except HTTPException:

        # Already handled intentionally.
        raise

    # =====================================================
    # Timeout
    # =====================================================

    except requests.exceptions.Timeout as e:

        logger.exception(
            "Foodpanda request TIMEOUT | url=%s",
            url
        )

        raise HTTPException(
            status_code=504,
            detail="Foodpanda request timed out after 30 seconds."
        ) from e

    # =====================================================
    # Request Error
    # =====================================================

    except requests.exceptions.RequestException as e:

        logger.exception(
            "Foodpanda request ERROR | type=%s | url=%s",
            type(e).__name__,
            url
        )

        raise HTTPException(
            status_code=502,
            detail=(
                f"Foodpanda request failed: "
                f"{type(e).__name__}: {e}"
            )
        ) from e

    # =====================================================
    # Unknown / Unexpected Error
    # =====================================================

    except Exception as e:

        # IMPORTANT:
        # logger.exception() automatically prints
        # the full Python traceback in Render logs.

        logger.exception(
            "UNEXPECTED extract_menu ERROR | type=%s | url=%s",
            type(e).__name__,
            url
        )

        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {e}"
        ) from e