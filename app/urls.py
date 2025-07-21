from django.urls import path
from  . import views
urlpatterns = [
    path('recommend/',views.recommend_movies, name='recommend_movies'),
]
