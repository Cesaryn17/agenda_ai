from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from produtos.models import Anuncio, Categoria
from .models import Localizacao
from django.core.paginator import Paginator
from .serializers import AnuncioSerializer
import logging
from rest_framework import generics
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, DestroyAPIView
from rest_framework.decorators import api_view, permission_classes
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
import logging
from produtos.models import Anuncio
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Prefetch
from django.conf import settings

from produtos.models import Servico, Categoria, Imagem
from .models import Notificacao, Favorito, HistoricoBusca, Mensagem

from .serializers import (
    UsuarioSerializer,
    UsuarioRegistroSerializer,
    UsuarioLoginSerializer,
    NotificacaoSerializer,
    FavoritoSerializer,
    HistoricoBuscaSerializer,
    FotoPerfilSerializer,
    UsuarioUpdateSerializer,
    MensagemSerializer,
    ServicoSerializer,
    ServicoDetailSerializer,
    CategoriaSerializer,
    UsuarioMobileRegistroSerializer,
)

logger = logging.getLogger(__name__)

CustomUser = get_user_model()

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class DebugMixin:
    """Mixin para debug de querysets"""
    def debug_queryset(self, queryset, name):
        if settings.DEBUG:
            print(f"\n{'='*50}")
            print(f"Debug {name}:")
            print(f"Total encontrado: {queryset.count()}")
            if queryset.exists():
                for item in queryset[:3]:  
                    print(f"- ID: {item.id}, Título: {getattr(item, 'titulo', '')}, Status: {getattr(item, 'status', '')}, Ativo: {getattr(item, 'ativa', '')}")
            else:
                print("Nenhum item encontrado!")
            print(f"{'='*50}\n")

class HomeAPIView(APIView, DebugMixin):
    """API para a página inicial"""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            servicos_destaque = Servico.objects.filter(
                destaque=True,
                status='ativo'
            ).select_related('categoria', 'usuario', 'localizacao').prefetch_related(
                Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
            ).order_by('-data_criacao')[:8]
            
            servicos_recentes = Servico.objects.filter(
                status='ativo'
            ).select_related('categoria', 'usuario', 'localizacao').prefetch_related(
                Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
            ).order_by('-data_criacao')[:8]
            
            categorias_populares = Categoria.objects.filter(
                ativa=True
            ).annotate(
                num_servicos=Count('servicos', filter=Q(servicos__status='ativo'))
            ).order_by('-num_servicos')[:8]
            
            total_servicos = Servico.objects.filter(status='ativo').count()
            total_categorias = Categoria.objects.filter(ativa=True).count()
            
            return Response({
                'servicos_destaque': ServicoSerializer(servicos_destaque, many=True).data,
                'servicos_recentes': ServicoSerializer(servicos_recentes, many=True).data,
                'categorias_populares': CategoriaSerializer(categorias_populares, many=True).data,
                'estatisticas': {
                    'total_servicos': total_servicos,
                    'total_categorias': total_categorias,
                }
            })
        
        except Exception as e:
            if settings.DEBUG:
                import traceback
                return Response({
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(
                {"error": "Erro interno do servidor"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ServicoListAPIView(ListAPIView, DebugMixin):
    """API para listagem de serviços com filtros"""
    serializer_class = ServicoSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = {
        'categoria__slug': ['exact'],
        'valor': ['gte', 'lte'],
        'localizacao__id': ['exact'],
        'estado_produto': ['exact'],
    }
    search_fields = ['titulo', 'descricao', 'categoria__titulo']
    ordering_fields = ['data_criacao', 'valor', 'visualizacoes']
    ordering = ['-data_criacao']
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = Servico.objects.filter(
            status='ativo'
        ).select_related('categoria', 'usuario', 'localizacao').prefetch_related(
            Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
        )
        
        destaque = self.request.query_params.get('destaque')
        if destaque and destaque.lower() == 'true':
            queryset = queryset.filter(destaque=True)
        
        self.debug_queryset(queryset, "Serviços filtrados")
        return queryset

class ServicoDetailAPIView(RetrieveAPIView):
    """API para detalhes completos de um serviço"""
    queryset = Servico.objects.filter(status='ativo')
    serializer_class = ServicoDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'pk'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        instance.visualizacoes += 1
        instance.save(update_fields=['visualizacoes'])
        
        favoritado = False
        if request.user.is_authenticated:
            favoritado = Favorito.objects.filter(
                usuario=request.user, 
                servico=instance
            ).exists()
        
        servicos_relacionados = Servico.objects.filter(
            categoria=instance.categoria,
            status='ativo'
        ).exclude(pk=instance.pk).select_related('usuario')[:4]
        
        return Response({
            'servico': self.get_serializer(instance).data,
            'favoritado': favoritado,
            'servicos_relacionados': ServicoSerializer(servicos_relacionados, many=True).data,
            'whatsapp_url': instance.get_whatsapp_url(),
        })

class CategoriaListAPIView(ListAPIView, DebugMixin):
    """API para listagem de categorias"""
    serializer_class = CategoriaSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Categoria.objects.filter(ativa=True).annotate(
            num_servicos=Count('servicos', filter=Q(servicos__status='ativo'))
        ).order_by('-num_servicos')
        
        self.debug_queryset(queryset, "Categorias filtradas")
        return queryset

class UsuarioAPIView(APIView):
    """API para informações e atualização do usuário"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UsuarioUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegistroAPIView(APIView):
    """API para registro de novos usuários - VERSÃO CORRIGIDA"""
    permission_classes = [AllowAny]

    def post(self, request):
        print("📝 [API] Recebendo requisição de registro:", request.data)
        
        data = request.data.copy()
        data['first_name'] = data.get('nome', '')
        data['password2'] = data.get('confirmPassword', '')
        data['termos_aceitos'] = True  
        
        serializer = UsuarioRegistroSerializer(data=data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                print(f"✅ [API] Usuário criado: {user.email}")
                
                refresh = RefreshToken.for_user(user)
                
                user_data = {
                    'id': user.id,
                    'nome': user.nome or user.first_name or user.email.split('@')[0],
                    'email': user.email,
                    'telefone': user.telefone,
                    'data_criacao': user.date_created.isoformat() if hasattr(user, 'date_created') else user.date_joined.isoformat(),
                }
                
                return Response({
                    'user': user_data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'Conta criada com sucesso!'
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                print(f"❌ [API] Erro ao salvar usuário: {str(e)}")
                return Response(
                    {"error": "Erro interno ao criar conta"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        print(f"❌ [API] Erros de validação: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    """API para autenticação de usuários"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UsuarioLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UsuarioSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

class LogoutAPIView(APIView):
    """API para logout de usuários"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {"detail": "Logout realizado com sucesso"},
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception as e:
            return Response(
                {"error": "Token inválido"},
                status=status.HTTP_400_BAD_REQUEST
            )

class FotoPerfilAPIView(APIView):
    """API para upload de foto de perfil"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FotoPerfilSerializer(
            request.user, 
            data=request.data,
            files=request.FILES
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PerfilAPIView(APIView):
    """API para perfil do usuário"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            usuario = request.user
            favoritos = Favorito.objects.filter(
                usuario=usuario
            ).select_related('servico', 'servico__categoria')[:6]
            
            notificacoes = Notificacao.objects.filter(
                usuario=usuario,
                lida=False
            ).order_by('-data_criacao')[:5]
            
            return Response({
                'usuario': UsuarioSerializer(usuario).data,
                'favoritos': FavoritoSerializer(favoritos, many=True).data,
                'notificacoes': NotificacaoSerializer(notificacoes, many=True).data,
                'servicos_count': Servico.objects.filter(usuario=usuario).count(),
            })
        except Exception as e:
            if settings.DEBUG:
                raise e
            return Response(
                {"error": "Erro ao carregar perfil"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class NotificacaoListAPIView(ListAPIView):
    """API para notificações do usuário"""
    serializer_class = NotificacaoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Notificacao.objects.filter(
            usuario=self.request.user
        ).order_by('-data_criacao')

class FavoritoListCreateDestroyView(ListAPIView, CreateAPIView, DestroyAPIView):
    """API para favoritos com operações completas"""
    serializer_class = FavoritoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Favorito.objects.filter(
            usuario=self.request.user
        ).select_related('servico', 'servico__categoria', 'servico__usuario')

    def create(self, request, *args, **kwargs):
        servico_id = request.data.get('servico_id')
        if not servico_id:
            return Response(
                {"error": "O campo servico_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        servico = get_object_or_404(Servico, pk=servico_id, status='ativo')
        favorito, created = Favorito.objects.get_or_create(
            usuario=request.user,
            servico=servico
        )
        
        if created:
            return Response(
                FavoritoSerializer(favorito).data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"detail": "Este serviço já está nos seus favoritos"},
            status=status.HTTP_200_OK
        )

    def delete(self, request, *args, **kwargs):
        servico_id = request.data.get('servico_id')
        if not servico_id:
            return Response(
                {"error": "O campo servico_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        favorito = get_object_or_404(
            Favorito,
            usuario=request.user,
            servico_id=servico_id
        )
        favorito.delete()
        return Response(
            {"detail": "Serviço removido dos favoritos"},
            status=status.HTTP_204_NO_CONTENT
        )

class MensagemAPIView(ListAPIView, CreateAPIView):
    """API para listar e enviar mensagens"""
    serializer_class = MensagemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Mensagem.objects.filter(
            Q(remetente=self.request.user) | Q(destinatario=self.request.user)
        ).order_by('-data_envio').distinct('conversa_id')

    def perform_create(self, serializer):
        serializer.save(remetente=self.request.user)

class ConversaAPIView(ListAPIView):
    """API para visualizar uma conversa específica"""
    serializer_class = MensagemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        conversa_id = self.kwargs['conversa_id']
        return Mensagem.objects.filter(
            conversa_id=conversa_id
        ).filter(
            Q(remetente=self.request.user) | Q(destinatario=self.request.user)
        ).order_by('data_envio')

class HistoricoBuscaListAPIView(ListAPIView):
    """API para histórico de buscas"""
    serializer_class = HistoricoBuscaSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return HistoricoBusca.objects.filter(
            usuario=self.request.user
        ).order_by('-data_busca')

class MarcarNotificacaoLidaView(APIView):
    """API para marcar uma notificação como lida"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notificacao = get_object_or_404(Notificacao, pk=pk, usuario=request.user)
        notificacao.lida = True
        notificacao.save()
        return Response({'success': True})

class MarcarTodasNotificacoesLidasView(APIView):
    """API para marcar todas as notificações como lidas"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notificacao.objects.filter(usuario=request.user, lida=False).update(lida=True)
        return Response({'success': True})

class ContadorNotificacoesNaoLidasView(APIView):
    """API para obter contador de notificações não lidas"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notificacao.objects.filter(usuario=request.user, lida=False).count()
        return Response({'count': count})

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Endpoint de verificação de saúde da API"""
    return Response({
        "status": "healthy",
        "service": "Agenda AI API",
        "version": "1.0.0"
    })

class EstatisticasAPIView(APIView):
    """API para estatísticas gerais da plataforma"""
    permission_classes = [AllowAny]

    def get(self, request):
        total_servicos = Servico.objects.filter(status='ativo').count()
        total_usuarios = CustomUser.objects.count()
        total_categorias = Categoria.objects.filter(ativa=True).count()
        
        return Response({
            'total_servicos': total_servicos,
            'total_usuarios': total_usuarios,
            'total_categorias': total_categorias,
            'servicos_por_categoria': Categoria.objects.filter(ativa=True).annotate(
                total=Count('servicos', filter=Q(servicos__status='ativo'))
            ).values('titulo', 'total').order_by('-total')[:10]
        })

logger = logging.getLogger(__name__)

class SearchAPIView(APIView):
    """API View para pesquisa avançada de anúncios"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            query = request.GET.get('q', '').strip()
            categoria = request.GET.get('categoria', '')
            localizacao = request.GET.get('localizacao', '')
            ordenar = request.GET.get('ordenar', 'recentes')
            preco_min = request.GET.get('preco_min', '')
            preco_max = request.GET.get('preco_max', '')
            page = request.GET.get('page', 1)
            
            logger.info(f"🔍 API Search - Query: {query}, Categoria: {categoria}")
            
            anuncios = Anuncio.objects.filter(
                Q(status='ativo') | Q(status='pendente')
            ).select_related('usuario', 'localizacao', 'categoria').prefetch_related(
                Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
            )

            if query:
                anuncios = anuncios.filter(
                    Q(titulo__icontains=query) |
                    Q(descricao__icontains=query) |
                    Q(categoria__titulo__icontains=query)
                )

            if categoria:
                anuncios = anuncios.filter(categoria__slug=categoria)

            if localizacao:
                anuncios = anuncios.filter(localizacao__id=localizacao)

            if preco_min:
                try:
                    anuncios = anuncios.filter(valor__gte=float(preco_min))
                except (ValueError, TypeError):
                    pass

            if preco_max:
                try:
                    anuncios = anuncios.filter(valor__lte=float(preco_max))
                except (ValueError, TypeError):
                    pass

            ordenacao_map = {
                'recentes': '-data_criacao',
                'antigos': 'data_criacao',
                'menor-preco': 'valor',
                'maior-preco': '-valor',
                'mais-vistos': '-visualizacoes',
            }
            anuncios = anuncios.order_by(ordenacao_map.get(ordenar, '-data_criacao'))

            paginator = Paginator(anuncios, 12)
            try:
                anuncios_paginados = paginator.page(page)
            except:
                anuncios_paginados = paginator.page(1)

            serializer = AnuncioSerializer(
                anuncios_paginados, 
                many=True, 
                context={'request': request}
            )

            categorias = Categoria.objects.filter(ativa=True).annotate(
                total_anuncios=Count('anuncios', filter=Q(anuncios__status='ativo') | Q(anuncios__status='pendente'))
            ).order_by('titulo')
            
            localizacoes = Localizacao.objects.all()

            if query and request.user.is_authenticated:
                try:
                    historico_busca = HistoricoBusca(
                        usuario=request.user,
                        termo=query,
                        tipo='search'
                    )
                    
                    if categoria:
                        try:
                            categoria_obj = Categoria.objects.get(slug=categoria)
                            historico_busca.categoria = categoria_obj
                        except Categoria.DoesNotExist:
                            pass
                    
                    if localizacao:
                        try:
                            localizacao_obj = Localizacao.objects.get(id=localizacao)
                            historico_busca.localizacao = localizacao_obj
                        except Localizacao.DoesNotExist:
                            pass
                    
                    historico_busca.save()
                    logger.info(f"📝 Histórico salvo: {query} para usuário {request.user.email}")
                    
                except Exception as e:
                    logger.error(f"⚠️ Erro ao salvar histórico: {str(e)}")

            return Response({
                'anuncios': serializer.data,
                'total_resultados': anuncios.count(),
                'pagina_atual': anuncios_paginados.number,
                'total_paginas': paginator.num_pages,
                'tem_proxima': anuncios_paginados.has_next(),
                'tem_anterior': anuncios_paginados.has_previous(),
                'categorias': [{
                    'id': cat.id,
                    'titulo': cat.titulo,
                    'slug': cat.slug,
                    'total_anuncios': getattr(cat, 'total_anuncios', 0)
                } for cat in categorias],
                'localizacoes': [{
                    'id': loc.id,
                    'nome': loc.nome,
                    'cidade': loc.cidade,
                    'estado': loc.estado
                } for loc in localizacoes],
                'filtros_aplicados': {
                    'query': query,
                    'categoria': categoria,
                    'localizacao': localizacao,
                    'ordenar': ordenar,
                    'preco_min': preco_min,
                    'preco_max': preco_max,
                }
            })

        except Exception as e:
            logger.error(f"❌ ERRO na API de pesquisa: {str(e)}")
            if settings.DEBUG:
                import traceback
                return Response({
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(
                {"error": "Erro interno do servidor na pesquisa"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class MobileRegistroAPIView(APIView):
    """API para registro mobile"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UsuarioMobileRegistroSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            refresh = RefreshToken.for_user(user)
            
            user_data = UsuarioSerializer(user).data
            
            return Response({
                'user': user_data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'Conta criada com sucesso!'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
