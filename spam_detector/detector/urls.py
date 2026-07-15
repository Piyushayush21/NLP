from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('predict/', views.predict_ajax, name='predict_ajax'),
    path('batch/', views.predict_batch, name='predict_batch'),
    path('history/', views.history, name='history'),
    path('history/delete/', views.delete_history, name='delete_history'),
    path('dashboard/', views.dashboard, name='dashboard'),
]
