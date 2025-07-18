
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

FAQ_START_PATH = "https://www.kotaksecurities.com/support"

def get_category_links():
    resp = requests.get(FAQ_START_PATH)
    soup = BeautifulSoup(resp.text, 'html.parser')
    return [a['href'] for a in soup.select('a[href*="/support/"]')]

def scrape_faqs():
    faqs = []
    for link in set(get_category_links()):
        url = link if link.startswith("http") else "https://www.kotaksecurities.com" + link
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            for q in soup.select('h2, h3'):
                text = q.get_text(strip=True)
                if text.endswith('?'):
                    nxt = q.find_next_sibling()
                    a = nxt.get_text(strip=True) if nxt else ""
                    faqs.append({"question": text, "answer": a, "url": url})
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
    return pd.DataFrame(faqs)

@st.cache(allow_output_mutation=True)
def load_data():
    df = scrape_faqs()
    df.columns = df.columns.str.strip().str.lower()  # Clean column names
    if 'question' not in df or df.empty:
        st.error("FAQ data could not be loaded. Please check the source.")
        st.stop()

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(df['question'].tolist())
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))
    return df, model, index

st.title("📘 Kotak Securities Universal FAQ Search")
st.write("Ask questions like 'How to apply for IPO' or 'How to place a bracket order'.")

df, model, index = load_data()
st.write("Scraped FAQ count:", len(df))  # Helpful for debugging
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
