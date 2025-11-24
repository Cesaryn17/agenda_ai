from django.db import models
from django.conf import settings
import uuid

class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participantes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='chats_participados'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    ultima_mensagem = models.ForeignKey(
        'MensagemChat',  
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_ultima_mensagem'
    )
    is_group = models.BooleanField(default=False)
    nome_grupo = models.CharField(max_length=100, blank=True, null=True)
    foto_grupo = models.ImageField(upload_to='chat_grupos/', blank=True, null=True)
    
    def atualizar_ultima_mensagem(self):
        ultima_mensagem = self.mensagens_chat.filter(excluida=False).order_by('-data_envio').first()
        self.ultima_mensagem = ultima_mensagem
        self.save()
    
    @property
    def outro_usuario(self):
        if hasattr(self, '_outro_usuario'):
            return self._outro_usuario
        return None

    def __str__(self):
        if self.is_group:
            return f"Grupo: {self.nome_grupo or f'Chat {self.id}'}"
        return f"Chat {self.id}"

    def atualizar_ultima_mensagem(self):
        ultima = self.mensagens_chat.order_by('-data_envio').first()
        self.ultima_mensagem = ultima
        self.save()

class MensagemChat(models.Model): 
    TIPO_CHOICES = [
        ('texto', 'Texto'),
        ('imagem', 'Imagem'),
        ('audio', 'Áudio'),
        ('video', 'Vídeo'),
        ('localizacao', 'Localização'),
        ('arquivo', 'Arquivo'),
        ('contato', 'Contato'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='mensagens_chat'
    )
    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensagens_chat_enviadas'  
    )
    conteudo = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='texto')
    arquivo = models.FileField(upload_to='mensagens/', blank=True, null=True)
    duracao_audio = models.IntegerField(blank=True, null=True)  
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    data_envio = models.DateTimeField(auto_now_add=True)
    data_edicao = models.DateTimeField(blank=True, null=True)
    lida = models.BooleanField(default=False)
    excluida = models.BooleanField(default=False)
    respondendo_a = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='respostas'
    )

    class Meta:
        ordering = ['data_envio']
        indexes = [
            models.Index(fields=['chat', 'data_envio']),
            models.Index(fields=['remetente', 'data_envio']),
        ]
        verbose_name = "Mensagem de Chat"  
        verbose_name_plural = "Mensagens de Chat"  

    def __str__(self):
        return f"{self.tipo} - {self.remetente} - {self.data_envio}"

    def marcar_como_lida(self):
        self.lida = True
        self.save()

class MensagemVisualizacao(models.Model):
    mensagem = models.ForeignKey(
        MensagemChat,  
        on_delete=models.CASCADE, 
        related_name='visualizacoes'
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    data_visualizacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['mensagem', 'usuario']
        verbose_name = "Visualização de Mensagem"  
        verbose_name_plural = "Visualizações de Mensagens" 

    def __str__(self):
        return f"{self.usuario.nome} visualizou mensagem"