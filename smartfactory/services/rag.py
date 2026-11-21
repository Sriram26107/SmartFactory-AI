from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def search_documents(question,folder='knowledge',top_k=3):
    """Local retrieval: returns excerpts and filenames, no generated or invented answers."""
    paths=sorted(Path(folder).glob('*.txt'))
    chunks=[]
    for p in paths:
        content=p.read_text(encoding='utf-8')
        for i in range(0,len(content),900):
            text=content[i:i+1100].strip()
            if text:chunks.append((p.name,text))
    if not chunks:return []
    corpus=[x[1] for x in chunks]
    try:
        tfidf=TfidfVectorizer(stop_words='english').fit_transform(corpus+[question])
    except ValueError:return []
    scores=cosine_similarity(tfidf[-1],tfidf[:-1]).ravel()
    return [{'source':chunks[i][0],'excerpt':chunks[i][1],'score':round(float(scores[i]),3)} for i in scores.argsort()[::-1][:top_k] if scores[i]>0]
