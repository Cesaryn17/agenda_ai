from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db.models import Q, Count
from django import forms
from .models import Categoria, Servico, Anuncio, Imagem, Avaliacao
from django.contrib.contenttypes.admin import GenericTabularInline

class StatusFilter(admin.SimpleListFilter):
    title = _('Status')
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('ativo', _('Ativos')),
            ('pendente', _('Pendentes')),
            ('finalizado', _('Finalizados')),
            ('desativado', _('Desativados')),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset

class DestaqueFilter(admin.SimpleListFilter):
    title = _('Destaque')
    parameter_name = 'destaque'

    def lookups(self, request, model_admin):
        return [
            ('sim', _('Em destaque')),
            ('nao', _('Sem destaque')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'sim':
            return queryset.filter(destaque=True)
        elif self.value() == 'nao':
            return queryset.filter(destaque=False)
        return queryset

class CategoriaAtivaFilter(admin.SimpleListFilter):
    title = _('Categoria ativa')
    parameter_name = 'categoria_ativa'

    def lookups(self, request, model_admin):
        return [
            ('sim', _('Categorias ativas')),
            ('nao', _('Categorias inativas')),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'sim':
            return queryset.filter(categoria__ativa=True)
        elif self.value() == 'nao':
            return queryset.filter(categoria__ativa=False)
        return queryset

def marcar_como_destaque(modeladmin, request, queryset):
    updated = queryset.update(destaque=True)
    modeladmin.message_user(
        request, 
        _("%(count)d itens marcados como destaque com sucesso.") % {'count': updated},
        messages.SUCCESS
    )
marcar_como_destaque.short_description = _("Marcar selecionados como destaque")

def remover_destaque(modeladmin, request, queryset):
    updated = queryset.update(destaque=False)
    modeladmin.message_user(
        request, 
        _("%(count)d itens removidos do destaque com sucesso.") % {'count': updated},
        messages.SUCCESS
    )
remover_destaque.short_description = _("Remover selecionados do destaque")

def ativar_itens(modeladmin, request, queryset):
    updated = queryset.update(status='ativo')
    modeladmin.message_user(
        request, 
        _("%(count)d itens ativados com sucesso.") % {'count': updated},
        messages.SUCCESS
    )
ativar_itens.short_description = _("Ativar selecionados")

def desativar_itens(modeladmin, request, queryset):
    updated = queryset.update(status='desativado')
    modeladmin.message_user(
        request, 
        _("%(count)d itens desativados com sucesso.") % {'count': updated},
        messages.SUCCESS
    )
desativar_itens.short_description = _("Desativar selecionados")

def aprovar_avaliacoes(modeladmin, request, queryset):
    updated = queryset.update(aprovada=True)
    modeladmin.message_user(
        request, 
        _("%(count)d avaliações aprovadas com sucesso.") % {'count': updated},
        messages.SUCCESS
    )
aprovar_avaliacoes.short_description = _("Aprovar avaliações selecionadas")

class ImagemInline(admin.TabularInline):
    model = Imagem
    extra = 1
    fields = ('imagem_preview', 'imagem', 'ordem', 'capa')
    readonly_fields = ('imagem_preview',)
    
    def imagem_preview(self, obj):
        if obj.imagem:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px; object-fit: cover;" />', 
                obj.imagem.url
            )
        return _("Sem imagem")
    imagem_preview.short_description = _('Pré-visualização')

class AvaliacaoGenericInline(GenericTabularInline):
    model = Avaliacao
    ct_field = 'content_type'
    ct_fk_field = 'object_id'
    extra = 0
    readonly_fields = ('usuario_avaliador', 'nota', 'comentario', 'data_criacao', 'aprovada')
    fields = ('usuario_avaliador', 'nota', 'comentario', 'resposta', 'data_criacao', 'aprovada')
    classes = ['collapse']
    
    def has_add_permission(self, request, obj=None):
        return False

class ServicoAdminForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = '__all__'
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

class AnuncioAdminForm(forms.ModelForm):
    class Meta:
        model = Anuncio
        fields = '__all__'
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'slug', 'destaque', 'ordem_menu', 'ativa', 'total_itens']
    list_editable = ['destaque', 'ordem_menu', 'ativa']
    search_fields = ['titulo', 'slug']
    prepopulated_fields = {'slug': ('titulo',)}
    list_filter = ['destaque', 'ativa', 'ordem_menu']
    actions = [marcar_como_destaque, remover_destaque, ativar_itens, desativar_itens]
    
    fieldsets = (
        (None, {
            'fields': ('titulo', 'slug', 'imagem')
        }),
        (_('Configurações'), {
            'fields': ('destaque', 'ordem_menu', 'ativa')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            total_itens_count=Count('servicos') + Count('anuncios')
        )

    def total_itens(self, obj):
        return obj.total_itens_count
    total_itens.short_description = _('Total de Itens')
    total_itens.admin_order_field = 'total_itens_count'

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    form = ServicoAdminForm
    list_display = [
        'titulo', 
        'usuario', 
        'categoria', 
        'valor_formatado', 
        'status', 
        'destaque',
        'visualizacoes'
    ]
    list_filter = [
        'categoria', 
        'status', 
        'destaque', 
        'tipo',
        CategoriaAtivaFilter,
        StatusFilter,
        DestaqueFilter
    ]
    search_fields = ['titulo', 'descricao', 'usuario__email', 'usuario__username']
    list_select_related = ['usuario', 'categoria']
    inlines = [ImagemInline, AvaliacaoGenericInline]
    raw_id_fields = ['usuario', 'localizacao']
    readonly_fields = ['visualizacoes', 'data_criacao', 'data_atualizacao']
    actions = [marcar_como_destaque, remover_destaque, ativar_itens, desativar_itens]
    
    fieldsets = (
        (None, {
            'fields': ('titulo', 'descricao', 'usuario', 'categoria')
        }),
        (_('Detalhes'), {
            'fields': ('valor', 'tipo', 'disponivel_24h', 'tempo_entrega')
        }),
        (_('Localização'), {
            'fields': ('localizacao', 'whatsapp'),
            'classes': ('collapse',)
        }),
        (_('Status e Métricas'), {
            'fields': ('status', 'destaque', 'visualizacoes', 'data_criacao', 'data_atualizacao')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'usuario', 'categoria'
        )

    def valor_formatado(self, obj):
        return f"R$ {obj.valor:,.2f}"
    valor_formatado.short_description = _('Valor')
    valor_formatado.admin_order_field = 'valor'

    def view_on_site(self, obj):
        return obj.get_absolute_url()

@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    form = AnuncioAdminForm
    list_display = [
        'titulo', 
        'usuario', 
        'categoria', 
        'valor_formatado', 
        'estado_produto', 
        'quantidade',
        'status',
        'destaque',
        'visualizacoes'
    ]
    list_filter = [
        'categoria', 
        'estado_produto', 
        'status',
        'destaque',
        CategoriaAtivaFilter,
        StatusFilter,
        DestaqueFilter
    ]
    search_fields = ['titulo', 'descricao', 'usuario__email', 'usuario__username', 'marca']
    list_select_related = ['usuario', 'categoria']
    inlines = [ImagemInline, AvaliacaoGenericInline]
    list_editable = ['quantidade']
    raw_id_fields = ['usuario', 'localizacao']
    readonly_fields = ['visualizacoes', 'data_criacao', 'data_atualizacao']
    actions = [marcar_como_destaque, remover_destaque, ativar_itens, desativar_itens]
    
    fieldsets = (
        (None, {
            'fields': ('titulo', 'descricao', 'usuario', 'categoria')
        }),
        (_('Detalhes do Produto'), {
            'fields': ('valor', 'estado_produto', 'quantidade', 'marca', 'garantia')
        }),
        (_('Localização'), {
            'fields': ('localizacao', 'whatsapp'),
            'classes': ('collapse',)
        }),
        (_('Status e Métricas'), {
            'fields': ('status', 'destaque', 'visualizacoes', 'data_criacao', 'data_atualizacao')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'usuario', 'categoria'
        )

    def valor_formatado(self, obj):
        return f"R$ {obj.valor:,.2f}"
    valor_formatado.short_description = _('Valor')
    valor_formatado.admin_order_field = 'valor'

    def view_on_site(self, obj):
        return obj.get_absolute_url()

@admin.register(Imagem)
class ImagemAdmin(admin.ModelAdmin):
    list_display = [
        'imagem_preview', 
        'item_associado_link', 
        'tipo_item', 
        'ordem', 
        'capa'
    ]
    list_filter = ['capa']
    search_fields = ['servico__titulo', 'anuncio__titulo']
    list_editable = ['ordem', 'capa']
    readonly_fields = ['imagem_preview']
    list_per_page = 20
    
    def imagem_preview(self, obj):
        if obj.imagem:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 80px; object-fit: cover;" />', 
                obj.imagem.url
            )
        return _("Sem imagem")
    imagem_preview.short_description = _('Imagem')

    def item_associado(self, obj):
        if obj.servico:
            return obj.servico.titulo
        return obj.anuncio.titulo
    item_associado.short_description = _('Item Associado')

    def item_associado_link(self, obj):
        if obj.servico:
            url = reverse('admin:produtos_servico_change', args=[obj.servico.id])
            return format_html('<a href="{}">{}</a>', url, obj.servico.titulo)
        elif obj.anuncio:
            url = reverse('admin:produtos_anuncio_change', args=[obj.anuncio.id])
            return format_html('<a href="{}">{}</a>', url, obj.anuncio.titulo)
        return _("Nenhum")
    item_associado_link.short_description = _('Item Associado')

    def tipo_item(self, obj):
        if obj.servico:
            return _("Serviço")
        return _("Anúncio")
    tipo_item.short_description = _('Tipo')

@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = [
        'usuario_avaliador', 
        'nota', 
        'item_associado_link', 
        'tipo_item', 
        'aprovada', 
        'data_criacao',
        'tem_resposta'
    ]
    list_filter = ['nota', 'data_criacao', 'aprovada']
    search_fields = [
        'comentario', 
        'usuario_avaliador__email', 
        'usuario_avaliador__username',
        'servico__titulo',
        'anuncio__titulo'
    ]
    readonly_fields = ['usuario_avaliador', 'data_criacao', 'item_associado_info']
    raw_id_fields = ['usuario_avaliador']
    list_editable = ['aprovada']
    actions = [aprovar_avaliacoes]
    
    fieldsets = (
        (None, {
            'fields': ('usuario_avaliador', 'nota', 'comentario', 'aprovada')
        }),
        (_('Resposta'), {
            'fields': ('resposta', 'data_resposta'),
            'classes': ('collapse',)
        }),
        (_('Informações do Item'), {
            'fields': ('item_associado_info',),
            'classes': ('collapse',)
        }),
        (_('Datas'), {
            'fields': ('data_criacao',),
            'classes': ('collapse',)
        }),
    )

    def item_associado(self, obj):
        return str(obj.item)
    item_associado.short_description = _('Item Avaliado')

    def item_associado_link(self, obj):
        if obj.servico:
            url = reverse('admin:produtos_servico_change', args=[obj.servico.id])
            return format_html('<a href="{}">{}</a>', url, obj.servico.titulo)
        elif obj.anuncio:
            url = reverse('admin:produtos_anuncio_change', args=[obj.anuncio.id])
            return format_html('<a href="{}">{}</a>', url, obj.anuncio.titulo)
        return _("Nenhum")
    item_associado_link.short_description = _('Item Avaliado')

    def item_associado_info(self, obj):
        if obj.servico:
            return f"Serviço: {obj.servico.titulo} (ID: {obj.servico.id})"
        elif obj.anuncio:
            return f"Anúncio: {obj.anuncio.titulo} (ID: {obj.anuncio.id})"
        return _("Item não encontrado")
    item_associado_info.short_description = _('Informações do Item')

    def tipo_item(self, obj):
        if obj.servico:
            return _("Serviço")
        return _("Anúncio")
    tipo_item.short_description = _('Tipo')

    def tem_resposta(self, obj):
        return bool(obj.resposta)
    tem_resposta.short_description = _('Tem Resposta')
    tem_resposta.boolean = True