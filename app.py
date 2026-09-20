from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from bs4 import BeautifulSoup
from curl_cffi import requests

app = FastAPI(title="Foodpanda Scraper API")

class MenuRequest(BaseModel):
    url: str

@app.post("/api/extract_menu")
def extract_menu(request: MenuRequest):
    url = request.url
    
    try:
        # ক্লাউডফ্লেয়ার বাইপাস করার জন্য রিকোয়েস্ট পাঠানো
        response = requests.get(url, impersonate="chrome", timeout=35)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return {
                "success": False,
                "restaurant_name": "Unknown",
                "total_items": 0,
                "items": [],
                "error": f"Foodpanda returned status code {response.status_code}"
            }
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # রেস্তোরাঁর নাম বের করা
        restaurant_name = "Unknown"
        schema_tag = soup.find("script", {"data-testid": "restaurant-seo-schema"})
        if schema_tag and schema_tag.string:
            try:
                data = json.loads(schema_tag.string)
                restaurant_name = data.get('name', 'Unknown')
            except:
                pass
        
        # মেনু আইটেম বের করার লজিক
        available_items = []
        nodes = soup.find_all(attrs={"aria-label": True})
        for node in nodes:
            label = node.get("aria-label", "")
            if "Tk" in label and "Add to cart" in label:
                item_name = label.split(",")[0].strip()
                if item_name and item_name not in available_items:
                    available_items.append(item_name)
        
        return {
            "success": True,
            "restaurant_name": restaurant_name,
            "total_items": len(available_items),
            "items": available_items
        }
            
    except Exception as e:
        # কোনো কারণে কোড ফেল করলে ক্র্যাশ না করে এরর মেসেজ রিটার্ন করবে
        return {
            "success": False,
            "restaurant_name": "Error",
            "total_items": 0,
            "items": [],
            "error": str(e)
        }