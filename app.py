import json
import time
from bs4 import BeautifulSoup
import requests as py_requests
from playwright.sync_api import sync_playwright

FOODPANDA_URL = "https://www.foodpanda.com.bd/restaurant/gqt8/hotel-raj-satkhira"
PHP_API_URL = "https://admin.wedeenpay.com/wedeen/partner/ai/foodpanda_sync_receiver.php"
SECRET_TOKEN = "WedeenPay_Secret_2026"

def auto_scrape_and_sync():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ফুডপান্ডা থেকে ডেটা সংগ্রহ শুরু (Playwright দিয়ে)...")
    
    try:
        # Playwright ব্রাউজার চালু করা
        with sync_playwright() as p:
            # headless=True মানে ব্রাউজারটি ব্যাকগ্রাউন্ডে চলবে। 
            # ডিবাগ করার সময় দেখতে চাইলে headless=False করে দিতে পারেন।
            browser = p.chromium.launch(headless=True)
            
            # আসল ইউজারের মতো প্রক্সি/হেডার সেট করা
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = context.new_page()
            
            print("ব্রাউজার ওপেন হয়েছে। পেজ লোড হচ্ছে, দয়া করে অপেক্ষা করুন...")
            
            # ফুডপান্ডার লিংকে যাওয়া এবং পেজের সব JavaScript রান হওয়া পর্যন্ত অপেক্ষা করা
            page.goto(FOODPANDA_URL, wait_until="networkidle", timeout=60000)
            
            # পেজের সম্পূর্ণ HTML সোর্স কোড নিয়ে নেওয়া
            html_content = page.content()
            browser.close()

            # --- HTML পার্সিং (আপনার আগের লজিক) ---
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # ১. রেস্টুরেন্টের নাম বের করা
            restaurant_name = "Restaurant"
            schema_tag = soup.find("script", {"data-testid": "restaurant-seo-schema"})

            if schema_tag:
                try:
                    data = json.loads(schema_tag.string)
                    restaurant_name = data.get('name', 'Restaurant')
                except:
                    pass
            
            # ২. মেনু আইটেমগুলোর পরিষ্কার নাম বের করা (Set ব্যবহার করে)
            available_items = set()
            nodes = soup.find_all(attrs={"aria-label": True})

            for node in nodes:
                label = node.get("aria-label", "")
                if "Tk" in label and "Add to cart" in label:
                    item_name = label.split(",")[0].strip()
                    available_items.add(item_name)
            
            if not available_items:
                print("❌ কোনো আইটেম পাওয়া যায়নি। আইপি ব্লক থাকতে পারে বা মেনু লোড হয়নি।")
                return

            print(f"'{restaurant_name}' এর {len(available_items)} টি আইটেম পাওয়া গেছে। সার্ভারে পাঠানো হচ্ছে...")
            
            # ৩. আপনার সার্ভারে ডেটা পাঠানো
            payload = {
                "secret_token": SECRET_TOKEN,
                "restaurant_name": restaurant_name,
                "available_items": json.dumps(list(available_items))
            }
            
            res = py_requests.post(
                PHP_API_URL,
                data=payload,
                timeout=30
            )
            
            if res.status_code == 200:
                print(f"✅ সার্ভার রেসপন্স: {res.text}")
            else:
                print(f"❌ সার্ভার এরর: {res.status_code}")
            
    except Exception as e:
        print(f"❌ ত্রুটি: {e}")

if __name__ == "__main__":
    auto_scrape_and_sync()
