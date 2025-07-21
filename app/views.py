import os
from django.shortcuts import render
import pickle
import pandas as pd
from pathlib import Path
import requests
from functools import lru_cache
from dotenv import load_dotenv
import os
# ==== CONSTANTS ====
load_dotenv()  # Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
MOVIES_PATH = os.path.join(BASE_DIR, 'app/movies.pkl')
SIMILARITY_PATH = os.path.join(BASE_DIR, 'app/similarity.pkl')
TMDB_API_TOKEN = f"Bearer {os.getenv("API_Key")}"  # truncated for safety

# ==== CACHE PICKLE FILES ====
@lru_cache(maxsize=1)
def load_movies():
    with open(MOVIES_PATH, 'rb') as f:
        return pd.DataFrame(pickle.load(f))

@lru_cache(maxsize=1)
def load_similarity():
    with open(SIMILARITY_PATH, 'rb') as f:
        return pickle.load(f)

# ==== EXTERNAL API CALL ====
def get_movie_poster(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?language=en-US"
    headers = {
        "accept": "application/json",
        "Authorization": TMDB_API_TOKEN
    }

    try:
        response = requests.get(url, headers=headers, timeout=3)
        if response.ok:
            data = response.json()
            poster_path = data.get('poster_path')
            if poster_path:
                return {
                    "title": data.get('title'),
                    "path": f"https://image.tmdb.org/t/p/w500/{poster_path}"
                }
    except requests.RequestException:
        pass
    return {"title": "Not Found", "path": ""}

# ==== CORE LOGIC ====
def recommend(title):
    cosine_sim = load_similarity()
    movies = load_movies()
    
    try:
        idx = movies[movies["title"] == title].index[0]
    except IndexError:
        return pd.DataFrame(columns=["title", "movie_id"])

    scores = list(enumerate(cosine_sim[idx]))
    top_indices = sorted(scores, key=lambda x: x[1], reverse=True)[1:6]
    movie_indices = [i[0] for i in top_indices]

    return movies.iloc[movie_indices][["title", "movie_id"]]

# ==== DJANGO VIEW ====
def recommend_movies(request):
    movies = load_movies()
    movie_titles = movies['title'].values
    selected_movie = ''
    posters = []

    if request.method == 'POST':
        selected_movie = request.POST.get('movie', '')
        if selected_movie:
            recommended = recommend(selected_movie)
            posters = [get_movie_poster(mid) for mid in recommended['movie_id']]

    return render(request, 'recommend_movies.html', {
        'movies_titles': movie_titles,
        'posters': posters,
        'selected_movie': selected_movie
    })
