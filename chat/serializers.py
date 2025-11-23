from rest_framework import serializers
from .models import Chat, Mensagem, MensagemVisualizacao
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    nome_completo = serializers.SerializerMethodField()
    nome_exibicao = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'foto_perfil', 'nome_completo', 'nome_exibicao']
    
    def get_nome_completo(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        elif obj.first_name:
            return obj.first_name
        elif obj.last_name:
            return obj.last_name
        else:
            return obj.username or obj.email.split('@')[0]
    
    def get_nome_exibicao(self, obj):
        if obj.first_name:
            return obj.first_name
        elif obj.username:
            return obj.username
        else:
            return obj.email.split('@')[0]

class MensagemVisualizacaoSerializer(serializers.ModelSerializer):
    usuario = UserSerializer(read_only=True)

    class Meta:
        model = MensagemVisualizacao
        fields = ['usuario', 'data_visualizacao']

class MensagemSerializer(serializers.ModelSerializer):
    remetente = UserSerializer(read_only=True)
    respondendo_a = serializers.SerializerMethodField()
    visualizacoes = MensagemVisualizacaoSerializer(many=True, read_only=True)
    arquivo_url = serializers.SerializerMethodField()
    nome_remetente = serializers.SerializerMethodField()

    class Meta:
        model = Mensagem
        fields = [
            'id', 'chat', 'remetente', 'nome_remetente', 'conteudo', 'tipo', 'arquivo', 
            'arquivo_url', 'duracao_audio', 'latitude', 'longitude',
            'data_envio', 'data_edicao', 'lida', 'respondendo_a',
            'visualizacoes', 'excluida'
        ]
        read_only_fields = ['id', 'data_envio', 'remetente']

    def get_arquivo_url(self, obj):
        if obj.arquivo:
            return obj.arquivo.url
        return None

    def get_respondendo_a(self, obj):
        if obj.respondendo_a:
            return MensagemSerializer(obj.respondendo_a).data
        return None
    
    def get_nome_remetente(self, obj):
        if obj.remetente.first_name:
            return obj.remetente.first_name
        elif obj.remetente.username:
            return obj.remetente.username
        else:
            return obj.remetente.email.split('@')[0]

class ChatSerializer(serializers.ModelSerializer):
    participantes = UserSerializer(many=True, read_only=True)
    ultima_mensagem = MensagemSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    outro_usuario = serializers.SerializerMethodField()
    nome_conversa = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = [
            'id', 'participantes', 'outro_usuario', 'nome_conversa', 'data_criacao', 
            'ultima_mensagem', 'unread_count', 'is_group', 'nome_grupo', 'foto_grupo'
        ]

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.mensagens_chat.filter(lida=False).exclude(remetente=user).count()
    
    def get_outro_usuario(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            outros_usuarios = obj.participantes.exclude(id=request.user.id)
            if outros_usuarios.exists():
                outro_usuario = outros_usuarios.first()
                return UserSerializer(outro_usuario).data
        return None
    
    def get_nome_conversa(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if obj.is_group and obj.nome_grupo:
                return obj.nome_grupo
            else:
                outros_usuarios = obj.participantes.exclude(id=request.user.id)
                if outros_usuarios.exists():
                    outro_usuario = outros_usuarios.first()
                    serializer = UserSerializer(outro_usuario)
                    return serializer.data.get('nome_exibicao', 'Usuário')
        return 'Conversa'

class CriarMensagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mensagem
        fields = [
            'chat', 'conteudo', 'tipo', 'arquivo', 'duracao_audio',
            'latitude', 'longitude', 'respondendo_a'
        ]

class CriarChatSerializer(serializers.ModelSerializer):
    participantes_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )

    class Meta:
        model = Chat
        fields = ['participantes_ids', 'is_group', 'nome_grupo', 'foto_grupo']