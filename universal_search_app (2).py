
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

FAQ_START_PATH = "https://www.kotaksecurities.com/support"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_category_links():
    try:
        resp = requests.get(FAQ_START_PATH, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        return [a['href'] for a in soup.select('a[href*="/support/"]')]
    except Exception as e:
        print("Failed to fetch category links:", e)
        return []

def scrape_faqs():
    faqs = []
    links = set(get_category_links())
    for link in links:
        url = link if link.startswith("http") else "https://www.kotaksecurities.com" + link
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            found = False
            for q in soup.select('h2, h3'):
                text = q.get_text(strip=True)
                if text.endswith('?'):
                    nxt = q.find_next_sibling()
                    a = nxt.get_text(strip=True) if nxt else ""
                    faqs.append({"question": text, "answer": a, "url": url})
                    found = True
            print(f"✅ Scraped {len(faqs)} FAQs from: {url}" if found else f"⚠️ No FAQs found at: {url}")
        except Exception as e:
            print(f"❌ Failed to scrape {url}: {e}")
    return pd.DataFrame(faqs)

@st.cache(allow_output_mutation=True)
def load_data():
    df = scrape_faqs()
    df.columns = df.columns.str.strip().str.lower()

    if df.empty or 'question' not in df:
        st.warning("No FAQs found from the live site. Loading fallback demo data.")
        df = pd.DataFrame([
            {"question": "How to apply for an IPO?", "answer": "You can apply via the IPO section in your Kotak Securities app or website.", "url": FAQ_START_PATH},
            {"question": "How to place a bracket order?", "answer": "Go to the order placement screen, select 'Bracket Order' and define your target and stoploss.", "url": FAQ_START_PATH},
            {"question": "What are the brokerage charges?", "answer": "They depend on the plan you're subscribed to. Check Charges section for details.", "url": FAQ_START_PATH},
            {"question": "How to reset my password?", "answer": "Use the 'Forgot Password' option on the login screen to reset.", "url": FAQ_START_PATH}
        ])

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(df['question'].tolist())
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))
    return df, model, index

st.title("📘 Kotak Securities Universal FAQ Search")
st.write("Ask questions like 'How to apply for IPO' or 'How to place a bracket order'.")

df, model, index = load_data()
st.write("Scraped FAQ count:", len(df))  # For debugging

query = st.text_input("Your question:")

if query:
    emb = model.encode([query])
    D, I = index.search(np.array(emb), k=5)
    st.subheader("Top results:")
    for idx in I[0]:
        row = df.iloc[idx]
        st.markdown(f"**Q: {row.question}**")
        st.write(row.answer)
        st.markdown(f"[Read more]({row.url})")
        st.markdown("---")
