from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.utils import timezone
from django.utils.timesince import timesince
from django.db.models import Avg  
from produtos.models import Anuncio
from django.contrib.contenttypes.models import ContentType

from produtos.models import Servico, Categoria, Imagem, Avaliacao  
from .models import CustomUser, Notificacao, Favorito, HistoricoBusca, Mensagem

class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer para exibir informações de um usuário."""
    localizacao = serializers.StringRelatedField()
    reputacao = serializers.DecimalField(max_digits=2, decimal_places=1, coerce_to_string=False)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'nome', 'nome_utilizador', 'email', 
            'foto_perfil', 'telefone', 'localizacao',
            'premium', 'reputacao', 'data_nascimento',
            'email_verificado', 'creditos'
        ]
        read_only_fields = ['email', 'email_verificado', 'reputacao', 'creditos']
        extra_kwargs = {
            'data_nascimento': {'format': '%d/%m/%Y'},
        }

class UsuarioRegistroSerializer(serializers.ModelSerializer):
    """Serializer para registro de novos usuários - VERSÃO CORRIGIDA"""
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'},
        min_length=6
    )
    password2 = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )
    first_name = serializers.CharField(required=True, max_length=30)
    telefone = serializers.CharField(required=True, max_length=20)
    termos_aceitos = serializers.BooleanField(required=True, write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'email', 'telefone', 'password', 'password2', 'termos_aceitos'
        ]
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate(self, attrs):
        print("🔍 [SERIALIZER] Validando dados...")
        
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "As senhas não coincidem."})
        
        if not attrs.get('termos_aceitos'):
            raise serializers.ValidationError({"termos_aceitos": "Você deve aceitar os termos de uso."})
        
        if CustomUser.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Este email já está cadastrado."})
        
        print("✅ [SERIALIZER] Validações passaram")
        return attrs

    def create(self, validated_data):
        print("👤 [SERIALIZER] Criando usuário...")
        
        password = validated_data.pop('password')
        validated_data.pop('password2')
        validated_data.pop('termos_aceitos')
        
        email = validated_data['email']
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        validated_data['username'] = username
        
        print(f"🔧 [SERIALIZER] Criando usuário: {validated_data['email']}")
        
        user = CustomUser.objects.create_user(
            **validated_data,
            password=password  
        )
        
        print(f"✅ [SERIALIZER] Usuário criado: {user.email}")
        return user

class UsuarioLoginSerializer(serializers.Serializer):
    """Serializer para autenticação de usuário - VERSÃO CORRIGIDA"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
        required=True
    )

    def validate(self, attrs):
        print("🔐 [LOGIN-SERIALIZER] Validando login...")
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError(
                "Deve incluir 'email' e 'password'", 
                code='authorization'
            )

        try:
            user = CustomUser.objects.get(email=email)
            print(f"👤 [LOGIN-SERIALIZER] Usuário encontrado: {user.email}")
            
            if not user.check_password(password):
                print("❌ [LOGIN-SERIALIZER] Senha incorreta")
                raise serializers.ValidationError(
                    "Credenciais inválidas", 
                    code='authorization'
                )
                
            if not user.is_active:
                raise serializers.ValidationError(
                    "Conta desativada", 
                    code='authorization'
                )
                
        except CustomUser.DoesNotExist:
            print("❌ [LOGIN-SERIALIZER] Usuário não encontrado")
            raise serializers.ValidationError(
                "Credenciais inválidas", 
                code='authorization'
            )

        attrs['user'] = user
        print("✅ [LOGIN-SERIALIZER] Login validado com sucesso")
        return attrs

class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """Serializer para atualização parcial de dados do usuário."""
    class Meta:
        model = CustomUser
        fields = [
            'nome', 'nome_utilizador', 'telefone',
            'data_nascimento', 'localizacao'
        ]

class FotoPerfilSerializer(serializers.ModelSerializer):
    """Serializer para upload de foto de perfil."""
    class Meta:
        model = CustomUser
        fields = ['foto_perfil']
        extra_kwargs = {
            'foto_perfil': {'required': True}
        }

class ServicoSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Servico."""
    categoria_nome = serializers.CharField(source='categoria.titulo', read_only=True)
    usuario_nome = serializers.CharField(source='usuario.nome', read_only=True)
    localizacao_nome = serializers.SerializerMethodField()
    imagem_capa = serializers.SerializerMethodField()
    whatsapp_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Servico
        fields = [
            'id', 'titulo', 'descricao', 'valor', 'categoria', 'categoria_nome',
            'usuario', 'usuario_nome', 'localizacao', 'localizacao_nome',
            'data_criacao', 'visualizacoes', 'status', 'imagem_capa', 'whatsapp_url'
        ]
        read_only_fields = ['id', 'usuario', 'data_criacao', 'visualizacoes']
    
    def get_localizacao_nome(self, obj):
        if obj.localizacao:
            return f"{obj.localizacao.cidade}, {obj.localizacao.estado}"
        return None
    
    def get_imagem_capa(self, obj):
        if obj.imagens.filter(capa=True).exists():
            return obj.imagens.filter(capa=True).first().imagem.url
        return None
    
    def get_whatsapp_url(self, obj):
        return obj.get_whatsapp_url()

class CategoriaSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Categoria."""
    class Meta:
        model = Categoria
        fields = ['id', 'titulo', 'slug', 'imagem', 'destaque', 'ordem_menu']
        read_only_fields = ['id', 'slug']

class NotificacaoSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Notificacao."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    tempo_decorrido = serializers.SerializerMethodField()
    icone = serializers.CharField(read_only=True)

    class Meta:
        model = Notificacao
        fields = [
            'id', 'titulo', 'mensagem', 'tipo', 'tipo_display',
            'lida', 'data_criacao', 'url', 'icone', 'tempo_decorrido'
        ]
        read_only_fields = fields

    def get_tempo_decorrido(self, obj):
        return timesince(obj.data_criacao)

class FavoritoSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Favorito."""
    servico_titulo = serializers.CharField(source='servico.titulo', read_only=True)
    servico_valor = serializers.DecimalField(
        source='servico.valor',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    servico_imagem = serializers.SerializerMethodField()

    class Meta:
        model = Favorito
        fields = [
            'id', 'servico', 'servico_titulo',
            'servico_valor', 'servico_imagem', 'data_criacao'
        ]
        read_only_fields = fields

    def get_servico_imagem(self, obj):
        if obj.servico.imagens.exists():
            return obj.servico.imagens.first().imagem.url
        return None

class HistoricoBuscaSerializer(serializers.ModelSerializer):
    """Serializer para o modelo HistoricoBusca."""
    categoria_nome = serializers.CharField(source='categoria.titulo', read_only=True)
    localizacao_nome = serializers.CharField(source='localizacao.nome', read_only=True)

    class Meta:
        model = HistoricoBusca
        fields = [
            'id', 'termo', 'categoria', 'categoria_nome',
            'localizacao', 'localizacao_nome', 'data_busca'
        ]
        read_only_fields = fields

class MensagemSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Mensagem."""
    remetente_nome = serializers.CharField(source='remetente.nome', read_only=True)
    destinatario_nome = serializers.CharField(source='destinatario.nome', read_only=True)
    tempo_decorrido = serializers.SerializerMethodField()

    class Meta:
        model = Mensagem
        fields = [
            'id', 'remetente', 'remetente_nome', 'destinatario',
            'destinatario_nome', 'mensagem', 'data_envio', 'lida', 'conversa_id',
            'tempo_decorrido'
        ]
        read_only_fields = ['id', 'remetente', 'remetente_nome', 'data_envio', 'lida', 'conversa_id', 'tempo_decorrido']

    def get_tempo_decorrido(self, obj):
        return timesince(obj.data_envio)
    
class ServicoDetailSerializer(serializers.ModelSerializer):
    """Serializer detalhado para o modelo Servico, incluindo todas as informações e imagens."""
    categoria_nome = serializers.CharField(source='categoria.titulo', read_only=True)
    usuario_info = serializers.SerializerMethodField()
    localizacao_info = serializers.SerializerMethodField()
    imagens = serializers.SerializerMethodField()
    whatsapp_url = serializers.SerializerMethodField()
    favoritado = serializers.SerializerMethodField()
    servicos_relacionados = serializers.SerializerMethodField()
    avaliacoes = serializers.SerializerMethodField()
    media_avaliacoes = serializers.SerializerMethodField()

    class Meta:
        model = Servico
        fields = [
            'id', 'titulo', 'descricao', 'valor', 'categoria', 'categoria_nome',
            'usuario', 'usuario_info', 'localizacao', 'localizacao_info',
            'data_criacao', 'data_atualizacao', 'visualizacoes', 'status',
            'whatsapp', 'whatsapp_url', 'imagens', 'favoritado',
            'servicos_relacionados', 'avaliacoes', 'media_avaliacoes',
            'tipo', 'destaque', 'disponivel_24h', 'tempo_entrega'
        ]
        read_only_fields = fields

    def get_usuario_info(self, obj):
        return {
            'id': obj.usuario.id,
            'nome': obj.usuario.nome,
            'foto_perfil': obj.usuario.foto_perfil.url if obj.usuario.foto_perfil else None,
            'reputacao': obj.usuario.reputacao
        }

    def get_localizacao_info(self, obj):
        if obj.localizacao:
            return {
                'id': obj.localizacao.id,
                'nome': obj.localizacao.nome,
                'cidade': obj.localizacao.cidade,
                'estado': obj.localizacao.estado
            }
        return None

    def get_imagens(self, obj):
        return [{
            'id': img.id,
            'imagem': img.imagem.url,
            'capa': img.capa,
            'ordem': img.ordem
        } for img in obj.imagens.all().order_by('ordem')]

    def get_whatsapp_url(self, obj):
        return obj.get_whatsapp_url()

    def get_favoritado(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favoritos.filter(usuario=request.user).exists()
        return False

    def get_servicos_relacionados(self, obj):
        relacionados = Servico.objects.filter(
            categoria=obj.categoria,
            status='ativo'
        ).exclude(pk=obj.pk).select_related('usuario')[:4]
        
        return ServicoSerializer(relacionados, many=True, context=self.context).data

    def get_avaliacoes(self, obj):
        avaliacoes = obj.avaliacoes.filter(aprovada=True).order_by('-data_criacao')[:5]
        return AvaliacaoSerializer(avaliacoes, many=True).data

    def get_media_avaliacoes(self, obj):
        return obj.avaliacoes.aggregate(media=Avg('nota'))['media']

class AvaliacaoSerializer(serializers.ModelSerializer):
    """Serializer para avaliações de serviços."""
    usuario_nome = serializers.CharField(source='usuario_avaliador.nome', read_only=True)
    usuario_foto = serializers.SerializerMethodField()
    tempo_decorrido = serializers.SerializerMethodField()

    class Meta:
        model = Avaliacao
        fields = [
            'id', 'usuario_avaliador', 'usuario_nome', 'usuario_foto',
            'nota', 'comentario', 'data_criacao', 'resposta',
            'data_resposta', 'tempo_decorrido'
        ]
        read_only_fields = fields

    def get_usuario_foto(self, obj):
        if obj.usuario_avaliador.foto_perfil:
            return obj.usuario_avaliador.foto_perfil.url
        return None

    def get_tempo_decorrido(self, obj):
        return timesince(obj.data_criacao)

class AnuncioSerializer(serializers.ModelSerializer):
    """Serializer para o modelo Anuncio"""
    categoria_nome = serializers.CharField(source='categoria.titulo', read_only=True)
    usuario_nome = serializers.CharField(source='usuario.get_full_name', read_only=True)
    usuario_foto = serializers.SerializerMethodField()
    localizacao_str = serializers.SerializerMethodField()
    imagem_principal = serializers.SerializerMethodField()
    whatsapp_url = serializers.SerializerMethodField()
    favoritado = serializers.SerializerMethodField()
    valor_formatado = serializers.SerializerMethodField()
    
    class Meta:
        model = Anuncio
        fields = [
            'id', 'titulo', 'descricao', 'valor', 'valor_formatado', 'categoria', 'categoria_nome',
            'usuario', 'usuario_nome', 'usuario_foto', 'localizacao', 'localizacao_str',
            'data_criacao', 'visualizacoes', 'status', 'imagem_principal', 'whatsapp_url',
            'favoritado', 'whatsapp', 'estado_produto', 'destaque'
        ]
        read_only_fields = ['id', 'usuario', 'data_criacao', 'visualizacoes']
    
    def get_usuario_foto(self, obj):
        if obj.usuario.foto_perfil:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.usuario.foto_perfil.url)
        return None
    
    def get_localizacao_str(self, obj):
        if obj.localizacao:
            return f"{obj.localizacao.cidade}, {obj.localizacao.estado}"
        return "Localização não informada"
    
    def get_imagem_principal(self, obj):
        if obj.imagens.exists():
            imagem_capa = obj.imagens.filter(capa=True).first()
            if imagem_capa:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(imagem_capa.imagem.url)
            primeira_imagem = obj.imagens.first()
            if primeira_imagem:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(primeira_imagem.imagem.url)
        return None
    
    def get_whatsapp_url(self, obj):
        return obj.get_whatsapp_url()
    
    def get_favoritado(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            anuncio_content_type = ContentType.objects.get_for_model(Anuncio)
            return Favorito.objects.filter(
                usuario=request.user,
                content_type=anuncio_content_type,
                object_id=obj.id
            ).exists()
        return False
    
    def get_valor_formatado(self, obj):
        if obj.valor:
            return f"R$ {obj.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return "A combinar"
    
class UsuarioMobileRegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True)
    termos_aceitos = serializers.BooleanField(required=True)

    class Meta:
        model = CustomUser
        fields = ['nome', 'email', 'telefone', 'password', 'password2', 'termos_aceitos']
        extra_kwargs = {
            'nome': {'required': True},
            'email': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "As senhas não coincidem."})
        
        if not attrs.get('termos_aceitos'):
            raise serializers.ValidationError({"termos_aceitos": "Você deve aceitar os termos de uso."})
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        validated_data.pop('termos_aceitos')
    
        if 'nome_utilizador' not in validated_data:
            base_name = validated_data['nome'].split()[0].lower()
            final_name = base_name
            counter = 1
            
            while CustomUser.objects.filter(nome_utilizador=final_name).exists():
                final_name = f"{base_name}{counter}"
                counter += 1
                
            validated_data['nome_utilizador'] = final_name
        
        user = CustomUser.objects.create_user(**validated_data)
        return user