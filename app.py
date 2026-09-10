import json
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
import requests as py_requests
import time

# ================= কনফিগারেশন =================
# ফুডপান্ডার লিঙ্ক
FOODPANDA_URL = "https://www.foodpanda.com.bd/restaurant/gqt8/hotel-raj-satkhira"

# আপনার আপডেট করা অরিজিনাল API লিঙ্ক
PHP_API_URL = "https://admin.wedeenpay.com/wedeen/partner/ai/foodpanda_sync_receiver.php"

# সিকিউরিটি টোকেন (পিএইচপি ফাইলের পাসওয়ার্ডের সাথে হুবহু মিল থাকতে হবে)
SECRET_TOKEN = "WedeenPay_Secret_2026"
# ==============================================

def auto_scrape_and_sync():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ফুডপান্ডা থেকে ডেটা সংগ্রহ শুরু হচ্ছে...")
    
    try:
        # ক্লাউডফ্লেয়ার বাইপাস করে ডেটা আনা
        response = curl_requests.get(FOODPANDA_URL, impersonate="chrome", timeout=30)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            schema_tag = soup.find("script", {"data-testid": "restaurant-seo-schema"})
            
            restaurant_name = "Restaurant"
            output_text = "=== Foodpanda Menu ===\n\n"
            
            if schema_tag:
                try:
                    data = json.loads(schema_tag.string)
                    restaurant_name = data.get('name', 'Restaurant')
                except:
                    pass
            
            output_text += soup.get_text(separator="\n", strip=True)
            
            # সার্ভারে ডেটা পাঠানো
            print(f"'{restaurant_name}' এর ডেটা সার্ভারে পাঠানো হচ্ছে...")
            payload = {
                "secret_token": SECRET_TOKEN,
                "restaurant_name": restaurant_name,
                "menu_data": output_text
            }
            
            res = py_requests.post(PHP_API_URL, data=payload, timeout=30)
            
            if res.status_code == 200:
                print(f"✅ সফলভাবে সিংক হয়েছে! সার্ভার রেসপন্স: {res.text}")
            else:
                print(f"❌ সার্ভার এরর: {res.status_code}")
                
        else:
            print(f"❌ ফুডপান্ডা ব্লক করেছে। সার্ভার কোড: {response.status_code}")
            
    except Exception as e:
        print(f"❌ একটি ত্রুটি ঘটেছে: {e}")

if __name__ == "__main__":
    auto_scrape_and_sync()
