import streamlit as st
import requests
import json
from bs4 import BeautifulSoup

st.set_page_config(page_title="Foodpanda Menu Extractor", page_icon="🍔")

st.title("🍔 ফুডপান্ডা মেনু এক্সট্র্যাক্টর (Cloud Ready)")
st.write("ফুডপান্ডার ক্লাউডফ্লেয়ার বাইপাস করার জন্য আপডেট করা সংস্করণ।")

url = st.text_input("ফুডপান্ডা রেস্তোরাঁর লিংক দিন:", "https://www.foodpanda.com.bd/restaurant/gqt8/hotel-raj-satkhira")

if st.button("মেনু বের করুন"):
    if url:
        with st.spinner("সুরক্ষিত সার্ভার থেকে ডেটা সংগ্রহ করা হচ্ছে, দয়া করে অপেক্ষা করুন..."):
            
            # নিখুঁত ব্রাউজার হেডার্স যা ক্লাউডফ্লেয়ারকে বোকা বানাতে সাহায্য করবে
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.google.com/",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            try:
                # সাধারণ requests এর বদলে Session ব্যবহার করা যাতে কুকি হ্যান্ডেল করতে পারে
                session = requests.Session()
                response = session.get(url, headers=headers, timeout=30)
                
                # বাংলা ফন্ট বা এনকোডিং ঠিক করার লাইন
                response.encoding = 'utf-8'
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    schema_tag = soup.find("script", {"data-testid": "restaurant-seo-schema"})
                    
                    output_text = "=== Restaurant Menu & Details ===\n\n"
                    file_name = "foodpanda_menu.txt"
                    
                    if schema_tag:
                        try:
                            data = json.loads(schema_tag.string)
                            safe_name = str(data.get('name', 'restaurant')).replace(" ", "_").replace("-", "")
                            file_name = f"{safe_name}_menu.txt"
                            
                            output_text += f"Restaurant Name: {data.get('name')}\n"
                            output_text += f"Address: {data.get('address', {}).get('streetAddress')}\n"
                            output_text += f"Rating: {data.get('aggregateRating', {}).get('ratingValue')} / 5\n\n"
                        except:
                            pass
                    
                    output_text += soup.get_text(separator="\n", strip=True)
                    
                    st.success("✅ সফলভাবে মেনু সংগ্রহ করা হয়েছে!")
                    
                    st.download_button(
                        label="📥 মেনু ফাইলটি ডাউনলোড করুন",
                        data=output_text,
                        file_name=file_name,
                        mime="text/plain"
                    )
                    
                    st.text_area("মেনুর প্রিভিউ:", output_text[:1500] + "\n\n...(বাকি অংশ ফাইলে আছে)", height=300)
                    
                else:
                    st.error(f"❌ সার্ভার থেকে ব্লক করা হয়েছে। কোড: {response.status_code}. ক্লাউড সার্ভারের আইপি ফুডপান্ডা ট্র্যাক করেছে।")
            except Exception as e:
                st.error(f"একটি ত্রুটি ঘটেছে: {e}")
    else:
        st.warning("দয়া করে একটি সঠিক লিংক দিন।")
