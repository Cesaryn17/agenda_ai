from django.contrib import admin
from .models import Chat, Mensagem

class MensagemInline(admin.TabularInline):
    model = Mensagem
    extra = 0 
    readonly_fields = ('remetente', 'conteudo', 'data_envio') 

class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_participantes')
    filter_horizontal = ('participantes',) 
    inlines = [MensagemInline]
    
    def display_participantes(self, obj):
        return ", ".join([p.nome for p in obj.participantes.all()])
    display_participantes.short_description = 'Participantes'

admin.site.register(Chat, ChatAdmin)