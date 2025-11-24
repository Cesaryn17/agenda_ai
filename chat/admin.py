from django.contrib import admin
from .models import Chat, MensagemChat, MensagemVisualizacao

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_group', 'nome_grupo', 'data_criacao']
    list_filter = ['is_group', 'data_criacao']
    filter_horizontal = ['participantes']
    search_fields = ['nome_grupo', 'participantes__nome']
    readonly_fields = ['id', 'data_criacao']

@admin.register(MensagemChat)
class MensagemChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'chat', 'remetente', 'tipo', 'data_envio', 'lida']
    list_filter = ['tipo', 'lida', 'data_envio']
    search_fields = ['conteudo', 'remetente__nome', 'chat__id']
    readonly_fields = ['id', 'data_envio']
    raw_id_fields = ['chat', 'remetente', 'respondendo_a']

@admin.register(MensagemVisualizacao)
class MensagemVisualizacaoAdmin(admin.ModelAdmin):
    list_display = ['mensagem', 'usuario', 'data_visualizacao']
    list_filter = ['data_visualizacao']
    search_fields = ['mensagem__conteudo', 'usuario__nome']
    readonly_fields = ['data_visualizacao']
    raw_id_fields = ['mensagem', 'usuario']