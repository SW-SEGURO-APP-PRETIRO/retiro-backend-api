from django.urls import path

from .web_views import chat_general

urlpatterns = [path("", chat_general, name="web-chat")]