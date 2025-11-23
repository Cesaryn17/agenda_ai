from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

class CustomUserManager(BaseUserManager):
    """
    Gerenciador de modelos para CustomUser com e-mail como identificador de login.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Cria e salva um usuário com o email e senha fornecidos.
        """
        if not email:
            raise ValueError(_('O e-mail deve ser definido'))
        
        email = self.normalize_email(email)
        
        if 'nome_utilizador' not in extra_fields:
      
            base_name = extra_fields.get('first_name', email.split('@')[0])
            extra_fields['nome_utilizador'] = self.generate_username(base_name)
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Cria e salva um superusuário com o email e senha fornecidos.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superusuário deve ter is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superusuário deve ter is_superuser=True.'))
        
        extra_fields.pop('first_name', None)
        extra_fields.pop('last_name', None)
        
        extra_fields.setdefault('nome', 'Administrador')
        extra_fields.setdefault('nome_utilizador', 'admin')
        
        return self.create_user(email, password, **extra_fields)
    
    def generate_username(self, base_name):
        """
        Gera um nome de usuário único a partir de um nome base.
        """
        import re
        base_name = re.sub(r'[^a-zA-Z0-9_]', '', str(base_name).split()[0].lower())
        if not base_name:
            base_name = 'user'
        
        final_name = base_name
        counter = 1
        
        while self.get_queryset().filter(nome_utilizador=final_name).exists():
            final_name = f"{base_name}{counter}"
            counter += 1
            
        return final_name

class Localizacao(models.Model):
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome da Localização")
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Latitude")
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Longitude")
    
    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Localização'
        verbose_name_plural = 'Localizações'
        ordering = ['nome']

class CustomUser(AbstractUser):
    username = None
    first_name = None
    last_name = None
    
    # Campos obrigatórios
    nome = models.CharField(
        max_length=255, 
        verbose_name="Nome Completo",
        help_text="Seu nome completo como deseja ser chamado"
    )
    nome_utilizador = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nome de Usuário",
        help_text="Nome único que será usado para login e identificação"
    )
    email = models.EmailField(
        unique=True,
        max_length=255,
        verbose_name="E-mail",
        error_messages={
            'unique': _("Já existe um usuário com este e-mail."),
        }
    )

    pagina_criada = models.BooleanField(
        default=False,
        verbose_name="Página Pessoal Criada"
    )
    
    # Campos opcionais
    foto_perfil = models.ImageField(
        upload_to='perfil/',
        null=True,
        blank=True,
        verbose_name="Foto de Perfil"
    )
    cpf = models.CharField(
        max_length=14,
        unique=True,
        null=True,
        blank=True,
        verbose_name="CPF",
        error_messages={
            'unique': _("Já existe um usuário com este CPF."),
        }
    )
    data_nascimento = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data de Nascimento"
    )
    localizacao = models.ForeignKey(
        Localizacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Localização"
    )
    telefone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Telefone"
    )
    
    # Campos de status
    email_verificado = models.BooleanField(
        default=False,
        verbose_name="E-mail Verificado"
    )
    premium = models.BooleanField(
        default=False,
        verbose_name="Assinatura Premium"
    )
    creditos = models.PositiveIntegerField(
        default=0,
        verbose_name="Créditos"
    )
    reputacao = models.FloatField(
        default=5.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Reputação (0-5)"
    )
    
    # ✅ CAMPO ADICIONADO: termos_aceitos
    termos_aceitos = models.BooleanField(
        default=False,
        verbose_name="Termos Aceitos"
    )
    
    # Campos de controle
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Criação"
    )
    ultima_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name="Última Atualização"
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome', 'nome_utilizador']
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.nome or self.email
    
    def clean(self):
        super().clean()
        if self.cpf and not self.validar_cpf(self.cpf):
            raise ValidationError({'cpf': _('CPF inválido.')})
    
    @staticmethod
    def validar_cpf(cpf):
        """Validação básica de CPF"""
        import re
        cpf = re.sub(r'[^0-9]', '', cpf)
        
        if len(cpf) != 11:
            return False
        
        # Verifica se todos os dígitos são iguais
        if cpf == cpf[0] * 11:
            return False
        
        # Cálculo do primeiro dígito verificador
        soma = 0
        for i in range(9):
            soma += int(cpf[i]) * (10 - i)
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto
        
        if digito1 != int(cpf[9]):
            return False
        
        # Cálculo do segundo dígito verificador
        soma = 0
        for i in range(10):
            soma += int(cpf[i]) * (11 - i)
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto
        
        if digito2 != int(cpf[10]):
            return False
        
        return True
    
    def get_full_name(self):
        """Retorna o nome completo"""
        return self.nome
    
    def get_short_name(self):
        """Retorna o primeiro nome"""
        return self.nome.split()[0] if self.nome else self.nome_utilizador
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['nome']
    
    @staticmethod
    def validar_cpf(cpf):
        """Método simples de validação de CPF (implementação básica)"""
        return len(cpf) == 14  
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['nome_utilizador']),
            models.Index(fields=['cpf']),
        ]

class Notificacao(models.Model):
    TIPO_CHOICES = [
        ('mensagem', 'Nova Mensagem'),
        ('sistema', 'Notificação do Sistema'),
        ('promocao', 'Promoção Especial'),
        ('atualizacao', 'Atualização Importante'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificacoes'
    )
    titulo = models.CharField(max_length=255)
    mensagem = models.TextField()
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='sistema'
    )
    lida = models.BooleanField(default=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    url = models.URLField(null=True, blank=True)
    icone = models.CharField(max_length=50, default='fas fa-bell')
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.nome}"

    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        indexes = [
            models.Index(fields=['usuario', 'lida']),
        ]

class Favorito(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favoritos'
    )
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'content_type', 'object_id')
        verbose_name = 'Favorito'
        verbose_name_plural = 'Favoritos'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['usuario', 'data_criacao']),
        ]

    def __str__(self):
        return f"{self.usuario.nome} - {self.content_object}"

class HistoricoBusca(models.Model):
    TIPO_CHOICES = [
        ('search', 'Busca'),
        ('view', 'Visualização'),
        ('favorite', 'Favorito'),
        ('message', 'Mensagem'),
    ]
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='historico_buscas'
    )
    
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='search',
        verbose_name="Tipo de Atividade"
    )
    
    termo = models.CharField(max_length=255, blank=True, null=True)  
    
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    data_busca = models.DateTimeField(auto_now_add=True)
    localizacao = models.ForeignKey(
        Localizacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    categoria_ct = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'app_label': 'produtos', 'model': 'categoria'},
        related_name='historico_categoria'  
    )
    categoria_id = models.PositiveIntegerField(null=True, blank=True)
    categoria = GenericForeignKey('categoria_ct', 'categoria_id')

    class Meta:
        ordering = ['-data_busca']
        verbose_name = 'Histórico de Atividade'
        verbose_name_plural = 'Históricos de Atividades'
        indexes = [
            models.Index(fields=['usuario', 'data_busca']),
            models.Index(fields=['tipo']),
            models.Index(fields=['termo']),
        ]

    def __str__(self):
        return f"{self.usuario.nome} - {self.get_tipo_display()} - {self.termo or self.content_object}"

    def get_item_relacionado(self):
        """Método auxiliar para obter o item relacionado"""
        if self.content_object:
            return self.content_object
        return None

    def get_titulo_item(self):
        """Retorna o título do item relacionado"""
        item = self.get_item_relacionado()
        if item and hasattr(item, 'titulo'):
            return item.titulo
        elif self.termo:
            return f'Busca: "{self.termo}"'
        return 'Atividade'

    class Meta:
        ordering = ['-data_busca']
        verbose_name = 'Histórico de Busca'
        verbose_name_plural = 'Históricos de Busca'
        indexes = [
            models.Index(fields=['usuario', 'data_busca']),
            models.Index(fields=['termo']),
        ]

    def __str__(self):
        return f"{self.usuario.nome} - {self.termo}"
    
    def get_titulo_item(self):
        """Método CORRIGIDO para obter o título do item relacionado"""
        try:
            if self.content_object:
                if hasattr(self.content_object, 'titulo'):
                    return self.content_object.titulo
                elif hasattr(self.content_object, 'nome'):
                    return self.content_object.nome
 
                elif hasattr(self.content_object, '__str__'):
                    return str(self.content_object)
        except:
            pass
        
        if self.tipo == 'search':
            return f'Busca: "{self.termo}"'
        elif self.tipo == 'view':
            return 'Item visualizado'
        elif self.tipo == 'favorite':
            return 'Item favoritado'
        elif self.tipo == 'message':
            return 'Mensagem enviada'
        
        return 'Atividade no sistema'
    
    def get_url_item(self):
        """Método para obter a URL do item relacionado"""
        try:
            if self.content_object:
                if hasattr(self.content_object, 'get_absolute_url'):
                    return self.content_object.get_absolute_url()
                elif hasattr(self.content_object, 'id'):
                    if self.content_type.model == 'anuncio':
                        return f'/anuncio/{self.content_object.id}/'
                    elif self.content_type.model == 'servico':
                        return f'/servico/{self.content_object.id}/'
        except:
            pass
        
        return '#'

class Mensagem(models.Model):
    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensagens_enviadas'
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensagens_recebidas'
    )
    mensagem = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False)
    conversa_id = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self):
        return f"Mensagem de {self.remetente.nome} para {self.destinatario.nome}"

    class Meta:
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
        ordering = ['data_envio']
        indexes = [
            models.Index(fields=['conversa_id']),
            models.Index(fields=['remetente', 'destinatario']),
            models.Index(fields=['data_envio']),
        ]

class ConfiguracaoUsuario(models.Model):
    IDIOMA_CHOICES = [
        ('pt-br', 'Português (Brasil)'),
        ('en', 'English'),
        ('es', 'Español'),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='configuracoes'
    )
    receber_email = models.BooleanField(
        default=True,
        verbose_name="Receber e-mails de notificação"
    )
    modo_escuro = models.BooleanField(
        default=False,
        verbose_name="Usar modo escuro"
    )
    idioma = models.CharField(
        max_length=10,
        choices=IDIOMA_CHOICES,
        default='pt-br',
        verbose_name="Idioma preferido"
    )
    notificacoes_push = models.BooleanField(
        default=True,
        verbose_name="Receber notificações push"
    )
    mostrar_localizacao = models.BooleanField(
        default=True,
        verbose_name="Compartilhar localização"
    )

    def __str__(self):
        return f"Configurações de {self.usuario.nome}"

    class Meta:
        verbose_name = "Configuração do Usuário"
        verbose_name_plural = "Configurações dos Usuários"
        
class PaginaPessoal(models.Model):
    """Modelo para páginas pessoais de usuários"""
    
    VISIBILIDADE_CHOICES = [
        ('publico', 'Público'),
        ('privado', 'Privado'),
        ('seguidores', 'Apenas Seguidores'),
    ]
    
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pagina_pessoal',
        verbose_name=_("Usuário")
    )
    
    nome_pagina = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Nome da Página"),
        help_text=_("Nome único para sua página pessoal")
    )
    
    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        verbose_name=_("Slug da Página")
    )
    
    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name=_("Biografia"),
        help_text=_("Conte um pouco sobre você e seus produtos")
    )
    
    foto_capa = models.ImageField(
        upload_to='paginas/capas/',
        null=True,
        blank=True,
        verbose_name=_("Foto de Capa")
    )
    
    visibilidade = models.CharField(
        max_length=20,
        choices=VISIBILIDADE_CHOICES,
        default='publico',
        verbose_name=_("Visibilidade da Página")
    )
    
    ativa = models.BooleanField(
        default=True,
        verbose_name=_("Página Ativa")
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Página Pessoal")
        verbose_name_plural = _("Páginas Pessoais")
        ordering = ['nome_pagina']
    
    def __str__(self):
        return f"Página de {self.usuario.nome} - {self.nome_pagina}"
    
    def clean(self):
        from django.utils.text import slugify
        if not self.slug:
            self.slug = slugify(self.nome_pagina)
        
        if PaginaPessoal.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{self.slug}-{self.usuario.id}"
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('pagina-detail', kwargs={'slug': self.slug})
    
    def total_seguidores(self):
        return self.seguidores.count()
    
    def total_postagens(self):
        return self.postagens.filter(ativa=True).count()

class SeguidorPagina(models.Model):
    """Modelo para seguidores de páginas"""
    
    pagina = models.ForeignKey(
        PaginaPessoal,
        on_delete=models.CASCADE,
        related_name='seguidores'
    )
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seguindo_paginas'
    )
    
    data_seguimento = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('pagina', 'usuario')
        verbose_name = _("Seguidor de Página")
        verbose_name_plural = _("Seguidores de Páginas")
    
    def __str__(self):
        return f"{self.usuario.nome} segue {self.pagina.nome_pagina}"

class PostagemProduto(models.Model):
    """Modelo para postagens estilo Instagram"""
    
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('publicado', 'Publicado'),
        ('arquivado', 'Arquivado'),
    ]
    
    pagina = models.ForeignKey(
        PaginaPessoal,
        on_delete=models.CASCADE,
        related_name='postagens'
    )
    
    titulo = models.CharField(max_length=200, blank=True)
    descricao = models.TextField(max_length=2200, blank=True)
    
    produto_relacionado = models.ForeignKey(
        'produtos.Anuncio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    localizacao = models.ForeignKey(
        Localizacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    hashtags = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='rascunho')
    ativa = models.BooleanField(default=True)
    
    data_publicacao = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    visualizacoes = models.PositiveIntegerField(default=0)
    curtidas_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = _("Postagem de Produto")
        verbose_name_plural = _("Postagens de Produtos")
        ordering = ['-data_publicacao']
    
    def __str__(self):
        return f"Postagem de {self.pagina.nome_pagina}"
    
    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.status == 'publicado' and not self.data_publicacao:
            self.data_publicacao = timezone.now()
        super().save(*args, **kwargs)

class MidiaPostagem(models.Model):
    """Modelo para mídias das postagens"""
    
    postagem = models.ForeignKey(
        PostagemProduto,
        on_delete=models.CASCADE,
        related_name='midias'
    )
    
    arquivo = models.FileField(upload_to='postagens/midias/')
    tipo = models.CharField(max_length=10, choices=[('imagem', 'Imagem'), ('video', 'Vídeo')])
    ordem = models.PositiveSmallIntegerField(default=0)
    
    data_upload = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['ordem']
        verbose_name = _("Mídia de Postagem")
        verbose_name_plural = _("Mídias de Postagens")
    
    def __str__(self):
        return f"Mídia {self.ordem} - {self.postagem}"

class CurtidaPostagem(models.Model):
    """Modelo para curtidas em postagens"""
    
    postagem = models.ForeignKey(
        PostagemProduto,
        on_delete=models.CASCADE,
        related_name='curtidas'
    )
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='curtidas_postagens'
    )
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('postagem', 'usuario')
        verbose_name = _("Curtida de Postagem")
        verbose_name_plural = _("Curtidas de Postagens")
    
    def __str__(self):
        return f"{self.usuario.nome} curtiu {self.postagem}"