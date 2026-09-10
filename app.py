import streamlit as st
import requests
import json
from bs4 import BeautifulSoup

st.title("🍔 ফুডপান্ডা মেনু এক্সট্র্যাক্টর (Online)")
st.write("যেকোনো ফুডপান্ডা রেস্তোরাঁর লিংক নিচে দিন এবং এক ক্লিকেই মেনু ও দাম বের করে নিন!")

# ব্যবহারকারীর থেকে লিংক নেওয়ার ইনপুট বক্স
url = st.text_input("ফুডপান্ডা রেস্তোরাঁর লিংক দিন:", "https://www.foodpanda.com.bd/restaurant/gqt8/hotel-raj-satkhira")

if st.button("মেনু বের করুন"):
    if url:
        with st.spinner("সার্ভার থেকে ডেটা সংগ্রহ করা হচ্ছে, দয়া করে অপেক্ষা করুন..."):
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            try:
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    schema_tag = soup.find("script", {"data-testid": "restaurant-seo-schema"})
                    
                    output_text = "=== Restaurant Menu & Details ===\n\n"
                    
                    if schema_tag:
                        try:
                            data = json.loads(schema_tag.string)
                            output_text += f"Restaurant Name: {data.get('name')}\n"
                            output_text += f"Address: {data.get('address', {}).get('streetAddress')}\n"
                            output_text += f"Rating: {data.get('aggregateRating', {}).get('ratingValue')} / 5\n\n"
                        except:
                            pass
                    
                    output_text += soup.get_text(separator="\n", strip=True)
                    
                    st.success("সফলভাবে মেনু সংগ্রহ করা হয়েছে!")
                    
                    # স্ক্রিনে আউটপুট দেখানোর পাশাপাশি ডাউনলোড করার বাটন দেওয়া
                    st.download_button(
                        label="টেキスト ফাইল ডাউনলোড করুন",
                        data=output_text,
                        file_name="foodpanda_menu.txt",
                        mime="text/plain"
                    )
                    
                    # স্ক্রিনে কিছু অংশ প্রিভিউ দেখানো
                    st.text_area("মেনুর প্রিভিউ:", output_text[:2000], height=300)
                    
                else:
                    st.error(f"সংযুক্ত হতে সমস্যা হয়েছে। সার্ভার কোড: {response.status_code}")
            except Exception as e:
                st.error(f"একটি ত্রুটি ঘটেছে: {e}")
    else:
        st.warning("দয়া করে একটি সঠিক লিংক দিন।")