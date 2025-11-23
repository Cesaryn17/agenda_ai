from django.utils.safestring import mark_safe
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.admin import GenericTabularInline
from django.db import models
from django.forms import CheckboxSelectMultiple
from django.contrib import admin
from .models import PaginaPessoal, PostagemProduto, MidiaPostagem, SeguidorPagina

from .models import (
    CustomUser, 
    Notificacao, 
    Favorito, 
    HistoricoBusca, 
    Localizacao,
    Mensagem,
    ConfiguracaoUsuario
)

from .forms import CustomUserCreationForm, CustomUserChangeForm

class ConfiguracaoUsuarioInline(admin.StackedInline):
    model = ConfiguracaoUsuario
    can_delete = False
    verbose_name_plural = 'Configurações do Usuário'
    fields = (
        'receber_email',
        'modo_escuro',
        'idioma',
        'notificacoes_push',
        'mostrar_localizacao'
    )

class NotificacaoInline(admin.TabularInline):
    model = Notificacao
    extra = 0
    readonly_fields = ('data_criacao',)
    fields = ('titulo', 'mensagem', 'tipo', 'lida', 'data_criacao')
    can_delete = True

class HistoricoBuscaInline(admin.TabularInline):
    model = HistoricoBusca
    extra = 0
    readonly_fields = ('data_busca',)
    fields = ('termo', 'localizacao', 'data_busca')
    can_delete = True

class FavoritoUsuarioInline(GenericTabularInline):
    """
    Inline para exibir Favoritos de um usuário na página do CustomUser.
    """
    model = Favorito
    extra = 0
    readonly_fields = ('data_criacao', 'content_object',)
    fields = ('content_object', 'data_criacao')
    can_delete = True

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = (
        'email', 
        'nome', 
        'nome_utilizador',
        'premium', 
        'is_staff', 
        'is_active', 
        'data_criacao',
        'foto_perfil_preview'
    )
    list_filter = ('premium', 'is_staff', 'is_active', 'localizacao', 'email_verificado')
    search_fields = ('email', 'nome', 'cpf', 'nome_utilizador')
    ordering = ('-data_criacao',)
    
    readonly_fields = (
        'foto_perfil_preview',
        'data_criacao',
        'ultima_atualizacao',
        'last_login'
    )
    
    filter_horizontal = ('groups', 'user_permissions',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Informações Pessoais'), {
            'fields': (
                'nome', 
                'nome_utilizador',
                'foto_perfil',
                'foto_perfil_preview',
                'data_nascimento',
                'cpf',
                'telefone',
                'localizacao'
            )
        }),
        (_('Status'), {
            'fields': (
                'premium',
                'creditos',
                'reputacao',
                'email_verificado'
            )
        }),
        (_('Permissões'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            )
        }),
        (_('Datas Importantes'), {
            'fields': (
                'last_login',
                'data_criacao',
                'ultima_atualizacao'
            )
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'nome',
                'nome_utilizador',
                'password',
                'is_staff',
                'is_active'
            )
        }),
    )

    inlines = []

    def foto_perfil_preview(self, obj):
        if obj.foto_perfil:
            return mark_safe(f'<img src="{obj.foto_perfil.url}" width="100" style="border-radius: 50%;" />')
        return "Sem foto"
    
    foto_perfil_preview.short_description = _("Pré-visualização")

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

class FavoritoInline(GenericTabularInline):
    model = Favorito
    extra = 0
    readonly_fields = ('data_criacao',)
    fields = ('usuario', 'content_object', 'data_criacao')
    can_delete = True

@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'content_object', 'content_type', 'data_criacao')
    list_filter = ('content_type', 'data_criacao')
    search_fields = ('usuario__nome', 'usuario__email')
    date_hierarchy = 'data_criacao'
    raw_id_fields = ('usuario',)
    readonly_fields = ('data_criacao', 'content_object_link')
    
    fieldsets = (
        (None, {
            'fields': ('usuario', 'content_type', 'object_id')
        }),
        (_('Detalhes'), {
            'fields': ('content_object_link', 'data_criacao')
        }),
    )

    def content_object_link(self, obj):
        if obj.content_object:
            try:
                url = obj.content_object.get_absolute_url()
                return mark_safe(f'<a href="{url}" target="_blank">{str(obj.content_object)}</a>')
            except:
                return str(obj.content_object)
        return "Nenhum objeto associado"
    
    content_object_link.short_description = _("Item Favorito")


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'usuario', 'tipo', 'lida', 'data_criacao')
    list_filter = ('tipo', 'lida', 'data_criacao')
    search_fields = ('titulo', 'mensagem', 'usuario__nome', 'usuario__email')
    date_hierarchy = 'data_criacao'
    readonly_fields = ('data_criacao',)
    raw_id_fields = ('usuario',)
    list_select_related = ('usuario',)
    list_per_page = 50
    
    actions = ['marcar_como_lida', 'marcar_como_nao_lida']
    
    @admin.action(description=_("Marcar notificações selecionadas como lidas"))
    def marcar_como_lida(self, request, queryset):
        updated = queryset.update(lida=True)
        self.message_user(request, f"{updated} notificação(s) marcada(s) como lida(s).")
    
    @admin.action(description=_("Marcar notificações selecionadas como não lidas"))
    def marcar_como_nao_lida(self, request, queryset):
        updated = queryset.update(lida=False)
        self.message_user(request, f"{updated} notificação(s) marcada(s) como não lida(s).")


@admin.register(HistoricoBusca)
class HistoricoBuscaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'termo', 'get_categoria', 'localizacao', 'data_busca')
    list_filter = ('data_busca', 'localizacao')
    search_fields = ('termo', 'usuario__nome', 'usuario__email')
    raw_id_fields = ('usuario', 'localizacao')
    date_hierarchy = 'data_busca'
    list_select_related = ('usuario', 'localizacao')
    
    def get_categoria(self, obj):
        if obj.categoria:
            return str(obj.categoria)
        return "-"
    get_categoria.short_description = 'Categoria'


@admin.register(Localizacao)
class LocalizacaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'lat', 'lng')
    search_fields = ('nome',)
    list_per_page = 50
    ordering = ('nome',)


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ('remetente', 'destinatario', 'mensagem_curta', 'data_envio', 'lida')
    list_filter = ('lida', 'data_envio')
    search_fields = ('remetente__nome', 'destinatario__nome', 'mensagem')
    date_hierarchy = 'data_envio'
    readonly_fields = ('data_envio', 'conversa_id')
    raw_id_fields = ('remetente', 'destinatario')
    list_select_related = ('remetente', 'destinatario')
    
    actions = ['marcar_como_lida', 'marcar_como_nao_lida']

    def mensagem_curta(self, obj):
        return f"{obj.mensagem[:50]}..." if len(obj.mensagem) > 50 else obj.mensagem
    mensagem_curta.short_description = "Mensagem"

    @admin.action(description=_("Marcar mensagens selecionadas como lidas"))
    def marcar_como_lida(self, request, queryset):
        updated = queryset.update(lida=True)
        self.message_user(request, f"{updated} mensagem(s) marcada(s) como lida(s).")

    @admin.action(description=_("Marcar mensagens selecionadas como não lidas"))
    def marcar_como_nao_lida(self, request, queryset):
        updated = queryset.update(lida=False)
        self.message_user(request, f"{updated} mensagem(s) marcada(s) como não lida(s).")


@admin.register(ConfiguracaoUsuario)
class ConfiguracaoUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'receber_email', 'modo_escuro', 'idioma', 'notificacoes_push')
    list_filter = ('receber_email', 'modo_escuro', 'idioma', 'notificacoes_push')
    search_fields = ('usuario__nome', 'usuario__email')
    raw_id_fields = ('usuario',)
    list_select_related = ('usuario',)

@admin.register(PaginaPessoal)
class PaginaPessoalAdmin(admin.ModelAdmin):
    list_display = ['nome_pagina', 'usuario', 'visibilidade', 'ativa', 'data_criacao']
    list_filter = ['visibilidade', 'ativa', 'data_criacao']
    search_fields = ['nome_pagina', 'usuario__nome', 'usuario__email']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    raw_id_fields = ['usuario']
    
    actions = ['ativar_paginas', 'desativar_paginas']
    
    def ativar_paginas(self, request, queryset):
        updated = queryset.update(ativa=True)
        self.message_user(request, f"{updated} página(s) ativada(s) com sucesso!")
    ativar_paginas.short_description = "Ativar páginas selecionadas"
    
    def desativar_paginas(self, request, queryset):
        updated = queryset.update(ativa=False)
        self.message_user(request, f"{updated} página(s) desativada(s) com sucesso!")
    desativar_paginas.short_description = "Desativar páginas selecionadas"

class MidiaPostagemInline(admin.TabularInline):
    model = MidiaPostagem
    extra = 1
    readonly_fields = ['data_upload']

@admin.register(PostagemProduto)
class PostagemProdutoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'pagina', 'status', 'ativa', 'data_publicacao', 'visualizacoes']
    list_filter = ['status', 'ativa', 'data_publicacao']
    search_fields = ['titulo', 'descricao', 'pagina__nome_pagina']
    readonly_fields = ['data_criacao', 'data_atualizacao', 'visualizacoes', 'curtidas_count']
    raw_id_fields = ['pagina', 'produto_relacionado', 'localizacao']
    inlines = [MidiaPostagemInline]
    
    actions = ['publicar_postagens', 'arquivar_postagens', 'mover_para_rascunho']
    
    def publicar_postagens(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='publicado', data_publicacao=timezone.now())
        self.message_user(request, f"{updated} postagem(s) publicada(s) com sucesso!")
    publicar_postagens.short_description = "Publicar postagens selecionadas"
    
    def arquivar_postagens(self, request, queryset):
        updated = queryset.update(status='arquivado')
        self.message_user(request, f"{updated} postagem(s) arquivada(s) com sucesso!")
    arquivar_postagens.short_description = "Arquivar postagens selecionadas"
    
    def mover_para_rascunho(self, request, queryset):
        updated = queryset.update(status='rascunho')
        self.message_user(request, f"{updated} postagem(s) movida(s) para rascunho!")
    mover_para_rascunho.short_description = "Mover para rascunho"

@admin.register(MidiaPostagem)
class MidiaPostagemAdmin(admin.ModelAdmin):
    list_display = ['postagem', 'tipo', 'ordem', 'data_upload']
    list_filter = ['tipo', 'data_upload']
    search_fields = ['postagem__titulo']
    readonly_fields = ['data_upload']

@admin.register(SeguidorPagina)
class SeguidorPaginaAdmin(admin.ModelAdmin):
    list_display = ['pagina', 'usuario', 'data_seguimento']
    list_filter = ['data_seguimento']
    search_fields = ['pagina__nome_pagina', 'usuario__nome']
    readonly_fields = ['data_seguimento']
    raw_id_fields = ['pagina', 'usuario']