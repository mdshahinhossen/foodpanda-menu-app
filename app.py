import json
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
import requests as py_requests
import time

FOODPANDA_URL = "https://www.foodpanda.com.bd/restaurant/gqt8/hotel-raj-satkhira"
PHP_API_URL = "https://admin.wedeenpay.com/wedeen/partner/ai/foodpanda_sync_receiver.php"
SECRET_TOKEN = "WedeenPay_Secret_2026"

def auto_scrape_and_sync():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ফুডপান্ডা থেকে ডেটা সংগ্রহ শুরু...")
    
    try:
        response = curl_requests.get(FOODPANDA_URL, impersonate="chrome", timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # ১. রেস্টুরেন্টের নাম বের করা
            restaurant_name = "Restaurant"
            schema_tag = soup.find("script", {"data-testid": "restaurant-seo-schema"})
            if schema_tag:
                try:
                    data = json.loads(schema_tag.string)
                    restaurant_name = data.get('name', 'Restaurant')
                except:
                    pass
            
            # ২. মেনু আইটেমগুলোর পরিষ্কার নাম বের করা (aria-label থেকে)
            available_items = []
            nodes = soup.find_all(attrs={"aria-label": True})
            for node in nodes:
                label = node.get("aria-label", "")
                if "Tk" in label and "Add to cart" in label:
                    item_name = label.split(",")[0].strip() # "Butter Naan, Tk 30" থেকে "Butter Naan" আলাদা করা
                    if item_name not in available_items:
                        available_items.append(item_name)
            
            print(f"'{restaurant_name}' এর {len(available_items)} টি আইটেম পাওয়া গেছে। সার্ভারে পাঠানো হচ্ছে...")
            
            # ৩. আপনার সার্ভারে ডেটা পাঠানো
            payload = {
                "secret_token": SECRET_TOKEN,
                "restaurant_name": restaurant_name,
                "available_items": json.dumps(available_items) # Array টিকে JSON বানিয়ে পাঠানো
            }
            
            res = py_requests.post(PHP_API_URL, data=payload, timeout=30)
            
            if res.status_code == 200:
                print(f"✅ সার্ভার রেসপন্স: {res.text}")
            else:
                print(f"❌ সার্ভার এরর: {res.status_code}")
                
        else:
            print(f"❌ ফুডপান্ডা ব্লক করেছে। সার্ভার কোড: {response.status_code}")
            
    except Exception as e:
        print(f"❌ ত্রুটি: {e}")

if __name__ == "__main__":
    auto_scrape_and_sync()
