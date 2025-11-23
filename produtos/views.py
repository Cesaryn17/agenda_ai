from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
import logging

from rest_framework import generics
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from django.http import Http404
from django.shortcuts import get_object_or_404
from .models import Anuncio
from .serializers import AnuncioDetailSerializer
from core.models import Favorito
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from .models import Categoria, Servico, Anuncio, Imagem, Avaliacao
from .serializers import (
    CategoriaSerializer,
    ServicoSerializer,
    ServicoCreateSerializer,
    AnuncioSerializer,
    AnuncioCreateSerializer,
    CategoriaMobileSerializer,
    ImagemSerializer,
    AvaliacaoCreateSerializer,
    RespostaAvaliacaoSerializer,
    AnuncioMobileSerializer,
)

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.usuario == request.user

class IsItemOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        item_id = view.kwargs.get('anuncio_id')
        item = get_object_or_404(Anuncio, pk=item_id)
        return item.usuario == request.user
    
class CategoriaListView(generics.ListAPIView):
    serializer_class = CategoriaSerializer
    queryset = Categoria.objects.filter(ativa=True).annotate(
        total_servicos=Count('servicos'),
        total_anuncios=Count('anuncios')
    ).order_by('ordem_menu')

class AnuncioListCreateView(generics.ListCreateAPIView):
    serializer_class = AnuncioSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categoria', 'estado_produto', 'localizacao']
    search_fields = ['titulo', 'descricao', 'marca']
    ordering_fields = ['valor', 'data_criacao', 'visualizacoes']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AnuncioCreateSerializer
        return AnuncioSerializer

    def get_queryset(self):
        return Anuncio.objects.filter(
            Q(status='ativo') | Q(status='pendente')
        ).select_related(
            'usuario', 'categoria', 'localizacao'
        ).prefetch_related('imagens').order_by('-data_criacao')

class AnuncioDetailView(generics.RetrieveAPIView):
    """View para detalhes do anúncio - VERSÃO DEFINITIVAMENTE CORRIGIDA"""
    queryset = Anuncio.objects.select_related('usuario', 'categoria', 'localizacao')\
                             .prefetch_related('imagens')
    serializer_class = AnuncioDetailSerializer
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    
    def get_object(self):
        try:
            anuncio = super().get_object()
            anuncio.visualizacoes += 1
            anuncio.save(update_fields=['visualizacoes'])
            return anuncio
        except Anuncio.DoesNotExist:
            raise Http404("Anúncio não encontrado")
    
    def get(self, request, *args, **kwargs):
        anuncio = self.get_object()
        
        if request.accepted_renderer.format == 'html':
            return self.render_html_response(request, anuncio)
        else:
            return self.render_json_response(request, anuncio)
    
    def render_html_response(self, request, anuncio):
        """Renderizar template HTML para o navegador"""
        favoritado = False
        if request.user.is_authenticated:
            content_type = ContentType.objects.get_for_model(Anuncio)
            favoritado = Favorito.objects.filter(
                usuario=request.user,
                content_type=content_type,
                object_id=anuncio.id
            ).exists()
        
        anuncios_relacionados = Anuncio.objects.filter(
            categoria=anuncio.categoria,
            status='ativo'
        ).exclude(pk=anuncio.id)[:4]
        
        context = {
            'anuncio': anuncio,
            'favoritado': favoritado,
            'anuncios_relacionados': anuncios_relacionados,
            'whatsapp_url': anuncio.get_whatsapp_url(),
        }
        
        return Response(context, template_name='detalhe.html')
    
    def render_json_response(self, request, anuncio):
        """Renderizar JSON para a API (app mobile)"""
        serializer = self.get_serializer(anuncio)
        data = serializer.data
        
        favoritado = False
        if request.user.is_authenticated:
            content_type = ContentType.objects.get_for_model(Anuncio)
            favoritado = Favorito.objects.filter(
                usuario=request.user,
                content_type=content_type,
                object_id=anuncio.id
            ).exists()
        
        data['favoritado'] = favoritado
        data['whatsapp_url'] = anuncio.get_whatsapp_url()
        
        data['usuario_nome'] = anuncio.usuario.nome if anuncio.usuario else 'Usuário'
        data['usuario_foto'] = request.build_absolute_uri(anuncio.usuario.foto_perfil.url) if anuncio.usuario and anuncio.usuario.foto_perfil else None
        data['categoria_nome'] = anuncio.categoria.titulo if anuncio.categoria else 'Categoria'
        data['localizacao_str'] = str(anuncio.localizacao) if anuncio.localizacao else 'Local não informado'
        data['imagem_principal'] = self.get_imagem_principal(anuncio, request)

        anuncios_relacionados = Anuncio.objects.filter(
            categoria=anuncio.categoria,
            status='ativo'
        ).exclude(pk=anuncio.id)[:4]
        
        relacionados_serializer = AnuncioMobileSerializer(
            anuncios_relacionados, 
            many=True, 
            context={'request': request}
        )
        data['anuncios_relacionados'] = relacionados_serializer.data
        
        return Response(data)
    
    def get_imagem_principal(self, anuncio, request):
        """Obter URL da imagem principal"""
        if anuncio.imagens.exists():
            imagem = anuncio.imagens.filter(capa=True).first() or anuncio.imagens.first()
            if imagem.imagem:
                return request.build_absolute_uri(imagem.imagem.url)
        return None
    
    def retrieve(self, request, *args, **kwargs):
        """Método padrão do RetrieveAPIView - usar nossa lógica personalizada"""
        return self.get(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.status = 'desativado'
        instance.save()

class MeusAnunciosListView(generics.ListAPIView):
    serializer_class = AnuncioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Anuncio.objects.filter(
            usuario=self.request.user
        ).order_by('-data_criacao')

class ServicoListCreateView(generics.ListCreateAPIView):
    serializer_class = ServicoSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['categoria', 'tipo', 'destaque']
    search_fields = ['titulo', 'descricao']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServicoCreateSerializer
        return ServicoSerializer

    def get_queryset(self):
        return Servico.objects.filter(status='ativo').select_related(
            'usuario', 'categoria', 'localizacao'
        ).order_by('-data_criacao')

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

class ImagemAnuncioCreateView(generics.CreateAPIView):
    serializer_class = ImagemSerializer
    permission_classes = [permissions.IsAuthenticated, IsItemOwner]

    def perform_create(self, serializer):
        anuncio = get_object_or_404(Anuncio, pk=self.kwargs['anuncio_id'])
        serializer.save(anuncio=anuncio)

class AvaliacaoCreateView(generics.CreateAPIView):
    serializer_class = AvaliacaoCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        anuncio = get_object_or_404(Anuncio, pk=self.kwargs['anuncio_id'])
        serializer.save(
            usuario_avaliador=self.request.user,
            anuncio=anuncio
        )

class RespostaAvaliacaoView(generics.UpdateAPIView):
    queryset = Avaliacao.objects.all()
    serializer_class = RespostaAvaliacaoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        avaliacao = super().get_object()
        item = avaliacao.servico if avaliacao.servico else avaliacao.anuncio
        if item.usuario != self.request.user:
            self.permission_denied(self.request)
        return avaliacao

class AnunciosPorCategoriaView(generics.ListAPIView):
    serializer_class = AnuncioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['estado_produto', 'localizacao']

    def get_queryset(self):
        categoria = get_object_or_404(Categoria, slug=self.kwargs['slug'])
        return Anuncio.objects.filter(
            categoria=categoria,
            status='ativo'
        ).select_related('usuario', 'categoria').order_by('-data_criacao')

@api_view(['GET'])
@permission_classes([AllowAny])
def categorias_api(request):
    """API para listar todas as categorias - CORRIGIDA"""
    try:
        print("🔍 DEBUG: Acessando API de categorias")
        
        categorias = Categoria.objects.filter(ativa=True).annotate(
            total_anuncios=Count('anuncios', filter=Q(anuncios__status='ativo') | Q(anuncios__status='pendente'))
        ).order_by('ordem_menu', 'titulo')
        
        print(f"✅ DEBUG: {categorias.count()} categorias encontradas")
        
        serializer = CategoriaMobileSerializer(categorias, many=True, context={'request': request})
        return Response(serializer.data)
        
    except Exception as e:
        print(f"🔥 ERRO em categorias_api: {str(e)}")
        return Response(
            {'error': f'Erro ao carregar categorias: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def anuncios_destaque_api(request):
    """API para anúncios em destaque - CORRIGIDA"""
    try:
        print("🔍 DEBUG: Acessando API de anúncios em destaque")
        
        anuncios = Anuncio.objects.filter(
            Q(status='ativo') | Q(status='pendente'),
            destaque=True
        ).select_related('usuario', 'categoria', 'localizacao').prefetch_related(
            'imagens'
        ).order_by('-data_criacao')[:20]
        
        print(f"✅ DEBUG: {anuncios.count()} anúncios em destaque encontrados")
        
        serializer = AnuncioMobileSerializer(anuncios, many=True, context={'request': request})
        return Response(serializer.data)
        
    except Exception as e:
        print(f"🔥 ERRO em anuncios_destaque_api: {str(e)}")
        return Response(
            {'error': f'Erro ao carregar anúncios em destaque: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def anuncios_recentes_api(request):
    """API para anúncios recentes - CORRIGIDA"""
    try:
        print("🔍 DEBUG: Acessando API de anúncios recentes")
        
        anuncios = Anuncio.objects.filter(
            Q(status='ativo') | Q(status='pendente')
        ).select_related('usuario', 'categoria', 'localizacao').prefetch_related(
            'imagens'
        ).order_by('-data_criacao')[:20]
        
        print(f"✅ DEBUG: {anuncios.count()} anúncios recentes encontrados")
        
        serializer = AnuncioMobileSerializer(anuncios, many=True, context={'request': request})
        return Response(serializer.data)
        
    except Exception as e:
        print(f"🔥 ERRO em anuncios_recentes_api: {str(e)}")
        return Response(
            {'error': f'Erro ao carregar anúncios recentes: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def home_data_api(request):
    """API completa para dados da home - VERSÃO DEFINITIVA"""
    try:
        print("🔍 DEBUG: Acessando API de dados da home")
        
        categorias = Categoria.objects.filter(ativa=True).annotate(
            total_anuncios=Count('anuncios', filter=Q(anuncios__status='ativo') | Q(anuncios__status='pendente'))
        ).order_by('ordem_menu', 'titulo')[:10]
        
        categorias_serializer = CategoriaMobileSerializer(
            categorias, 
            many=True, 
            context={'request': request}
        )
        
        anuncios_destaque = Anuncio.objects.filter(
            Q(status='ativo') | Q(status='pendente'),
            destaque=True
        ).select_related('usuario', 'categoria', 'localizacao').prefetch_related(
            'imagens'
        ).order_by('-data_criacao')[:8]
        
        anuncios_recentes = Anuncio.objects.filter(
            Q(status='ativo') | Q(status='pendente')
        ).select_related('usuario', 'categoria', 'localizacao').prefetch_related(
            'imagens'
        ).order_by('-data_criacao')[:8]
        
        print(f"✅ DEBUG: {categorias.count()} categorias, {anuncios_destaque.count()} destaque, {anuncios_recentes.count()} recentes")
    
        destaque_serializer = AnuncioMobileSerializer(anuncios_destaque, many=True, context={'request': request})
        recentes_serializer = AnuncioMobileSerializer(anuncios_recentes, many=True, context={'request': request})
        
        return Response({
            'categorias': categorias_serializer.data,  
            'anuncios_destaque': destaque_serializer.data,
            'anuncios_recentes': recentes_serializer.data,
            'total_categorias': categorias.count(),
            'total_destaque': anuncios_destaque.count(),
            'total_recentes': anuncios_recentes.count(),
        })
        
    except Exception as e:
        print(f"🔥 ERRO em home_data_api: {str(e)}")
        return Response(
            {'error': f'Erro ao carregar dados da home: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def categorias_list_simple(request):
    """API SIMPLES para categorias - CORRIGIDA"""
    try:
        print("🔍 DEBUG: Acessando API SIMPLES de categorias")
        
        categorias = Categoria.objects.filter(ativa=True).annotate(
            total_anuncios=Count('anuncios', filter=Q(anuncios__status='ativo') | Q(anuncios__status='pendente'))
        ).order_by('ordem_menu', 'titulo')
        
        print(f"✅ DEBUG: {categorias.count()} categorias encontradas")
        
        serializer = CategoriaMobileSerializer(categorias, many=True, context={'request': request})
        return Response(serializer.data)
        
    except Exception as e:
        print(f"🔥 ERRO em categorias_list_simple: {str(e)}")
        return Response(
            {'error': f'Erro ao carregar categorias: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        
logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def anuncios_por_categoria_api(request, slug):
    """API para obter anúncios por categoria - CORRIGIDA COM DADOS DO USUÁRIO"""
    try:
        logger.info(f"🔍 [DJANGO] Buscando anúncios da categoria: {slug}")
        
        categoria = get_object_or_404(Categoria, slug=slug, ativa=True)
        logger.info(f"✅ [DJANGO] Categoria encontrada: {categoria.titulo}")
        
        anuncios = Anuncio.objects.filter(
            categoria=categoria,
            status='ativo'
        ).select_related(
            'usuario',  
            'categoria', 
            'localizacao'
        ).prefetch_related(
            'imagens'
        ).order_by('-data_criacao')
        
        logger.info(f"📊 [DJANGO] {anuncios.count()} anúncios encontrados na categoria")
        
        for anuncio in anuncios[:3]:  
            logger.info(f"👤 [DEBUG] Anúncio {anuncio.id} - Usuário: {anuncio.usuario}, Nome: {getattr(anuncio.usuario, 'nome', 'N/A')}")

        ordenar = request.GET.get('ordenar', 'recentes')
        logger.info(f"🔧 [DJANGO] Ordenação solicitada: {ordenar}")
        
        if ordenar == 'recentes':
            anuncios = anuncios.order_by('-data_criacao')
        elif ordenar == 'antigos':
            anuncios = anuncios.order_by('data_criacao')
        elif ordenar == 'menor-preco':
            anuncios = anuncios.order_by('valor')
        elif ordenar == 'maior-preco':
            anuncios = anuncios.order_by('-valor')
        elif ordenar == 'mais-vistos':
            anuncios = anuncios.order_by('-visualizacoes')
        
        page_number = request.GET.get('page', 1)
        per_page = 12
        
        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            page_number = 1
        
        paginator = Paginator(anuncios, per_page)
        
        try:
            anuncios_paginados = paginator.page(page_number)
        except PageNotAnInteger:
            anuncios_paginados = paginator.page(1)
        except EmptyPage:
            anuncios_paginados = paginator.page(paginator.num_pages)
        
        try:
            anuncios_serializer = AnuncioMobileSerializer(
                anuncios_paginados, 
                many=True, 
                context={'request': request}
            )
            
            categoria_serializer = CategoriaMobileSerializer(
                categoria, 
                context={'request': request}
            )
            
            logger.info(f"✅ [DJANGO] Serialização concluída - {len(anuncios_serializer.data)} anúncios")
            
            for i, anuncio_data in enumerate(anuncios_serializer.data[:3]):
                logger.info(f"📱 [DEBUG] Anúncio {i+1} - Nome usuário: {anuncio_data.get('usuario_nome', 'N/A')}")
            
            response_data = {
                'categoria': categoria_serializer.data,
                'anuncios': anuncios_serializer.data,
                'paginacao': {
                    'pagina_atual': page_number,
                    'total_paginas': paginator.num_pages,
                    'total_anuncios': paginator.count,
                    'tem_proxima': anuncios_paginados.has_next(),
                    'tem_anterior': anuncios_paginados.has_previous(),
                }
            }
            
            return Response(response_data)
            
        except Exception as serialization_error:
            logger.error(f"🔥 [DJANGO] Erro na serialização: {str(serialization_error)}")
            return Response(
                {'error': 'Erro ao processar dados dos anúncios'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Categoria.DoesNotExist:
        logger.warning(f"❌ [DJANGO] Categoria não encontrada: {slug}")
        return Response(
            {'error': 'Categoria não encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"🔥 [DJANGO] Erro inesperado em anuncios_por_categoria_api: {str(e)}")
        import traceback
        logger.error(f"📋 [DJANGO] Traceback: {traceback.format_exc()}")
        
        return Response(
            {'error': f'Erro interno do servidor: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )