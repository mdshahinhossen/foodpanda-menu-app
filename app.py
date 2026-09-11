from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from bs4 import BeautifulSoup
from curl_cffi import requests

# API অ্যাপ তৈরি
app = FastAPI(title="Foodpanda Scraper API")

# ইনপুট ডাটার মডেল (API তে যে লিংক পাঠানো হবে)
class MenuRequest(BaseModel):
    url: str

# POST রিকোয়েস্টের জন্য এন্ডপয়েন্ট
@app.post("/api/extract_menu")
def extract_menu(request: MenuRequest):
    url = request.url
    
    try:
        # Cloudflare বাইপাস করে রিকোয়েস্ট পাঠানো
        response = requests.get(url, impersonate="chrome", timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # রেস্তোরাঁর বেসিক ডেটা বের করা
            restaurant_name = "Unknown"
            schema_tag = soup.find("script", {"data-testid": "restaurant-seo-schema"})
            
            if schema_tag:
                try:
                    data = json.loads(schema_tag.string)
                    restaurant_name = data.get('name', 'Unknown')
                except:
                    pass
            
            # মেনু আইটেমগুলোর পরিষ্কার নাম বের করা (আগের লজিক)
            available_items = []
            nodes = soup.find_all(attrs={"aria-label": True})
            for node in nodes:
                label = node.get("aria-label", "")
                if "Tk" in label and "Add to cart" in label:
                    item_name = label.split(",")[0].strip()
                    if item_name not in available_items:
                        available_items.append(item_name)
            
            # সাথে সাথে JSON ফরম্যাটে ডেটা রিটার্ন করা
            return {
                "success": True,
                "restaurant_name": restaurant_name,
                "total_items": len(available_items),
                "items": available_items
            }
        else:
            raise HTTPException(status_code=response.status_code, detail="Foodpanda blocked the request.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
