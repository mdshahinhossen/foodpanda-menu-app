import streamlit as st
import json
from bs4 import BeautifulSoup
from curl_cffi import requests  # ব্রাউজারের মতো ফিঙ্গারপ্রিন্ট ব্যবহারের জন্য

st.set_page_config(page_title="Foodpanda Menu Extractor", page_icon="🍔")

st.title("🍔 ফুডপান্ডা মেনু এক্সট্র্যাক্টর (Cloud Bypass)")
st.write("ক্লাউডফ্লেয়ার বাইপাস করার জন্য ব্রাউজার ফিঙ্গারপ্রিন্ট মোডে চলছে।")

url = st.text_input("ফুডপান্ডা রেস্তোরাঁর লিংক দিন:", "https://www.foodpanda.com.bd/restaurant/gqt8/hotel-raj-satkhira")

if st.button("মেনু বের করুন"):
    if url:
        with st.spinner("ব্রাউজার ছদ্মবেশে ডেটা সংগ্রহ করা হচ্ছে, দয়া করে অপেক্ষা করুন..."):
            try:
                # curl_cffi ব্যবহার করে রিকোয়েস্ট পাঠানো (impersonate='chrome' দিলে ক্লাউডফ্লেয়ার বোকা বনে যায়)
                response = requests.get(url, impersonate="chrome", timeout=30)
                
                # বাংলা ফন্ট বা এনকোডিং ঠিক রাখা
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
                    st.error(f"❌ সার্ভার কোড রিটার্ন করেছে: {response.status_code}")
            except Exception as e:
                st.error(f"একটি ত্রুটি ঘটেছে: {e}")
    else:
        st.warning("দয়া করে একটি সঠিক লিংক দিন।")
