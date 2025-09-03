import nltk
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import string

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

# Preprocessing function with lemmatization and stopword removal
def preprocess(text):
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))
    tokens = word_tokenize(text.lower())
    filtered = [
        lemmatizer.lemmatize(word)
        for word in tokens
        if word.isalnum() and word not in stop_words and word not in string.punctuation
    ]
    return ' '.join(filtered)

def getTopContributingTerms(query_vec, doc_vec, feature_names, top_n=5):
    """Get top terms that contribute most to the similarity score"""
    query_weights = query_vec.toarray()[0]
    doc_weights = doc_vec.toarray()[0]
    
    # Calculate contribution scores (element-wise multiplication)
    contributions = query_weights * doc_weights
    
    # Get top indices with positive contributions
    top_indices = np.argsort(contributions)[::-1]
    top_terms = []
    
    for idx in top_indices:
        if contributions[idx] > 0 and len(top_terms) < top_n:
            term = feature_names[idx]
            # Only include meaningful terms (not single characters, etc.)
            if len(term) > 2:
                top_terms.append((term, contributions[idx]))
        elif len(top_terms) >= top_n:
            break
    
    return top_terms

def recommendInternship(student, internships, top_n=5):
    # Remove duplicates based on company and title
    seen = set()
    unique_internships = []
    for intern in internships:
        key = (intern["company"], intern["title"])
        if key not in seen:
            seen.add(key)
            unique_internships.append(intern)
    internships = unique_internships
    
    if not internships:
        return []
    
    # Preprocess query from student's skills and interests
    query_raw = student["skills"] + " " + student["interests"]
    query = preprocess(query_raw)
    
    # Preprocess documents
    docs = []
    for intern in internships:
        doc_text = (
            intern["title"] + " " + 
            intern["description"] + " " + 
            intern["required_skills"] + " " +
            intern.get("preferred_skills", "") + " " +
            intern.get("responsibilities", "")
        )
        docs.append(preprocess(doc_text))
    
    if not query.strip():
        # Cold start: Recommend based on popularity, rating, and prestige
        scores = []
        for intern in internships:
            score = (intern["popularity"] / 100) * 0.4 + (intern["rating"] / 5) * 0.3 + (intern["company_prestige"] / 10) * 0.3
            scores.append((score, intern, "Recommended based on overall popularity and ratings (cold start)."))
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[:top_n]
    
    # Use sklearn TF-IDF for vectorization with better parameters
    vectorizer = TfidfVectorizer(
        max_features=5000,  # Limit vocabulary size
        min_df=2,           # Ignore terms that appear in only 1 document
        max_df=0.8,         # Ignore terms that appear in more than 80% of documents
        ngram_range=(1, 2)  # Include unigrams and bigrams
    )
    
    tfidf_matrix = vectorizer.fit_transform(docs + [query])
    query_vec = tfidf_matrix[-1]
    doc_vecs = tfidf_matrix[:-1]
    
    # Compute cosine similarities
    sims = cosine_similarity(query_vec, doc_vecs)[0]
    
    # Compute multi-factor scores
    max_stipend = max(intern["stipend"] for intern in internships)
    scores = []
    
    for i, intern in enumerate(internships):
        sim = sims[i]
        
        # Weighted score
        score = (
            sim * 0.4 +  # Similarity
            (intern["popularity"] / 100) * 0.2 +  # Popularity
            min(intern["stipend"] / max_stipend, 1) * 0.2 +  # Normalized stipend
            (intern["rating"] / 5) * 0.1 +  # Rating
            (intern["company_prestige"] / 10) * 0.1  # Prestige
        )
        
        # Enhanced explanation with top contributing terms
        feature_names = vectorizer.get_feature_names_out()
        top_terms = getTopContributingTerms(query_vec, doc_vecs[i], feature_names, top_n=5)

        if top_terms:
            term_list = [term for term, _ in top_terms]
            explanation = (
                f"Similarity score: {sim:.3f}\n"
                f"Top matched terms: {', '.join(term_list)}\n"
                f"Stipend: ${intern['stipend']} (normalized: {intern['stipend']/max_stipend:.2f})\n"
                f"Popularity: {intern['popularity']}/100\n"
                f"Rating: {intern['rating']}/5\n"
                f"Company Prestige: {intern['company_prestige']}/10"
            )
        else:
            explanation = (
                f"Similarity score: {sim:.3f}\n"
                f"No strong term matches found\n"
                f"Stipend: ${intern['stipend']} (normalized: {intern['stipend']/max_stipend:.2f})\n"
                f"Popularity: {intern['popularity']}/100\n"
                f"Rating: {intern['rating']}/5\n"
                f"Company Prestige: {intern['company_prestige']}/10"
            )
        
        scores.append((score, intern, explanation))
    
    # Sort by score and return top results
    scores.sort(key=lambda x: x[0], reverse=True)
    return scores[:top_n]


'''if __name__ == "__main__":
    # Sample student data
    student = {
        "skills": "Python machine learning deep learning neural networks TensorFlow PyTorch",
        "interests": "AI computer vision natural language processing"
    }
    
    # Sample internship data
    internships = [
        {
            "title": "Machine Learning Engineer Intern",
            "company": "TechCorp",
            "description": "Work on cutting-edge machine learning projects",
            "required_skills": "Python machine learning deep learning TensorFlow",
            "stipend": 5000,
            "popularity": 85,
            "rating": 4.7,
            "company_prestige": 9
        },
        {
            "title": "AI Research Intern",
            "company": "AI Labs",
            "description": "Research in neural networks and deep learning",
            "required_skills": "Python PyTorch neural networks computer vision",
            "stipend": 6000,
            "popularity": 90,
            "rating": 4.8,
            "company_prestige": 9
        }
    ]
    
    recommendations = recommend_internship(student, internships)
    
    for i, (score, intern, explanation) in enumerate(recommendations, 1):
        print(f"\nRecommendation #{i}: {intern['title']} at {intern['company']}")
        print(f"Overall Score: {score:.3f}")
        print(f"Explanation:\n{explanation}")
        print("-" * 50)'''