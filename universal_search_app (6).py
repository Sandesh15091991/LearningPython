from pathlib import Path
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from sentence_transformers import SentenceTransformer, util
import numpy as np
import os
import json

@st.cache_resource
def load_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_data
def scrape_faqs():
    base_url = "https://www.kotaksecurities.com/support/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(base_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Get all links that look like FAQ category pages
        links = soup.select('a[href*="/support/"]')
        faq_urls = list(set([
            "https://www.kotaksecurities.com" + link['href']
            for link in links
            if "/support/" in link['href'] and "kotaksecurities.com" not in link['href']
        ]))

        faq_data = []
        for url in faq_urls:
            try:
                r = requests.get(url, headers=headers, timeout=10)
                page = BeautifulSoup(r.text, 'html.parser')
                # Look for <h2> or <h3> tags that contain questions
                for tag in page.find_all(['h2', 'h3']):
                    question = tag.get_text(strip=True)
                    if question.endswith('?') and len(question.split()) > 2:
                        faq_data.append({'question': question, 'source': url})
            except Exception as inner_e:
                print(f"Error scraping {url}: {inner_e}")

        df = pd.DataFrame(faq_data)
        if not df.empty:
            df.to_csv("cached_faqs.csv", index=False)
        return df

    except Exception as e:
        print("Scraping failed:", e)
        return pd.DataFrame()  # fallback to local or demo

@st.cache_data
def load_data():
    if Path("cached_faqs.csv").exists():
        df = pd.read_csv("cached_faqs.csv")
        st.info("Loaded cached FAQ data from previous scrape.")
    else:
        df = scrape_faqs()
        if df.empty:
            st.warning("No FAQs found from the live site. Loading fallback demo data.")
            df = pd.DataFrame([
                {"question": "How to apply for an IPO?", "source": "https://www.kotaksecurities.com/support/ipo/"},
                {"question": "How to place a bracket order?", "source": "https://www.kotaksecurities.com/support/orders/"},
                {"question": "How to reset my trading password?", "source": "https://www.kotaksecurities.com/support/account/"},
            ])

    df.columns = [str(col).strip().lower() for col in df.columns]
    model = load_model()
    embeddings = model.encode(df['question'].astype(str).tolist(), convert_to_tensor=True)
    return df, model, embeddings

st.title("🔍 Universal Search – Kotak FAQs")
st.markdown("Search for frequently asked questions like **How to apply for IPO**, **bracket order**, etc.")

df, model, index = load_data()

query = st.text_input("Enter your query:", placeholder="e.g. How to apply for IPO")

if query:
    query_embedding = model.encode(query, convert_to_tensor=True)
    scores = util.cos_sim(query_embedding, index)[0].cpu().numpy()
    top_idx = np.argsort(scores)[::-1][:5]

    st.subheader("Top Matches")
    for i in top_idx:
        st.markdown(f"**Q:** {df.iloc[i]['question']}")
        st.markdown(f"[🔗 View Answer]({df.iloc[i]['source']})")
        st.markdown("---")
