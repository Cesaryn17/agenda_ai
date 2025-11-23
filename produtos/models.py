from django.db import models
from django.utils.text import slugify
from django.core.validators import (
    MinValueValidator, 
    MaxValueValidator, 
    FileExtensionValidator,
    MinLengthValidator
)
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from core.models import Localizacao
import os
from uuid import uuid4

MAX_LENGTH = {
    'TITULO': 200,
    'DESCRICAO': 2000,
    'TELEFONE': 20,
    'MARCA': 100,
    'CATEGORIA_TITULO': 100,
    'SLUG': 100,
    'COMENTARIO': 500
}

VALID_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']
MAX_FILE_SIZE_MB = 5  

def upload_to_imagens(instance, filename):
    """Gera caminho único para upload de imagens"""
    ext = os.path.splitext(filename)[1]
    item_type = 'servicos' if hasattr(instance, 'servico') else 'anuncios'
    return f'imagens/{item_type}/{instance.id}/{uuid4().hex}{ext}'

def upload_to_categorias(instance, filename):
    """Gera caminho organizado para imagens de categorias"""
    ext = os.path.splitext(filename)[1]
    return f'categorias/{instance.slug}/{uuid4().hex}{ext}'

def validate_image_size(value):
    """Validador personalizado para tamanho de imagem"""
    limit = MAX_FILE_SIZE_MB * 1024 * 1024
    if value.size > limit:
        raise ValidationError(f'Tamanho máximo do arquivo: {MAX_FILE_SIZE_MB}MB')

class CategoriaQuerySet(models.QuerySet):
    def ativas(self):
        return self.filter(ativa=True)
    
    def destaques(self):
        return self.filter(destaque=True, ativa=True)
    
    def para_menu(self):
        return self.ativas().order_by('ordem_menu', 'titulo')

class CategoriaManager(models.Manager):
    def get_queryset(self):
        return CategoriaQuerySet(self.model, using=self._db)
    
    def ativas(self):
        return self.get_queryset().ativas()
    
    def destaques(self):
        return self.get_queryset().destaques()
    
    def para_menu(self):
        return self.get_queryset().para_menu()

class Categoria(models.Model):
    """Modelo para categorias de produtos e serviços"""
    objects = CategoriaManager()
    
    class Meta:
        verbose_name = _("Categoria")
        verbose_name_plural = _("Categorias")
        ordering = ['ordem_menu', 'titulo']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['destaque']),
            models.Index(fields=['ativa']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['slug'],
                name='unique_categoria_slug'
            ),
        ]

    titulo = models.CharField(
        max_length=MAX_LENGTH['CATEGORIA_TITULO'],
        unique=True,
        verbose_name=_("Título"),
        help_text=_("Título da categoria (máx. %(max)d caracteres)") % {'max': MAX_LENGTH['CATEGORIA_TITULO']},
        validators=[MinLengthValidator(3)]
    )
    
    slug = models.SlugField(
        max_length=MAX_LENGTH['SLUG'],
        unique=True,
        blank=True,
        verbose_name=_("Slug"),
        help_text=_("Identificador único para URLs (gerado automaticamente)")
    )
    
    imagem = models.ImageField(
        upload_to=upload_to_categorias,
        verbose_name=_("Ícone/Imagem"),
        validators=[
            FileExtensionValidator(allowed_extensions=VALID_IMAGE_EXTENSIONS),
            validate_image_size
        ],
        help_text=_("Imagem representativa da categoria (max %(max)dMB)") % {'max': MAX_FILE_SIZE_MB}
    )
    
    destaque = models.BooleanField(
        default=False,
        verbose_name=_("Destaque na Home"),
        help_text=_("Se a categoria aparece na página inicial")
    )
    
    ordem_menu = models.PositiveSmallIntegerField(
        default=99,
        verbose_name=_("Ordem no Menu"),
        help_text=_("Ordem de exibição no menu (menor número aparece primeiro)")
    )
    
    ativa = models.BooleanField(
        default=True,
        verbose_name=_("Ativa"),
        help_text=_("Se a categoria está ativa e visível")
    )

    def __str__(self):
        return self.titulo
    
    def clean(self):
        """Validações adicionais antes de salvar"""
        if not self.slug:
            self.slug = slugify(self.titulo)
        
        if len(self.slug) > MAX_LENGTH['SLUG']:
            self.slug = self.slug[:MAX_LENGTH['SLUG']]
    
    def save(self, *args, **kwargs):
        self.clean()
        
        if self.destaque:
            Categoria.objects.filter(destaque=True).exclude(pk=self.pk).update(destaque=False)
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('categoria-detail', kwargs={'slug': self.slug})

class ItemBase(models.Model):
    """Classe abstrata base para Serviço e Anúncio"""
    
    STATUS_CHOICES = [
        ('ativo', _('Ativo')),
        ('pendente', _('Pendente')),
        ('finalizado', _('Finalizado')),
        ('desativado', _('Desativado')),
    ]

    titulo = models.CharField(
        max_length=MAX_LENGTH['TITULO'],
        verbose_name=_("Título"),
        help_text=_("Título do item (máx. %(max)d caracteres)") % {'max': MAX_LENGTH['TITULO']},
        validators=[MinLengthValidator(5)]
    )
    
    descricao = models.TextField(
        max_length=MAX_LENGTH['DESCRICAO'],
        verbose_name=_("Descrição Detalhada"),
        help_text=_("Descrição completa do item (máx. %(max)d caracteres)") % {'max': MAX_LENGTH['DESCRICAO']}
    )
    
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Valor"),
        validators=[MinValueValidator(0.01)],
        help_text=_("Valor em R$ (use . para decimais)")
    )
    
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='%(class)ss',
        verbose_name=_("Categoria"),
        help_text=_("Categoria principal do item")
    )
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(class)s_criados',
        verbose_name=_("Criador")
    )
    
    localizacao = models.ForeignKey(
        Localizacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Localização"),
        help_text=_("Localização principal do item")
    )
    
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Data de Criação")
    )
    
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Última Atualização")
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ativo',
        verbose_name=_("Status")
    )
    
    visualizacoes = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Visualizações"),
        editable=False
    )
    
    whatsapp = models.CharField(
        max_length=MAX_LENGTH['TELEFONE'],
        blank=True,
        verbose_name=_("WhatsApp para Contato"),
        help_text=_("Número para contato via WhatsApp (com DDD)")
    )

    class Meta:
        abstract = True
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['data_criacao']),
        ]

    def __str__(self):
        return self.titulo
    
    def incrementar_visualizacao(self):
        """Incrementa o contador de visualizações"""
        self.visualizacoes += 1
        self.save(update_fields=['visualizacoes'])
    
    def get_whatsapp_url(self):
        """Gera URL para conversa no WhatsApp"""
        if self.whatsapp:
            return f"https://wa.me/55{self.whatsapp}"
        return None

    def get_admin_url(self):
        """URL para edição no admin"""
        return reverse(
            f'admin:produtos_{self.__class__.__name__.lower()}_change',
            args=[self.id]
        )

    def clean(self):
        """Validações adicionais"""
        if self.whatsapp and not self.whatsapp.isdigit():
            raise ValidationError(
                {'whatsapp': _('O número deve conter apenas dígitos')}
            )

class ServicoQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(status='ativo')
    
    def destaques(self):
        return self.ativos().filter(destaque=True)
    
    def por_usuario(self, usuario):
        return self.filter(usuario=usuario)

class ServicoManager(models.Manager):
    def get_queryset(self):
        return ServicoQuerySet(self.model, using=self._db)
    
    def ativos(self):
        return self.get_queryset().ativos()
    
    def destaques(self):
        return self.get_queryset().destaques()
    
    def por_usuario(self, usuario):
        return self.get_queryset().por_usuario(usuario)

class Servico(ItemBase):
    """Modelo para serviços oferecidos"""
    
    TIPO_CHOICES = [
        ('presencial', _('Presencial')),
        ('online', _('Online')),
        ('misto', _('Misto')),
    ]
    
    objects = ServicoManager()
    
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='presencial',
        verbose_name=_("Tipo de Serviço")
    )
    
    destaque = models.BooleanField(
        default=False,
        verbose_name=_("Serviço em Destaque"),
        help_text=_("Aparece em posições destacadas no site")
    )
    
    disponivel_24h = models.BooleanField(
        default=False,
        verbose_name=_("Disponível 24h")
    )
    
    tempo_entrega = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Tempo de Entrega (dias)"),
        help_text=_("Tempo estimado para entrega do serviço")
    )
    
    favoritos = GenericRelation(
        'core.Favorito',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='servicos'
    )

    class Meta(ItemBase.Meta):
        verbose_name = _("Serviço")
        verbose_name_plural = _("Serviços")
        indexes = [
            models.Index(fields=['tipo']),
            models.Index(fields=['destaque']),
            models.Index(fields=['usuario', 'status']),
        ]

    def get_absolute_url(self):
        return reverse('servico-detail', kwargs={'pk': self.pk})

class AnuncioQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(status='ativo')
    
    def disponiveis(self):
        return self.ativos().filter(quantidade__gt=0)
    
    def por_usuario(self, usuario):
        return self.filter(usuario=usuario)

class AnuncioManager(models.Manager):
    def get_queryset(self):
        return AnuncioQuerySet(self.model, using=self._db)
    
    def ativos(self):
        return self.get_queryset().ativos()
    
    def disponiveis(self):
        return self.get_queryset().disponiveis()
    
    def por_usuario(self, usuario):
        return self.get_queryset().por_usuario(usuario)

class Anuncio(ItemBase):
    """Modelo para anúncios de produtos"""
    
    ESTADO_CHOICES = [
        ('novo', _('Novo')),
        ('usado', _('Usado - Em bom estado')),
        ('usado_avariado', _('Usado - Com avarias')),
    ]
    
    objects = AnuncioManager()
    
    estado_produto = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='novo',
        verbose_name=_("Estado do Produto")
    )
    
    quantidade = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantidade Disponível"),
        validators=[MinValueValidator(0)]
    )
    
    marca = models.CharField(
        max_length=MAX_LENGTH['MARCA'],
        blank=True,
        verbose_name=_("Marca/Fabricante")
    )
    
    garantia = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Garantia (meses)"),
        help_text=_("Tempo de garantia em meses (0 para sem garantia)")
    )
    
    favoritos = GenericRelation(
        'core.Favorito',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='anuncios'
    )
    
    destaque = models.BooleanField(
        default=False,
        verbose_name=_("Anúncio em Destaque"),
        help_text=_("Aparece em posições destacadas no site")
    )

    class Meta(ItemBase.Meta):
        verbose_name = _("Anúncio")
        verbose_name_plural = _("Anúncios")
        indexes = [
            models.Index(fields=['estado_produto']),
            models.Index(fields=['quantidade']),
            models.Index(fields=['marca']),
        ]

    def get_absolute_url(self):
        return reverse('anuncio-detail', kwargs={'pk': self.pk})

    def clean(self):
        super().clean()
        if self.quantidade < 0:
            raise ValidationError(
                {'quantidade': _('A quantidade não pode ser negativa')}
            )

class ImagemQuerySet(models.QuerySet):
    def principais(self):
        return self.filter(capa=True)
    
    def para_item(self, item):
        return self.filter(
            models.Q(servico=item) | models.Q(anuncio=item)
        ).order_by('ordem')

class ImagemManager(models.Manager):
    def get_queryset(self):
        return ImagemQuerySet(self.model, using=self._db)
    
    def principais(self):
        return self.get_queryset().principais()
    
    def para_item(self, item):
        return self.get_queryset().para_item(item)

class Imagem(models.Model):
    """Modelo para imagens de serviços e anúncios"""
    
    objects = ImagemManager()
    
    imagem = models.ImageField(
        upload_to=upload_to_imagens,
        verbose_name=_("Imagem"),
        validators=[
            FileExtensionValidator(allowed_extensions=VALID_IMAGE_EXTENSIONS),
            validate_image_size
        ],
        help_text=_("Imagem do item (max %(max)dMB)") % {'max': MAX_FILE_SIZE_MB}
    )
    
    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        related_name='imagens',
        null=True,
        blank=True
    )
    
    anuncio = models.ForeignKey(
        Anuncio,
        on_delete=models.CASCADE,
        related_name='imagens',
        null=True,
        blank=True
    )
    
    ordem = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Ordem de Exibição"),
        help_text=_("Ordem para exibição das imagens (menor aparece primeiro)")
    )
    
    capa = models.BooleanField(
        default=False,
        verbose_name=_("Imagem Principal"),
        help_text=_("Se esta é a imagem principal do item")
    )
    
    data_upload = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Data de Upload")
    )

    class Meta:
        verbose_name = _("Imagem do Item")
        verbose_name_plural = _("Imagens dos Itens")
        ordering = ['ordem']
        constraints = [
            # ✅ CORREÇÃO: CheckConstraint simplificada sem condition problemática
            models.CheckConstraint(
                check=(
                    models.Q(servico__isnull=False, anuncio__isnull=True) | 
                    models.Q(servico__isnull=True, anuncio__isnull=False)
                ),
                name='imagem_linked_to_one_item_only'
            ),
            # ✅ CORREÇÃO: UniqueConstraint sem 'condition' (usamos validação no clean)
            models.UniqueConstraint(
                fields=['servico', 'capa'],
                name='unique_capa_servico'
            ),
            models.UniqueConstraint(
                fields=['anuncio', 'capa'],
                name='unique_capa_anuncio'
            ),
        ]

    def __str__(self):
        if self.servico:
            return f"Imagem de {self.servico.titulo}"
        return f"Imagem de {self.anuncio.titulo}"
    
    def clean(self):
        """Valida se a imagem está vinculada a apenas um item"""
        super().clean()
        
        # Validação: imagem deve estar vinculada a apenas um item
        if self.servico and self.anuncio:
            raise ValidationError(
                _("A imagem deve estar vinculada a apenas um serviço ou anúncio")
            )
        
        if not self.servico and not self.anuncio:
            raise ValidationError(
                _("A imagem deve estar vinculada a um serviço ou anúncio")
            )
        
        # ✅ CORREÇÃO ADICIONAL: Validação manual para capa única
        if self.capa:
            if self.servico:
                # Verifica se já existe outra imagem de capa para este serviço
                existing_capa = Imagem.objects.filter(
                    servico=self.servico, 
                    capa=True
                ).exclude(pk=self.pk).exists()
                if existing_capa:
                    raise ValidationError(
                        _("Já existe uma imagem definida como capa para este serviço. "
                          "Remova a capa atual antes de definir uma nova.")
                    )
            elif self.anuncio:
                # Verifica se já existe outra imagem de capa para este anúncio
                existing_capa = Imagem.objects.filter(
                    anuncio=self.anuncio, 
                    capa=True
                ).exclude(pk=self.pk).exists()
                if existing_capa:
                    raise ValidationError(
                        _("Já existe uma imagem definida como capa para este anúncio. "
                          "Remova a capa atual antes de definir uma nova.")
                    )
            else:
                raise ValidationError(
                    _("A imagem de capa deve estar vinculada a um serviço ou anúncio")
                )
    
    def save(self, *args, **kwargs):
        """Garante apenas uma imagem de capa por item"""
        self.clean()
        
        # Se esta imagem está sendo definida como capa, remove capa de outras
        if self.capa:
            if self.servico:
                Imagem.objects.filter(
                    servico=self.servico, 
                    capa=True
                ).exclude(pk=self.pk).update(capa=False)
            elif self.anuncio:
                Imagem.objects.filter(
                    anuncio=self.anuncio, 
                    capa=True
                ).exclude(pk=self.pk).update(capa=False)
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return self.imagem.url if self.imagem else ''
    
    @property
    def item_associado(self):
        """Retorna o item associado a esta imagem"""
        return self.servico or self.anuncio
    
    @property
    def tipo_item(self):
        """Retorna o tipo do item associado"""
        if self.servico:
            return 'servico'
        elif self.anuncio:
            return 'anuncio'
        return None

class AvaliacaoQuerySet(models.QuerySet):
    def aprovadas(self):
        return self.filter(aprovada=True)
    
    def por_item(self, item):
        content_type = ContentType.objects.get_for_model(item)
        return self.filter(
            content_type=content_type,
            object_id=item.id
        )
    
    def por_usuario(self, usuario):
        return self.filter(usuario_avaliador=usuario)

class AvaliacaoManager(models.Manager):
    def get_queryset(self):
        return AvaliacaoQuerySet(self.model, using=self._db)
    
    def aprovadas(self):
        return self.get_queryset().aprovadas()
    
    def por_item(self, item):
        return self.get_queryset().por_item(item)
    
    def por_usuario(self, usuario):
        return self.get_queryset().por_usuario(usuario)

class Avaliacao(models.Model):
    """Modelo para avaliações de serviços e anúncios"""
    
    objects = AvaliacaoManager()
    
    usuario_avaliador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='avaliacoes_feitas',
        verbose_name=_("Usuário Avaliador")
    )
    
    nota = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name=_("Nota (0-5)")
    )
    
    comentario = models.TextField(
        max_length=MAX_LENGTH['COMENTARIO'],
        blank=True,
        null=True,
        verbose_name=_("Comentário"),
        help_text=_("Comentário sobre o item (máx. %(max)d caracteres)") % {'max': MAX_LENGTH['COMENTARIO']}
    )
    
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Data da Avaliação")
    )
    
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': ['servico', 'anuncio']}
    )
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey('content_type', 'object_id')
    
    resposta = models.TextField(
        max_length=MAX_LENGTH['COMENTARIO'],
        blank=True,
        null=True,
        verbose_name=_("Resposta do Vendedor")
    )
    
    data_resposta = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Data da Resposta")
    )
    
    aprovada = models.BooleanField(
        default=False,
        verbose_name=_("Aprovada"),
        help_text=_("Se a avaliação foi aprovada para exibição")
    )

    class Meta:
        verbose_name = _("Avaliação")
        verbose_name_plural = _("Avaliações")
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['aprovada']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['usuario_avaliador', 'content_type', 'object_id'],
                name='unique_avaliacao_por_item'
            ),
        ]

    def __str__(self):
        return f"Avaliação de {self.usuario_avaliador} para {self.item}"
    
    def save(self, *args, **kwargs):
        if self.resposta and not self.data_resposta:
            self.data_resposta = timezone.now()
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('avaliacao-detail', kwargs={'pk': self.pk})