from django.db import models
from rest_framework import serializers
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from django.core.validators import validate_image_file_extension

from .models import Categoria, Servico, Anuncio, Imagem, Avaliacao
from core.models import CustomUser, Localizacao

class ImagemSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    tipo_item = serializers.SerializerMethodField()
    
    class Meta:
        model = Imagem
        fields = [
            'id', 'imagem', 'url', 'ordem', 'capa', 
            'data_upload', 'tipo_item'
        ]
        read_only_fields = ['data_upload', 'url']
    
    def get_url(self, obj):
        request = self.context.get('request')
        if obj.imagem and request:
            return request.build_absolute_uri(obj.imagem.url)
        return None
    
    def get_tipo_item(self, obj):
        return 'servico' if obj.servico else 'anuncio'
    
    def validate(self, data):
        if 'servico' in self.initial_data and 'anuncio' in self.initial_data:
            raise ValidationError(_("A imagem deve estar vinculada apenas a um serviço ou anúncio."))
        return data

class CategoriaSerializer(serializers.ModelSerializer):
    total_servicos = serializers.IntegerField(
        read_only=True,
        source='servicos.count'
    )
    total_anuncios = serializers.IntegerField(
        read_only=True,
        source='anuncios.count'
    )
    
    class Meta:
        model = Categoria
        fields = [
            'id', 'titulo', 'slug', 'imagem',
            'destaque', 'ordem_menu', 'total_servicos',
            'total_anuncios', 'ativa'
        ]
        
class ItemBaseSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField(read_only=True)
    categoria = CategoriaSerializer(read_only=True)
    categoria_id = serializers.PrimaryKeyRelatedField(
        queryset=Categoria.objects.filter(ativa=True),
        write_only=True,
        source='categoria'
    )
    localizacao = serializers.StringRelatedField(read_only=True)
    localizacao_id = serializers.PrimaryKeyRelatedField(
        queryset=Localizacao.objects.all(),
        write_only=True,
        source='localizacao',
        required=False,
        allow_null=True
    )
    whatsapp_url = serializers.SerializerMethodField()
    is_meu_item = serializers.SerializerMethodField()
    imagens = ImagemSerializer(many=True, read_only=True)
    
    class Meta:
        fields = [
            'id', 'titulo', 'descricao', 'valor', 'status',
            'categoria', 'categoria_id', 'usuario', 'localizacao',
            'localizacao_id', 'data_criacao', 'data_atualizacao',
            'visualizacoes', 'whatsapp', 'whatsapp_url', 'is_meu_item',
            'imagens'
        ]
        read_only_fields = [
            'id', 'usuario', 'data_criacao', 'data_atualizacao',
            'visualizacoes', 'is_meu_item'
        ]
    
    def get_whatsapp_url(self, obj):
        return obj.get_whatsapp_url()
    
    def get_is_meu_item(self, obj):
        request = self.context.get('request')
        return request and request.user.is_authenticated and obj.usuario == request.user

class ServicoSerializer(ItemBaseSerializer):
    avaliacoes = serializers.SerializerMethodField()
    media_avaliacoes = serializers.SerializerMethodField()
    
    class Meta(ItemBaseSerializer.Meta):
        model = Servico
        fields = ItemBaseSerializer.Meta.fields + [
            'tipo', 'destaque', 'disponivel_24h', 'tempo_entrega',
            'avaliacoes', 'media_avaliacoes'
        ]
    
    def get_avaliacoes(self, obj):
        return AvaliacaoSerializer(
            obj.avaliacoes.all()[:5],
            many=True,
            context=self.context
        ).data
    
    def get_media_avaliacoes(self, obj):
        media = obj.avaliacoes.aggregate(media=models.Avg('nota'))['media']
        return media if media else 0.0

class ServicoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servico
        fields = [
            'titulo', 'descricao', 'valor', 'categoria',
            'localizacao', 'whatsapp', 'tipo', 'tempo_entrega'
        ]
        extra_kwargs = {
            'whatsapp': {'required': False}
        }
    
    def validate_valor(self, value):
        if value <= 0:
            raise serializers.ValidationError(_("O valor deve ser maior que zero."))
        return value
    
    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        return super().create(validated_data)

class AnuncioSerializer(ItemBaseSerializer):
    avaliacoes = serializers.SerializerMethodField()
    media_avaliacoes = serializers.SerializerMethodField()
    
    class Meta(ItemBaseSerializer.Meta):
        model = Anuncio
        fields = ItemBaseSerializer.Meta.fields + [
            'estado_produto', 'quantidade', 'marca', 'garantia',
            'avaliacoes', 'media_avaliacoes'
        ]
    
    def get_avaliacoes(self, obj):
        return AvaliacaoSerializer(
            obj.avaliacoes.all()[:5],
            many=True,
            context=self.context
        ).data
    
    def get_media_avaliacoes(self, obj):
        media = obj.avaliacoes.aggregate(media=models.Avg('nota'))['media']
        return media if media else 0.0

class AnuncioCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anuncio
        fields = [
            'titulo', 'descricao', 'valor', 'categoria',
            'localizacao', 'whatsapp', 'estado_produto',
            'quantidade', 'marca', 'garantia'
        ]
        extra_kwargs = {
            'quantidade': {'min_value': 1},
            'garantia': {'min_value': 0}
        }
    
    def validate(self, data):
        if data.get('estado_produto') == 'novo' and data.get('quantidade', 0) <= 0:
            raise serializers.ValidationError({
                'quantidade': _("Para produtos novos, a quantidade deve ser maior que zero.")
            })
        return data
    
    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        return super().create(validated_data)

class AvaliacaoSerializer(serializers.ModelSerializer):
    usuario_avaliador = serializers.StringRelatedField(read_only=True)
    pode_responder = serializers.SerializerMethodField()
    resposta = serializers.SerializerMethodField()
    
    class Meta:
        model = Avaliacao
        fields = [
            'id', 'usuario_avaliador', 'nota', 'comentario',
            'data_criacao', 'resposta', 'data_resposta', 'pode_responder'
        ]
        read_only_fields = [
            'id', 'usuario_avaliador', 'data_criacao',
            'data_resposta', 'pode_responder'
        ]
    
    def get_pode_responder(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        item = obj.servico if obj.servico else obj.anuncio
        return item.usuario == request.user and not obj.resposta
    
    def get_resposta(self, obj):
        if obj.resposta:
            return {
                'texto': obj.resposta,
                'data': obj.data_resposta,
                'pode_editar': self._pode_editar_resposta(obj)
            }
        return None
    
    def _pode_editar_resposta(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        from django.utils.timezone import now
        item = obj.servico if obj.servico else obj.anuncio
        return (item.usuario == request.user and 
                (now() - obj.data_resposta).total_seconds() < 86400)

class AvaliacaoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avaliacao
        fields = ['nota', 'comentario']
        extra_kwargs = {
            'comentario': {'required': False}
        }
    
    def validate(self, data):
        request = self.context.get('request')
        servico_id = self.context.get('servico_id')
        anuncio_id = self.context.get('anuncio_id')
        
        if not servico_id and not anuncio_id:
            raise ValidationError(_("Deve especificar um serviço ou anúncio."))
        
        if servico_id:
            if Avaliacao.objects.filter(servico_id=servico_id, usuario_avaliador=request.user).exists():
                raise ValidationError(_("Você já avaliou este serviço."))
        else:
            if Avaliacao.objects.filter(anuncio_id=anuncio_id, usuario_avaliador=request.user).exists():
                raise ValidationError(_("Você já avaliou este anúncio."))
        
        return data
    
    def create(self, validated_data):
        servico_id = self.context.get('servico_id')
        anuncio_id = self.context.get('anuncio_id')
        
        avaliacao = Avaliacao(
            usuario_avaliador=self.context['request'].user,
            **validated_data
        )
        
        if servico_id:
            avaliacao.servico_id = servico_id
        else:
            avaliacao.anuncio_id = anuncio_id
        
        avaliacao.save()
        return avaliacao

class RespostaAvaliacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avaliacao
        fields = ['resposta']
    
    def update(self, instance, validated_data):
        from django.utils.timezone import now
        
        instance.resposta = validated_data.get('resposta', instance.resposta)
        instance.data_resposta = now()
        instance.save()
        return instance

class AnuncioDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalhes do anúncio - CORRIGIDO O NOME DO USUÁRIO"""
    categoria = CategoriaSerializer(read_only=True)
    usuario = serializers.SerializerMethodField()
    localizacao = serializers.SerializerMethodField()
    imagens = ImagemSerializer(many=True, read_only=True)
    whatsapp_url = serializers.SerializerMethodField()
    usuario_nome = serializers.SerializerMethodField()
    usuario_foto = serializers.SerializerMethodField()
    localizacao_str = serializers.SerializerMethodField()
    imagem_principal = serializers.SerializerMethodField()
    
    class Meta:
        model = Anuncio
        fields = [
            'id', 'titulo', 'descricao', 'valor', 'status',
            'categoria', 'usuario', 'localizacao', 'data_criacao',
            'data_atualizacao', 'visualizacoes', 'whatsapp', 
            'whatsapp_url', 'imagens', 'estado_produto', 'quantidade',
            'marca', 'garantia', 'usuario_nome', 'usuario_foto',
            'localizacao_str', 'imagem_principal', 'destaque'
        ]
    
    def get_whatsapp_url(self, obj):
        return obj.get_whatsapp_url()
    
    def get_usuario(self, obj):
        """Retorna objeto usuário completo"""
        if obj.usuario:
            return {
                'id': obj.usuario.id,
                'nome': self._get_usuario_nome_seguro(obj.usuario),  # ✅ 
                'foto_perfil': self.get_usuario_foto_url(obj.usuario)
            }
        return None
    
    def get_usuario_nome(self, obj):
        """Nome do usuário para compatibilidade - CORRIGIDO"""
        if obj.usuario:
            return self._get_usuario_nome_seguro(obj.usuario)
        return "Anunciante"
    
    def _get_usuario_nome_seguro(self, usuario):
        """Método auxiliar para obter nome do usuário de forma segura"""
        if usuario.nome and usuario.nome.strip():
            return usuario.nome.strip()
        elif usuario.email:
            return usuario.email.split('@')[0]
        return "Anunciante"
    
    def get_usuario_foto(self, obj):
        """Foto do usuário para compatibilidade"""
        return self.get_usuario_foto_url(obj.usuario) if obj.usuario else None
    
    def get_usuario_foto_url(self, usuario):
        """URL da foto do usuário"""
        request = self.context.get('request')
        if usuario and usuario.foto_perfil and request:
            try:
                return request.build_absolute_uri(usuario.foto_perfil.url)
            except:
                return None
        return None
    
    def get_localizacao(self, obj):
        """Retorna objeto localização completo"""
        if obj.localizacao:
            return {
                'id': obj.localizacao.id,
                'nome': str(obj.localizacao),
                'cidade': getattr(obj.localizacao, 'cidade', None),
                'estado': getattr(obj.localizacao, 'estado', None)
            }
        return None
    
    def get_localizacao_str(self, obj):
        """String da localização para compatibilidade"""
        if obj.localizacao:
            if hasattr(obj.localizacao, 'cidade') and hasattr(obj.localizacao, 'estado'):
                cidade = obj.localizacao.cidade or ''
                estado = obj.localizacao.estado or ''
                if cidade and estado:
                    return f"{cidade}, {estado}"
                elif cidade:
                    return cidade
                elif estado:
                    return estado
            return str(obj.localizacao)
        return "Localização não informada"
    
    def get_imagem_principal(self, obj):
        """Imagem principal do anúncio"""
        request = self.context.get('request')
        if obj.imagens.exists():
            imagem = obj.imagens.filter(capa=True).first() or obj.imagens.first()
            if imagem.imagem:
                try:
                    return request.build_absolute_uri(imagem.imagem.url)
                except:
                    return None
        return None

class CategoriaMobileSerializer(serializers.ModelSerializer):
    """Serializer simplificado para o app mobile - CORRIGIDO"""
    total_anuncios = serializers.IntegerField(read_only=True)
    imagem = serializers.SerializerMethodField()  
    
    class Meta:
        model = Categoria
        fields = [
            'id', 'titulo', 'slug', 'imagem', 'imagem_url'
            'destaque', 'ordem_menu', 'total_anuncios', 'ativa'
        ]
    
    def get_imagem(self, obj):  
        request = self.context.get('request')
        if obj.imagem and request:
            return request.build_absolute_uri(obj.imagem.url)
        return None
    
class AnuncioMobileSerializer(serializers.ModelSerializer):
    """Serializer para anúncios mobile - CORRIGIDO O NOME DO USUÁRIO"""
    categoria_nome = serializers.CharField(source='categoria.titulo', read_only=True)
    usuario_nome = serializers.SerializerMethodField()
    usuario_foto = serializers.SerializerMethodField()
    imagem_principal = serializers.SerializerMethodField()
    localizacao_str = serializers.SerializerMethodField()
    favoritado = serializers.SerializerMethodField()
    
    class Meta:
        model = Anuncio
        fields = [
            'id', 'titulo', 'descricao', 'valor', 'status',
            'categoria', 'categoria_nome', 'usuario_nome', 'usuario_foto',
            'localizacao_str', 'data_criacao', 'visualizacoes',
            'whatsapp', 'imagem_principal', 'estado_produto',
            'quantidade', 'marca', 'garantia', 'destaque', 'favoritado'
        ]
    
    def get_usuario_nome(self, obj):
        """Obtém o nome do usuário de forma segura - CORRIGIDO"""
        if obj.usuario:
            if obj.usuario.nome and obj.usuario.nome.strip():
                return obj.usuario.nome.strip()
            elif obj.usuario.email:
                return obj.usuario.email.split('@')[0]
        return "Anunciante"
    
    def get_usuario_foto(self, obj):
        """Obtém a foto de perfil do usuário"""
        request = self.context.get('request')
        if obj.usuario and obj.usuario.foto_perfil:
            try:
                return request.build_absolute_uri(obj.usuario.foto_perfil.url)
            except:
                return None
        return None
    
    def get_imagem_principal(self, obj):
        """Obtém a imagem principal ou a primeira imagem"""
        request = self.context.get('request')
        if obj.imagens.exists():
            imagem = obj.imagens.filter(capa=True).first() or obj.imagens.first()
            if imagem and imagem.imagem:
                try:
                    return request.build_absolute_uri(imagem.imagem.url)
                except:
                    return None
        return None
    
    def get_localizacao_str(self, obj):
        """Obtém a localização em formato string"""
        if obj.localizacao:
            if hasattr(obj.localizacao, 'cidade') and hasattr(obj.localizacao, 'estado'):
                cidade = obj.localizacao.cidade or ''
                estado = obj.localizacao.estado or ''
                if cidade and estado:
                    return f"{cidade}, {estado}"
                elif cidade:
                    return cidade
                elif estado:
                    return estado
            elif hasattr(obj.localizacao, 'nome') and obj.localizacao.nome:
                return obj.localizacao.nome
        return "Local não informado"
    
    def get_favoritado(self, obj):
        """Verifica se o anúncio está favoritado pelo usuário atual"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from django.contrib.contenttypes.models import ContentType
            from core.models import Favorito
            
            try:
                anuncio_content_type = ContentType.objects.get_for_model(Anuncio)
                return Favorito.objects.filter(
                    usuario=request.user,
                    content_type=anuncio_content_type,
                    object_id=obj.id
                ).exists()
            except:
                return False
        return False