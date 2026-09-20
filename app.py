import json
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bs4 import BeautifulSoup
from curl_cffi import requests


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("foodpanda-menu-app")

app = FastAPI(title="Foodpanda Menu Extractor")


class MenuRequest(BaseModel):
    url: str


def extract_menu_from_html(html: str):
    soup = BeautifulSoup(html, "html.parser")

    restaurant_name = "Restaurant"

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
                    "Restaurant"
                )

        except Exception as e:
            logger.warning(
                "Schema parsing failed: %s",
                e
            )

    # Menu items
    available_items = []

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
        ).strip()

        label_lower = label.lower()

        if (
            "tk" in label_lower
            and "add to cart" in label_lower
        ):
            item_name = label.split(
                ",",
                1
            )[0].strip()

            if (
                item_name
                and item_name not in available_items
            ):
                available_items.append(
                    item_name
                )

    return {
        "restaurant_name": restaurant_name,
        "total_items": len(available_items),
        "items": available_items
    }


def fetch_foodpanda(url: str):

    logger.info(
        "FOODPANDA REQUEST | %s",
        url
    )

    response = requests.get(
        url,
        impersonate="chrome",
        timeout=30
    )

    response.encoding = "utf-8"

    logger.info(
        "FOODPANDA RESPONSE | status=%s | length=%s",
        response.status_code,
        len(response.text)
    )

    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail=(
                "Foodpanda returned HTTP "
                f"{response.status_code}"
            )
        )

    return extract_menu_from_html(
        response.text
    )


@app.get("/")
def root():

    return {
        "status": "ok",
        "service": "foodpanda-menu-app",
        "method": "curl_cffi"
    }


@app.post("/api/extract_menu")
def extract_menu(request: MenuRequest):

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
        "EXTRACTION REQUEST | %s",
        url
    )

    try:

        result = fetch_foodpanda(url)

        logger.info(
            "EXTRACTION SUCCESS | restaurant=%s | items=%s",
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
            detail="Foodpanda request timed out."
        )

    except requests.exceptions.RequestException as e:

        logger.exception(
            "Foodpanda request failed"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Foodpanda request failed: "
                f"{type(e).__name__}: {e}"
            )
        )

    except Exception as e:

        logger.exception(
            "EXTRACTION FAILED"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(e).__name__}: {e}"
            )
        )