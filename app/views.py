import os
import pickle
import requests
import pandas as pd
from pathlib import Path
from django.shortcuts import render
from functools import lru_cache
from dotenv import load_dotenv

# ==== Load environment variables ====
load_dotenv()
TMDB_API_TOKEN = f"Bearer {os.getenv('API_Key')}"  # Make sure API_Key is in your .env file

# ==== Google Drive File IDs ====
MOVIES_FILE_ID = "1M6wNUUrQ4UKdfCIkT0hQQRd0qmQs8ObU"
SIMILARITY_FILE_ID = "1ABm3TLUBi3ih18g9voWOGbmmoIC4ooTU"

# ==== Utility to download large files from Google Drive ====
def download_large_file_from_google_drive(file_id):
    session = requests.Session()
    URL = "https://drive.google.com/uc?export=download"

    # Initial request
    response = session.get(URL, params={'id': file_id}, stream=True)
    
    # Check if Google asks for confirmation
    token = None
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            token = value

    if token:
        response = session.get(URL, params={'id': file_id, 'confirm': token}, stream=True)

    # Read binary content
    content = b''.join(chunk for chunk in response.iter_content(32768))

    # Check for HTML instead of binary
    if content[:1] == b'<':
        print(content[:200].decode())  # Print error page for debugging
        raise ValueError("Downloaded content is HTML, not a valid pickle file. Check file permissions or quota.")

    return content



# ==== Cached loading of model data ====
@lru_cache(maxsize=1)
def load_movies():
    content = download_large_file_from_google_drive(MOVIES_FILE_ID)
    return pd.DataFrame(pickle.loads(content))

@lru_cache(maxsize=1)
def load_similarity():
    content = download_large_file_from_google_drive(SIMILARITY_FILE_ID)
    return pickle.loads(content)

# ==== Get movie poster from TMDB ====
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

# ==== Recommendation logic ====
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

# ==== Django view ====
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
