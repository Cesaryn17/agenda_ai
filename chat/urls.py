from django.urls import path
from . import views

urlpatterns = [
    path('chats/', views.ChatListView.as_view(), name='chat-list'),
    path('chats/criar/', views.CriarChatView.as_view(), name='criar-chat'),
    path('chats/<uuid:pk>/', views.ChatDetailView.as_view(), name='chat-detail'),
    path('chats/<uuid:chat_id>/mensagens/', views.MensagemListView.as_view(), name='mensagem-list'),
    path('chats/<uuid:chat_id>/marcar-lidas/', views.marcar_mensagens_lidas, name='marcar-lidas'),
    path('mensagens/<uuid:mensagem_id>/excluir/', views.excluir_mensagem, name='excluir-mensagem'),
]