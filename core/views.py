from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q, Prefetch
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.utils import timezone
from produtos.models import Anuncio, Categoria, Imagem
from django.contrib.contenttypes.models import ContentType
import requests
from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from .models import PostagemProduto, MidiaPostagem
from .forms import CriarPostagemForm 
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib.auth import update_session_auth_hash
from .models import ConfiguracaoUsuario
from rest_framework import generics
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from rest_framework.exceptions import ValidationError
from django.urls import reverse  
from chat.models import Chat, Mensagem  
import json
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Sum
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import PaginaPessoal, PostagemProduto, SeguidorPagina


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import login
from django.contrib import messages
from .forms import CustomUserCreationForm
from django.contrib.auth import logout as django_logout
from django.http import HttpResponseRedirect

from produtos.models import Servico, Categoria, Imagem
from .models import Notificacao, Favorito, HistoricoBusca, Localizacao

import logging

logger = logging.getLogger(__name__)

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
    CategoriaSerializer,
    UsuarioMobileRegistroSerializer,
    AnuncioSerializer,
)
CustomUser = get_user_model()

def custom_logout(request):
    """View de logout que limpa completamente a sessão"""
    django_logout(request)
    request.session.flush()  
    response = HttpResponseRedirect(reverse('home'))
    response.delete_cookie('sessionid')  
    response.delete_cookie('csrftoken')
    return response

def registro_view(request):
    """
    View 100% CORRETA - apenas campos que EXISTEM no seu modelo
    """
    if request.method == 'POST':
        print("📝 [REGISTRO] Iniciando processo de registro...")
        
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')
        termos_aceitos = request.POST.get('terms') == 'on'
        
        print(f"📦 [REGISTRO] Dados: Nome={name}, Email={email}")
        
        errors = []
        
        if not name:
            errors.append('O nome completo é obrigatório.')
        
        if not email or '@' not in email:
            errors.append('Por favor, insira um e-mail válido.')
        
        if not phone:
            errors.append('O telefone é obrigatório.')
        
        if not password or len(password) < 6:
            errors.append('A senha deve ter pelo menos 6 caracteres.')
        
        if password != confirm_password:
            errors.append('As senhas não coincidem.')
        
        if not termos_aceitos:
            errors.append('Você deve aceitar os termos de uso.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'registro.html', {
                'name': name, 'email': email, 'phone': phone, 'terms': termos_aceitos,
            })
        
        try:
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Este email já está cadastrado.')
                return render(request, 'registro.html', {
                    'name': name, 'email': email, 'phone': phone, 'terms': True,
                })
            
            print(f"👤 [REGISTRO] Criando usuário: {email}")
            
            import re
            phone_clean = re.sub(r'[^\d]', '', phone)
            
            user = CustomUser(
                email=email,
                nome=name,  
                nome_utilizador=email.split('@')[0], 
                telefone=phone_clean,
                termos_aceitos=termos_aceitos,
                is_active=True
            )
            user.set_password(password)
            user.save()
            
            print(f"✅ [REGISTRO] Usuário criado com ID: {user.id}")
            
            # Login
            user = authenticate(request, email=email, password=password)
            if user:
                login(request, user)
                messages.success(request, 'Conta criada com sucesso!')
                return redirect('home')
            else:
                messages.success(request, 'Conta criada! Faça login.')
                return redirect('login')
                
        except Exception as e:
            print(f"💥 [REGISTRO] Erro: {str(e)}")
            messages.error(request, f'Erro ao criar conta: {str(e)}')
            
    return render(request, 'registro.html')

def login_view(request):
    """View para a página de login HTML - Versão Corrigida"""
    print("=== DEBUG: login_view chamada ===")
    
    if request.user.is_authenticated:
        print(f"DEBUG: Usuário já autenticado: {request.user.email}")
        next_url = request.GET.get('next', 'home')
        return redirect(next_url)
    
    if request.method == 'POST':
        print("DEBUG: POST request recebido")
        email = request.POST.get('email')
        password = request.POST.get('password')
        print(f"DEBUG: email={email}, password={'*' * len(password) if password else 'None'}")
        
        try:
            user = authenticate(request, email=email, password=password)
            print(f"DEBUG: Resultado da autenticação: {user}")
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    print(f"DEBUG: Login realizado para usuário: {user.email}")
                    
                    messages.success(request, 'Login realizado com sucesso!')
                    
                    next_url = request.GET.get('next', 'home')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Esta conta está desativada.')
            else:
                print("DEBUG: Credenciais inválidas")
                messages.error(request, 'Email ou senha incorretos.')
                
        except Exception as e:
            print(f"DEBUG: Erro no login: {str(e)}")
            messages.error(request, 'Erro ao fazer login. Tente novamente.')
    
    return render(request, 'login.html')

def travel_view(request):
    context = {} 
    return render(request, 'travel.html', context)

def anuncio_detail_view(request, anuncio_id):
    try:
        anuncio = get_object_or_404(
            Anuncio.objects.select_related(
                'usuario', 'categoria', 'localizacao'
            ).prefetch_related(
                Prefetch('imagens', queryset=Imagem.objects.all().order_by('capa', 'id'))
            ),
            pk=anuncio_id,
            status__in=['ativo', 'pendente']  
        )

        if not hasattr(anuncio, 'imagens'):
            anuncio.imagens_list = []
        else:
            anuncio.imagens_list = list(anuncio.imagens.all())
        
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
        ).exclude(pk=anuncio.id).select_related(
            'usuario', 'localizacao', 'categoria'
        ).prefetch_related(
            Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
        )[:4]
        
        for anuncio_rel in anuncios_relacionados:
            if hasattr(anuncio_rel, 'imagens'):
                anuncio_rel.imagens_list = list(anuncio_rel.imagens.all())
            else:
                anuncio_rel.imagens_list = []
            
            if request.user.is_authenticated:
                anuncio_rel.favoritado = Favorito.objects.filter(
                    usuario=request.user,
                    content_type=content_type,
                    object_id=anuncio_rel.id
                ).exists()
            else:
                anuncio_rel.favoritado = False
        
        if anuncio.valor:
            anuncio.valor_formatado = f"R$ {anuncio.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            anuncio.valor_formatado = "A combinar"
        
        anuncio.localizacao_str = "Localização não informada"
        if anuncio.localizacao:
            if hasattr(anuncio.localizacao, 'cidade') and hasattr(anuncio.localizacao, 'estado'):
                anuncio.localizacao_str = f"{anuncio.localizacao.cidade}, {anuncio.localizacao.estado}"
            elif hasattr(anuncio.localizacao, 'nome'):
                anuncio.localizacao_str = anuncio.localizacao.nome
            elif hasattr(anuncio.localizacao, 'cidade'):
                anuncio.localizacao_str = anuncio.localizacao.cidade
            elif hasattr(anuncio.localizacao, 'estado'):
                anuncio.localizacao_str = anuncio.localizacao.estado
            else:
                anuncio.localizacao_str = str(anuncio.localizacao)
        
        nome_anunciante = "Usuário"
        if anuncio.usuario:

            if anuncio.usuario.first_name and anuncio.usuario.last_name:
                nome_anunciante = f"{anuncio.usuario.first_name} {anuncio.usuario.last_name}"
            elif anuncio.usuario.first_name:
                nome_anunciante = anuncio.usuario.first_name
            elif hasattr(anuncio.usuario, 'nome') and anuncio.usuario.nome:
                nome_anunciante = anuncio.usuario.nome
            elif anuncio.usuario.username:
                nome_anunciante = anuncio.usuario.username

        anuncios_vendedor_count = Anuncio.objects.filter(
            usuario=anuncio.usuario,
            status='ativo'
        ).count()

        tempo_na_plataforma = "Há muito tempo"
        if anuncio.usuario.date_joined:
            from datetime import datetime
            from django.utils import timezone
            
            joined_date = anuncio.usuario.date_joined
            now = timezone.now()
            delta = now - joined_date
            
            if delta.days < 30:
                tempo_na_plataforma = "Novo na plataforma"
            elif delta.days < 365:
                meses = delta.days // 30
                tempo_na_plataforma = f"{meses} {'mês' if meses == 1 else 'meses'}"
            else:
                anos = delta.days // 365
                tempo_na_plataforma = f"{anos} {'ano' if anos == 1 else 'anos'}"

        anuncio.visualizacoes += 1
        anuncio.save(update_fields=['visualizacoes'])
        
        context = {
            'anuncio': anuncio,
            'favoritado': favoritado,
            'anuncios_relacionados': anuncios_relacionados,
            'whatsapp_number': anuncio.whatsapp or '5511999999999',
            'nome_anunciante': nome_anunciante,
            'anuncios_vendedor_count': anuncios_vendedor_count,
            'tempo_na_plataforma': tempo_na_plataforma,
        }
        
        return render(request, 'detalhe.html', context)
        
    except Anuncio.DoesNotExist:
        messages.error(request, "Anúncio não encontrado ou indisponível.")
        return redirect('home')
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, "Ocorreu um erro ao carregar o anúncio.")
        return redirect('home')
    
def servico_detail_view(request, servico_id):
    """View de detalhe de serviço"""
    try:
        servico = get_object_or_404(
            Servico.objects.select_related('usuario', 'categoria', 'localizacao')
                           .prefetch_related('imagens'),
            pk=servico_id,
            status='ativo'
        )
        
        if request.user.is_authenticated:
            servico.visualizacoes += 1
            servico.save(update_fields=['visualizacoes'])
        
        favoritado = False
        if request.user.is_authenticated:
            favoritado = Favorito.objects.filter(
                usuario=request.user, 
                servico=servico
            ).exists()
        
        servicos_relacionados = Servico.objects.filter(
            categoria=servico.categoria,
            status='ativo'
        ).exclude(pk=servico.pk).select_related('usuario')[:4]
        

        categorias = Categoria.objects.filter(
            ativa=True
        ).annotate(
            total_anuncios=Count('anuncios', filter=Q(anuncios__status='ativo') | Q(anuncios__status='pendente'))
        ).order_by('ordem_menu', 'titulo')

        context = {
            'servico': servico,
            'favoritado': favoritado,
            'servicos_relacionados': servicos_relacionados,
            'whatsapp_url': servico.get_whatsapp_url(),
            'categorias': categorias,
        }
        return render(request, 'detalhe.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '404.html', status=404)

@login_required
def perfil_view(request):
    """View de perfil do usuário com favoritos e notificações"""
    try:

        usuario = request.user
        
        try:
            profile = usuario.profile
        except AttributeError:
            profile = None 
        
        favoritos = Favorito.objects.filter(
            usuario=usuario
        ).select_related('servico', 'servico__categoria')[:6]
        
        notificacoes = Notificacao.objects.filter(
            usuario=usuario,
            lida=False
        ).order_by('-data_criacao')[:5]
    
        servicos_count = Servico.objects.filter(
            usuario=usuario
        ).count()
        
        context = {
            'usuario': usuario,
            'favoritos': favoritos,
            'notificacoes': notificacoes,
            'servicos_count': servicos_count,
            'profile': profile,  
        }
        return render(request, 'perfil.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '500.html', status=500)

@login_required
def my_ads_view(request):
    """View para listar e gerenciar os anúncios do usuário logado."""
    try:
        meus_anuncios = Anuncio.objects.filter(
            usuario=request.user
        ).select_related('localizacao', 'categoria').prefetch_related(
            Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
        ).order_by('-data_criacao')

        if request.method == 'POST' and 'delete_ad' in request.POST:
            anuncio_id = request.POST.get('delete_ad')
            try:
                anuncio = get_object_or_404(Anuncio, pk=anuncio_id, usuario=request.user)
                anuncio_titulo = anuncio.titulo
                anuncio.delete()
                messages.success(request, f'Anúncio "{anuncio_titulo}" excluído com sucesso!')

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Anúncio "{anuncio_titulo}" excluído com sucesso!',
                        'anuncio_id': anuncio_id
                    })
                    
                return redirect('my-ads')
            except Exception as e:
                error_msg = f'Erro ao excluir anúncio: {str(e)}'
                messages.error(request, error_msg)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    }, status=500)
                    
                return redirect('my-ads')
        
        if request.method == 'POST' and 'change_status' in request.POST:
            anuncio_id = request.POST.get('change_status')
            novo_status = request.POST.get('novo_status')
            try:
                anuncio = get_object_or_404(Anuncio, pk=anuncio_id, usuario=request.user)
                if novo_status in ['ativo', 'pendente', 'inativo']:
                    anuncio.status = novo_status
                    anuncio.save()
                    msg = f'Status alterado para {novo_status.capitalize()}!'
                    messages.success(request, msg)
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': msg,
                            'novo_status': novo_status
                        })
                else:
                    error_msg = 'Status inválido'
                    messages.error(request, error_msg)
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'error': error_msg
                        }, status=400)
            except Exception as e:
                error_msg = f'Erro ao alterar status: {str(e)}'
                messages.error(request, error_msg)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    }, status=500)
        
        total_anuncios = meus_anuncios.count()
        anuncios_ativos = meus_anuncios.filter(status='ativo').count()
        anuncios_pendentes = meus_anuncios.filter(status='pendente').count()
        anuncios_inativos = meus_anuncios.filter(status='inativo').count()
        
        context = {
            'meus_anuncios': meus_anuncios,
            'total_anuncios': total_anuncios,
            'anuncios_ativos': anuncios_ativos,
            'anuncios_pendentes': anuncios_pendentes,
            'anuncios_inativos': anuncios_inativos,
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            anuncios_data = []
            for anuncio in meus_anuncios:
                primeira_imagem = anuncio.imagens.first() if anuncio.imagens.exists() else None
                anuncios_data.append({
                    'id': anuncio.id,
                    'titulo': anuncio.titulo,
                    'categoria': anuncio.categoria.titulo,
                    'valor': float(anuncio.valor) if anuncio.valor else 0,
                    'status': anuncio.status,
                    'status_display': anuncio.get_status_display(),
                    'data_criacao': anuncio.data_criacao.strftime('%d/%m/%Y'),
                    'visualizacoes': anuncio.visualizacoes,
                    'localizacao': f"{anuncio.localizacao.cidade}, {anuncio.localizacao.estado}" if anuncio.localizacao else '',
                    'imagem_url': primeira_imagem.imagem.url if primeira_imagem and primeira_imagem.imagem else None,
                    'destaque': anuncio.destaque,
                    'estado_produto': anuncio.estado_produto,
                })
            
            return JsonResponse({
                'anuncios': anuncios_data,
                'estatisticas': {
                    'total_anuncios': total_anuncios,
                    'anuncios_ativos': anuncios_ativos,
                    'anuncios_pendentes': anuncios_pendentes,
                    'anuncios_inativos': anuncios_inativos,
                }
            })
        
        return render(request, 'meus_anuncios.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        
        error_msg = 'Erro ao carregar seus anúncios.'
        messages.error(request, error_msg)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=500)
            
        return render(request, 'meus_anuncios.html', {
            'meus_anuncios': [],
            'total_anuncios': 0,
            'anuncios_ativos': 0,
            'anuncios_pendentes': 0,
            'anuncios_inativos': 0,
        })

def contact_view(request):
    """
    Renders the contact page.
    """
    return render(request, 'contact.html')

def about_view(request):
    """
    Renders the about page.
    """
    return render(request, 'about.html')

def create_ad(request):
    return render(request, 'your_app/create_ad.html') 

def search_view(request):
    """View CORRIGIDA para pesquisa - funcionando corretamente"""
    try:
        query = request.GET.get('q', '').strip()
        categoria_filter = request.GET.get('categoria', '')
        localizacao_filter = request.GET.get('localizacao', '')
        ordenar_filter = request.GET.get('ordenar', 'recentes')
        preco_min = request.GET.get('preco_min', '')
        preco_max = request.GET.get('preco_max', '')
        
        print(f"🔍 DEBUG Pesquisa - Query: {query}, Categoria: {categoria_filter}")
        
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
            print(f"✅ Filtro por query aplicado: {query}")
        
        if categoria_filter:
            anuncios = anuncios.filter(categoria__slug=categoria_filter)
            print(f"✅ Filtro por categoria: {categoria_filter}")
        
        if localizacao_filter:
            anuncios = anuncios.filter(localizacao__id=localizacao_filter)
            print(f"✅ Filtro por localização: {localizacao_filter}")
        
        if preco_min:
            try:
                anuncios = anuncios.filter(valor__gte=float(preco_min))
                print(f"✅ Preço mínimo: {preco_min}")
            except (ValueError, TypeError):
                print("❌ Erro no preço mínimo")
                pass
        
        if preco_max:
            try:
                anuncios = anuncios.filter(valor__lte=float(preco_max))
                print(f"✅ Preço máximo: {preco_max}")
            except (ValueError, TypeError):
                print("❌ Erro no preço máximo")
                pass
        
        if ordenar_filter == 'recentes':
            anuncios = anuncios.order_by('-data_criacao')
        elif ordenar_filter == 'antigos':
            anuncios = anuncios.order_by('data_criacao')
        elif ordenar_filter == 'menor-preco':
            anuncios = anuncios.order_by('valor')
        elif ordenar_filter == 'maior-preco':
            anuncios = anuncios.order_by('-valor')
        elif ordenar_filter == 'mais-vistos':
            anuncios = anuncios.order_by('-visualizacoes')
        
        print(f"📊 Total de anúncios encontrados: {anuncios.count()}")
        
        page = request.GET.get('page', 1)
        paginator = Paginator(anuncios, 12)
        
        try:
            anuncios_paginados = paginator.page(page)
        except PageNotAnInteger:
            anuncios_paginados = paginator.page(1)
        except EmptyPage:
            anuncios_paginados = paginator.page(paginator.num_pages)
        
        for anuncio in anuncios_paginados:
            if request.user.is_authenticated:
                anuncio.favoritado = Favorito.objects.filter(
                    usuario=request.user,
                    content_type=ContentType.objects.get_for_model(Anuncio),
                    object_id=anuncio.id
                ).exists()
            else:
                anuncio.favoritado = False

            if anuncio.valor:
                anuncio.valor_formatado = f"R$ {anuncio.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            else:
                anuncio.valor_formatado = "A combinar"
        
        categorias = Categoria.objects.filter(ativa=True)
        localizacoes = Localizacao.objects.all()
        
        context = {
            'anuncios': anuncios_paginados,
            'query': query,
            'categorias': categorias,
            'localizacoes': localizacoes,
            'total_resultados': anuncios.count(),
            'categoria_filtro': categoria_filter,
            'localizacao_filtro': localizacao_filter,
            'ordenar_filtro': ordenar_filter,
            'preco_min_filtro': preco_min,
            'preco_max_filtro': preco_max,
        }
        
        return render(request, 'search_results.html', context)
        
    except Exception as e:
        print(f"🔥 ERRO na pesquisa: {str(e)}")
        if settings.DEBUG:
            raise e
        
        context = {
            'anuncios': [],
            'query': query,
            'categorias': Categoria.objects.filter(ativa=True),
            'localizacoes': Localizacao.objects.all(),
            'total_resultados': 0,
            'error': 'Ocorreu um erro na pesquisa. Tente novamente.'
        }
        return render(request, 'search_results.html', context)

def home_view(request):
    try:
        ANUNCIOS_POR_SECAO = 8
        ANUNCIOS_MINIMOS_PARA_CARROSSEL = 4
        
        anuncios_destaque = Anuncio.objects.filter(
            Q(status='ativo') | Q(status='pendente'),
            destaque=True
        ).select_related('usuario', 'localizacao', 'categoria').prefetch_related(
            Prefetch('imagens', 
                     queryset=Imagem.objects.filter(capa=True).exclude(imagem=''),
                     to_attr='imagens_capa')
        ).order_by('-data_criacao')[:ANUNCIOS_POR_SECAO]

        anuncios_recentes = Anuncio.objects.filter(
            Q(status='ativo') | Q(status='pendente')
        ).select_related('usuario', 'localizacao', 'categoria').prefetch_related(
            Prefetch('imagens',
                     queryset=Imagem.objects.filter(capa=True).exclude(imagem=''),
                     to_attr='imagens_capa')
        ).order_by('-data_criacao')[:ANUNCIOS_POR_SECAO]

        anuncios_populares = Anuncio.objects.filter(
            Q(status='ativo') | Q(status='pendente')
        ).select_related('usuario', 'localizacao', 'categoria').prefetch_related(
            Prefetch('imagens',
                     queryset=Imagem.objects.filter(capa=True).exclude(imagem=''),
                     to_attr='imagens_capa')
        ).order_by('-visualizacoes')[:ANUNCIOS_POR_SECAO]

        categorias_populares_ids = list(
            Categoria.objects.filter(
                ativa=True
            ).annotate(
                total_anuncios=Count('anuncios', filter=Q(anuncios__status='ativo') | Q(anuncios__status='pendente'))
            ).order_by('-total_anuncios')[:3].values_list('id', flat=True)
        )
        
        if len(anuncios_recentes) < ANUNCIOS_MINIMOS_PARA_CARROSSEL and categorias_populares_ids:
            anuncios_recomendados = Anuncio.objects.filter(
                Q(status='ativo') | Q(status='pendente'),
                categoria_id__in=categorias_populares_ids
            ).select_related('usuario', 'localizacao', 'categoria').prefetch_related(
                Prefetch('imagens',
                         queryset=Imagem.objects.filter(capa=True).exclude(imagem=''),
                         to_attr='imagens_capa')
            ).order_by('?')[:ANUNCIOS_POR_SECAO]
        else:
            anuncios_recomendados = anuncios_recentes

        categorias = Categoria.objects.filter(
            ativa=True
        ).annotate(
            total_anuncios=Count('anuncios', filter=Q(anuncios__status='ativo') | Q(anuncios__status='pendente'))
        ).order_by('ordem_menu', 'titulo')

        categorias_populares = categorias.annotate(
            num_anuncios=Count('anuncios', filter=Q(anuncios__status='ativo') | Q(anuncios__status='pendente'))
        ).filter(num_anuncios__gt=0).order_by('-num_anuncios')[:6]

        anuncios_destaque = list(anuncios_destaque) if anuncios_destaque else []
        anuncios_recentes = list(anuncios_recentes) if anuncios_recentes else []
        anuncios_populares = list(anuncios_populares) if anuncios_populares else []
        anuncios_recomendados = list(anuncios_recomendados) if anuncios_recomendados else []
        categorias = list(categorias) if categorias else []
        categorias_populares = list(categorias_populares) if categorias_populares else []

        from django.contrib.contenttypes.models import ContentType
        anuncio_content_type = ContentType.objects.get_for_model(Anuncio)

        def processar_anuncios(lista_anuncios):
            for anuncio in lista_anuncios:
                if request.user.is_authenticated:
                    anuncio.favoritado = Favorito.objects.filter(
                        usuario=request.user,
                        content_type=anuncio_content_type,
                        object_id=anuncio.id
                    ).exists()
                else:
                    anuncio.favoritado = False
                
                if anuncio.usuario:
                    anuncio.usuario.first_name = anuncio.usuario.first_name or 'Usuário'
                    anuncio.usuario.last_name = anuncio.usuario.last_name or ''
                else:
                    class AnonymousUser:
                        first_name = 'Usuário'
                        last_name = ''
                    anuncio.usuario = AnonymousUser()
                
                if hasattr(anuncio, 'imagens_capa') and anuncio.imagens_capa:
                    anuncio.first_image = anuncio.imagens_capa[0]
                else:
                    anuncio.first_image = None
            return lista_anuncios

        anuncios_destaque = processar_anuncios(anuncios_destaque)
        anuncios_recentes = processar_anuncios(anuncios_recentes)
        anuncios_populares = processar_anuncios(anuncios_populares)
        anuncios_recomendados = processar_anuncios(anuncios_recomendados)

        total_anuncios = Anuncio.objects.filter(
            Q(status='ativo') | Q(status='pendente')
        ).count()
        
        total_usuarios = CustomUser.objects.count()
        
        anuncios_por_categoria = Categoria.objects.filter(
            ativa=True
        ).annotate(
            total=Count('anuncios', filter=Q(anuncios__status='ativo') | Q(anuncios__status='pendente'))
        ).values('titulo', 'total').order_by('-total')[:5]

        context = {
            'anuncios_destaque': anuncios_destaque,
            'anuncios_recentes': anuncios_recentes,
            'anuncios_populares': anuncios_populares,
            'anuncios_recomendados': anuncios_recomendados,
            'categorias': categorias,
            'categorias_populares': categorias_populares,
            'total_anuncios': total_anuncios,
            'total_usuarios': total_usuarios,
            'anuncios_por_categoria': anuncios_por_categoria,
            'tem_anuncios_suficientes': len(anuncios_recentes) >= ANUNCIOS_MINIMOS_PARA_CARROSSEL,
        }
        
        return render(request, 'home.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        import logging
        logging.error(f"Erro na home_view: {str(e)}")
        
        return render(request, 'home.html', {
            'anuncios_destaque': [],
            'anuncios_recentes': [],
            'anuncios_populares': [],
            'anuncios_recomendados': [],
            'categorias': [],
            'categorias_populares': [],
            'total_anuncios': 0,
            'total_usuarios': 0,
            'anuncios_por_categoria': [],
            'tem_anuncios_suficientes': False,
        })

@login_required
def perfil_view(request):
    """View de perfil do usuário com favoritos e notificações"""
    try:
        usuario = request.user
        
        from django.contrib.contenttypes.models import ContentType
        servico_content_type = ContentType.objects.get_for_model(Servico)
        
        favoritos = Favorito.objects.filter(
            usuario=usuario,
            content_type=servico_content_type
        ).select_related('content_type')[:6]
        
        for favorito in favoritos:
            try:
                favorito.servico = favorito.content_object
            except:
                favorito.servico = None
        
        notificacoes = Notificacao.objects.filter(
            usuario=usuario,
            lida=False
        ).order_by('-data_criacao')[:5]
        
        servicos_count = Servico.objects.filter(usuario=usuario).count()
        
        servicos_usuario = Servico.objects.filter(
            usuario=usuario,
            status='ativo'
        ).select_related('categoria', 'localizacao').prefetch_related('imagens')[:4]
        
        context = {
            'usuario': usuario,
            'favoritos': favoritos,
            'notificacoes': notificacoes,
            'servicos_count': servicos_count,
            'servicos_usuario': servicos_usuario,
        }
        return render(request, 'perfil.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '500.html', status=500)
    
@login_required
def favorites_view(request):
    """View robusta para listar favoritos do usuário"""
    try:
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        from django.contrib.contenttypes.models import ContentType
        
        anuncio_content_type = ContentType.objects.get_for_model(Anuncio)
        
        favoritos_list = Favorito.objects.filter(
            usuario=request.user,
            content_type=anuncio_content_type
        ).select_related('content_type').order_by('-data_criacao')
        
        paginator = Paginator(favoritos_list, 12)
        page = request.GET.get('page', 1)
        
        try:
            favoritos = paginator.page(page)
        except PageNotAnInteger:
            favoritos = paginator.page(1)
        except EmptyPage:
            favoritos = paginator.page(paginator.num_pages)
        
        favoritos_processados = []
        for favorito in favoritos:
            try:
                anuncio = favorito.content_object
                if anuncio and hasattr(anuncio, 'status') and anuncio.status in ['ativo', 'pendente']:
                    
                    if hasattr(anuncio, 'imagens') and anuncio.imagens.exists():
                        anuncio.first_image = anuncio.imagens.filter(capa=True).first() or anuncio.imagens.first()
                    else:
                        anuncio.first_image = None
                    

                    if hasattr(anuncio, 'valor') and anuncio.valor:
                        anuncio.valor_formatado = f"R$ {anuncio.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    else:
                        anuncio.valor_formatado = "A combinar"
                    
                    if hasattr(anuncio, 'localizacao') and anuncio.localizacao:
                        anuncio.localizacao_str = f"{anuncio.localizacao.cidade}, {anuncio.localizacao.estado}"
                    else:
                        anuncio.localizacao_str = "Localização não informada"
                    
                    favoritos_processados.append({
                        'favorito': favorito,
                        'item': anuncio
                    })
            except Exception as e:
                print(f"Erro ao processar favorito {favorito.id}: {str(e)}")
                continue
        
        context = {
            'favoritos_processados': favoritos_processados,
            'total_favoritos': favoritos_list.count(),
            'page_obj': favoritos,
        }
        
        return render(request, 'favoritos.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '500.html', status=500)
    
@login_required
def messages_view(request):
    """View para listar conversas do usuário - MELHORADA"""
    try:

        chats = Chat.objects.filter(participantes=request.user) \
                          .prefetch_related('participantes', 'mensagens_chat') \
                          .order_by('-data_criacao')

        chats_com_info = []
        for chat in chats:
            outro_usuario = chat.participantes.exclude(id=request.user.id).first()
            
            nome_usuario = "Usuário"
            if outro_usuario:
                if outro_usuario.first_name and outro_usuario.last_name:
                    nome_usuario = f"{outro_usuario.first_name} {outro_usuario.last_name}"
                elif outro_usuario.first_name:
                    nome_usuario = outro_usuario.first_name
                elif outro_usuario.username:
                    nome_usuario = outro_usuario.username
                elif outro_usuario.email:
                    nome_usuario = outro_usuario.email.split('@')[0]
            
            ultima_mensagem = chat.mensagens_chat.order_by('-data_envio').first()

            mensagens_nao_lidas = 0
            if outro_usuario:
                mensagens_nao_lidas = chat.mensagens_chat.filter(
                    lida=False, 
                    remetente=outro_usuario
                ).count()

            chats_com_info.append({
                'id': chat.id,
                'outro_usuario': outro_usuario,
                'outro_usuario_nome': nome_usuario, 
                'ultima_mensagem': ultima_mensagem.conteudo if ultima_mensagem else 'Nenhuma mensagem',
                'ultima_mensagem_tipo': ultima_mensagem.tipo if ultima_mensagem else 'texto',
                'ultima_mensagem_data': ultima_mensagem.data_envio if ultima_mensagem else chat.data_criacao,
                'mensagens_nao_lidas': mensagens_nao_lidas
            })

        chat_id = request.GET.get('chat')
        chat_ativo = None
        mensagens_ativas = []
        chat_ativo_info = None
        
        if chat_id:
            try:
                chat_ativo = Chat.objects.get(id=chat_id, participantes=request.user)
                mensagens_ativas = chat_ativo.mensagens_chat.all().order_by('data_envio')

                if chat_ativo:
                    chat_ativo.mensagens_chat.filter(
                        lida=False
                    ).exclude(
                        remetente=request.user
                    ).update(lida=True)
                    
                    outro_usuario_ativo = chat_ativo.participantes.exclude(id=request.user.id).first()
                    
                    nome_usuario_ativo = "Usuário"
                    if outro_usuario_ativo:
                        if outro_usuario_ativo.first_name and outro_usuario_ativo.last_name:
                            nome_usuario_ativo = f"{outro_usuario_ativo.first_name} {outro_usuario_ativo.last_name}"
                        elif outro_usuario_ativo.first_name:
                            nome_usuario_ativo = outro_usuario_ativo.first_name
                        elif outro_usuario_ativo.username:
                            nome_usuario_ativo = outro_usuario_ativo.username
                        elif outro_usuario_ativo.email:
                            nome_usuario_ativo = outro_usuario_ativo.email.split('@')[0]
                    
                    chat_ativo_info = {
                        'id': chat_ativo.id,
                        'outro_usuario': outro_usuario_ativo,
                        'outro_usuario_nome': nome_usuario_ativo, 
                        'mensagens_nao_lidas': 0
                    }
                
            except Chat.DoesNotExist:
                messages.error(request, "Conversa não encontrada.")

        context = {
            'chats': chats_com_info,
            'chat_ativo': chat_ativo_info,
            'mensagens': mensagens_ativas,
            'unread_messages': sum(chat['mensagens_nao_lidas'] for chat in chats_com_info),
        }
        return render(request, 'mensagens.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, "Erro ao carregar mensagens.")
        return render(request, '500.html', status=500)
    
@login_required
def favorites_view(request):
    """View para listar favoritos do usuário"""
    try:
        favoritos = Favorito.objects.filter(
            usuario=request.user
        ).select_related('servico', 'servico__categoria', 'servico__usuario')
        
        context = {
            'favoritos': favoritos,
        }
        return render(request, 'favoritos.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '500.html', status=500)

@login_required
def history_view(request):
    """View CORRIGIDA para histórico - com campos corretos do modelo"""
    try:
        historico_list = HistoricoBusca.objects.filter(
            usuario=request.user
        ).select_related(
            'usuario', 'content_type', 'localizacao', 'categoria_ct' 
        ).order_by('-data_busca')
        
        total_historico = historico_list.count()
        search_count = historico_list.filter(tipo='search').count()
        view_count = historico_list.filter(tipo='view').count()
        favorite_count = historico_list.filter(tipo='favorite').count()
        message_count = historico_list.filter(tipo='message').count()
        
        print(f"📊 Histórico - Total: {total_historico}, Buscas: {search_count}, Views: {view_count}, Favoritos: {favorite_count}")
        
        historico_processado = []
        for item in historico_list:
            try:
                titulo_item = item.get_titulo_item()
                url_item = item.get_url_item()
                
                historico_processado.append({
                    'item': item,
                    'titulo_item': titulo_item,
                    'url_item': url_item,
                    'tem_detalhes': bool(url_item and url_item != '#')
                })
            except Exception as e:
                print(f"⚠️ Erro ao processar item {item.id}: {e}")
                historico_processado.append({
                    'item': item,
                    'titulo_item': 'Item não disponível',
                    'url_item': '#',
                    'tem_detalhes': False
                })
        
        paginator = Paginator(historico_list, 15)  
        page = request.GET.get('page', 1)
        
        try:
            historico_paginado = paginator.page(page)
        except PageNotAnInteger:
            historico_paginado = paginator.page(1)
        except EmptyPage:
            historico_paginado = paginator.page(paginator.num_pages)
        
        historico_pagina_processado = []
        for item in historico_paginado:
            try:
                titulo_item = item.get_titulo_item()
                url_item = item.get_url_item()
                
                historico_pagina_processado.append({
                    'item': item,
                    'titulo_item': titulo_item,
                    'url_item': url_item,
                    'tem_detalhes': bool(url_item and url_item != '#')
                })
            except Exception as e:
                print(f"⚠️ Erro ao processar item {item.id}: {e}")
                historico_pagina_processado.append({
                    'item': item,
                    'titulo_item': 'Item não disponível',
                    'url_item': '#',
                    'tem_detalhes': False
                })
        
        context = {
            'historico': historico_paginado,  
            'historico_processado': historico_pagina_processado,  
            'total_historico': total_historico,
            'search_count': search_count,
            'view_count': view_count,
            'favorite_count': favorite_count,
            'message_count': message_count,
        }
        
        return render(request, 'historico.html', context)
    
    except Exception as e:
        print(f"🔥 ERRO no histórico: {str(e)}")
        if settings.DEBUG:
            raise e
        messages.error(request, 'Erro ao carregar histórico.')
        return render(request, 'historico.html', {
            'historico': [],
            'historico_processado': [],
            'total_historico': 0,
            'search_count': 0,
            'view_count': 0,
            'favorite_count': 0,
            'message_count': 0,
        })

@login_required
def filter_history_view(request, filter_type):
    """View para filtrar histórico por tipo - CORRIGIDA"""
    try:
        # Validar o tipo de filtro
        valid_filters = ['all', 'search', 'view', 'favorite', 'message']
        if filter_type not in valid_filters:
            filter_type = 'all'
        
        if filter_type == 'all':
            historico_list = HistoricoBusca.objects.filter(usuario=request.user)
        else:
            historico_list = HistoricoBusca.objects.filter(
                usuario=request.user, 
                tipo=filter_type
            )
        
        historico_list = historico_list.select_related(
            'usuario', 'localizacao', 'categoria_ct'
        ).prefetch_related(
            'content_type'
        ).order_by('-data_busca')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.utils.timesince import timesince
            from django.utils.timezone import now
            
            historico_data = []
            for item in historico_list[:50]:  
                item_titulo = ''
                item_url = ''
                item_obj = item.get_item_relacionado()
                
                if item_obj:
                    if hasattr(item_obj, 'titulo'):
                        item_titulo = item_obj.titulo
                    if hasattr(item_obj, 'get_absolute_url'):
                        item_url = item_obj.get_absolute_url()
                    elif hasattr(item_obj, 'id'):
                        if item.content_type.model == 'servico':
                            item_url = f'/servico/{item_obj.id}/'
                        elif item.content_type.model == 'anuncio':
                            item_url = f'/anuncio/{item_obj.id}/'
                
                historico_data.append({
                    'id': item.id,
                    'tipo': item.tipo,
                    'tipo_display': item.get_tipo_display(),
                    'termo': item.termo,
                    'item_titulo': item_titulo,
                    'item_url': item_url,
                    'categoria_titulo': item.categoria.titulo if item.categoria else None,
                    'data_busca': item.data_busca.strftime('%d/%m/%Y %H:%M'),
                    'data_busca_iso': item.data_busca.isoformat(),
                    'time_ago': timesince(item.data_busca, now()),
                })
            
            return JsonResponse({
                'success': True,
                'historico': historico_data,
                'count': historico_list.count()
            })
        
        request.session['history_filter'] = filter_type
        return redirect('history-view')
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
        messages.error(request, f'Erro ao filtrar histórico: {str(e)}')
        return redirect('history-view')

@login_required
@require_http_methods(["POST"])
def clear_history_view(request):
    """View para limpar todo o histórico do usuário"""
    try:
        count = HistoricoBusca.objects.filter(usuario=request.user).count()
        HistoricoBusca.objects.filter(usuario=request.user).delete()
        
        messages.success(request, f'Histórico limpo com sucesso! {count} itens removidos.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Histórico limpo! {count} itens removidos.',
                'count': count
            })
            
        return redirect('history-view')
        
    except Exception as e:
        error_msg = f'Erro ao limpar histórico: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
            
        messages.error(request, error_msg)
        return redirect('history-view')

@login_required
@require_http_methods(["POST"])
def export_history_view(request):
    """View para exportar histórico em CSV"""
    try:
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        historico = HistoricoBusca.objects.filter(
            usuario=request.user
        ).select_related('localizacao', 'categoria_ct').order_by('-data_busca')
        
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="historico_agenda_ai_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Data', 'Tipo', 'Descrição', 'Detalhes', 'Localização'])
        
        for item in historico:
            if item.tipo == 'search':
                descricao = f'Busca: "{item.termo}"'
                detalhes = f"Categoria: {item.categoria.titulo if item.categoria else 'Todas'}"
            elif item.tipo == 'view':
                descricao = f'Visualização: {item.get_titulo_item()}'
                detalhes = "Item visualizado"
            elif item.tipo == 'favorite':
                descricao = f'Favorito: {item.get_titulo_item()}'
                detalhes = "Item favoritado"
            elif item.tipo == 'message':
                descricao = f'Mensagem enviada'
                detalhes = "Mensagem no sistema"
            else:
                descricao = 'Atividade'
                detalhes = ''
            
            writer.writerow([
                item.data_busca.strftime('%d/%m/%Y %H:%M'),
                item.get_tipo_display(),
                descricao,
                detalhes,
                item.localizacao.nome if item.localizacao else ''
            ])
        
        return response
        
    except Exception as e:
        error_msg = f'Erro ao exportar histórico: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
            
        messages.error(request, error_msg)
        return redirect('history-view')

@login_required
@require_http_methods(["POST"])
def remove_history_item_view(request, item_id):
    """View para remover um item específico do histórico"""
    try:
        item = get_object_or_404(HistoricoBusca, pk=item_id, usuario=request.user)
        item.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Item removido do histórico!',
                'item_id': item_id
            })
            
        messages.success(request, 'Item removido do histórico!')
        return redirect('history-view')
        
    except Exception as e:
        error_msg = f'Erro ao remover item: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg}, status=500)
            
        messages.error(request, error_msg)
        return redirect('history-view')

class HistoricoAPIView(APIView):
    """API para histórico do usuário"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            filter_type = request.GET.get('filter', 'all')
            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 15))
            
            if filter_type == 'all':
                historico_list = HistoricoBusca.objects.filter(usuario=request.user)
            else:
                historico_list = HistoricoBusca.objects.filter(
                    usuario=request.user, 
                    tipo=filter_type
                )
            
            paginator = Paginator(historico_list, per_page)
            
            try:
                historico_page = paginator.page(page)
            except PageNotAnInteger:
                historico_page = paginator.page(1)
            except EmptyPage:
                historico_page = paginator.page(paginator.num_pages)
            
            from django.utils.timesince import timesince
            from django.utils.timezone import now
            
            historico_data = []
            for item in historico_page:
                historico_data.append({
                    'id': item.id,
                    'tipo': item.tipo,
                    'tipo_display': item.get_tipo_display(),
                    'termo': item.termo,
                    'item_titulo': item.get_titulo_item(),
                    'data_busca': item.data_busca.strftime('%d/%m/%Y %H:%M'),
                    'time_ago': timesince(item.data_busca, now()),
                })
            
            return Response({
                'success': True,
                'historico': historico_data,
                'pagination': {
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_items': paginator.count,
                    'has_previous': historico_page.has_previous(),
                    'has_next': historico_page.has_next(),
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_clear_history(request):
    """API para limpar histórico"""
    try:
        count = HistoricoBusca.objects.filter(usuario=request.user).count()
        HistoricoBusca.objects.filter(usuario=request.user).delete()
        
        return Response({
            'success': True,
            'message': f'Histórico limpo! {count} itens removidos.',
            'count': count
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
def settings_view(request):
    """View para configurações do usuário"""
    try:
        servicos_count = Servico.objects.filter(usuario=request.user).count()
        favoritos_count = Favorito.objects.filter(usuario=request.user).count()
        
        localizacoes = Localizacao.objects.all()
        
        try:
            configuracao = ConfiguracaoUsuario.objects.get(usuario=request.user)
        except ConfiguracaoUsuario.DoesNotExist:
            configuracao = ConfiguracaoUsuario.objects.create(usuario=request.user)
        
        context = {
            'usuario': request.user,
            'servicos_count': servicos_count,
            'favoritos_count': favoritos_count,
            'localizacoes': localizacoes,
            'configuracao': configuracao,
        }
        return render(request, 'configuracoes.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '500.html', status=500)

def categories_view(request):
    """View para listar todas as categorias"""
    try:
        categorias = Categoria.objects.filter(
            ativa=True
        ).annotate(
            num_servicos=Count('servicos', filter=Q(servicos__status='ativo'))
        ).order_by('titulo')
        
        context = {
            'categorias': categorias,
        }
        return render(request, 'categorias.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '500.html', status=500)

def category_view(request, slug):
    """View para listar serviços de uma categoria específica"""
    try:
        categoria = get_object_or_404(Categoria, slug=slug, ativa=True)
        servicos = Servico.objects.filter(
            categoria=categoria,
            status='ativo'
        ).select_related('usuario', 'localizacao').prefetch_related(
            Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
        ).order_by('-data_criacao')
        
        context = {
            'categoria': categoria,
            'servicos': servicos,
        }
        return render(request, 'categoria.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '404.html', status=404)

def featured_ads_view(request):
    """View para listar todos os anúncios em destaque"""
    try:
        servicos = Servico.objects.filter(
            destaque=True,
            status='ativo'
        ).select_related('categoria', 'usuario', 'localizacao').prefetch_related(
            Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
        ).order_by('-data_criacao')
        
        context = {
            'servicos': servicos,
            'anuncios_destaque': servicos,
        }
        return render(request, 'destaques.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '500.html', status=500)

def recent_ads_view(request):
    """View para listar todos os anúncios recentes"""
    try:
        servicos = Servico.objects.filter(
            status='ativo'
        ).select_related('categoria', 'usuario', 'localizacao').prefetch_related(
            Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
        ).order_by('-data_criacao')
        
        context = {
            'servicos': servicos,
            'anuncios_recentes': servicos,
        }
        return render(request, 'recentes.html', context)
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '500.html', status=500)
@login_required
def create_ad_view(request):
    """View para criação de novo anúncio com validação completa"""
    try:
        categorias = Categoria.objects.filter(ativa=True)
        localizacoes = Localizacao.objects.all()
        
        if request.method == 'POST':
            print("DEBUG: POST request recebido para criar anúncio")
            
            titulo = request.POST.get('titulo', '').strip()
            descricao = request.POST.get('descricao', '').strip()
            categoria_id = request.POST.get('categoria')
            valor_input = request.POST.get('valor', '').strip()
            localizacao_id = request.POST.get('localizacao')
            whatsapp_input = request.POST.get('whatsapp', '').strip()
            
            form_data = {
                'titulo': titulo,
                'descricao': descricao,
                'categoria': categoria_id,
                'valor': valor_input,
                'localizacao': localizacao_id,
                'whatsapp': whatsapp_input,
            }
            
            errors = []
            
            if not titulo:
                errors.append('O título é obrigatório.')
            elif len(titulo) < 10:
                errors.append('O título deve ter pelo menos 10 caracteres.')
            elif len(titulo) > 200:
                errors.append('O título não pode ter mais de 200 caracteres.')

            if not descricao:
                errors.append('A descrição é obrigatória.')
            elif len(descricao) < 20:
                errors.append('A descrição deve ter pelo menos 20 caracteres.')
            elif len(descricao) > 2000:
                errors.append('A descrição não pode ter mais de 2000 caracteres.')
            

            if not categoria_id:
                errors.append('Selecione uma categoria.')
            else:
                try:
                    categoria = Categoria.objects.get(id=categoria_id, ativa=True)
                except Categoria.DoesNotExist:
                    errors.append('Categoria selecionada não existe ou está inativa.')
            

            if not localizacao_id:
                errors.append('Selecione uma localização.')
            else:
                try:
                    localizacao = Localizacao.objects.get(id=localizacao_id)
                except Localizacao.DoesNotExist:
                    errors.append('Localização selecionada não existe.')
            

            whatsapp_clean = ''
            if not whatsapp_input:
                errors.append('WhatsApp é obrigatório.')
            else:

                whatsapp_clean = ''.join(filter(str.isdigit, whatsapp_input))
                
                if len(whatsapp_clean) < 10:
                    errors.append('WhatsApp deve ter pelo menos 10 dígitos.')
                elif len(whatsapp_clean) > 11:
                    errors.append('WhatsApp deve ter no máximo 11 dígitos.')
            

            valor_final = 0.00
            if valor_input:
                try:

                    valor_limpo = ''.join(c for c in valor_input if c.isdigit() or c == '.')
                    
                    if valor_limpo and any(c.isdigit() for c in valor_limpo):

                        if valor_limpo.count('.') > 1:
                            partes = valor_limpo.split('.')
                            valor_limpo = partes[0] + '.' + ''.join(partes[1:])
                        
                        valor_final = float(valor_limpo)
                        
                        if valor_final < 0:
                            errors.append('O valor não pode ser negativo.')
                        elif valor_final > 9999999.99:
                            errors.append('Valor muito alto. Máximo permitido: R$ 9.999.999,99')
                except (ValueError, TypeError):
                    errors.append('Valor do preço inválido. Use apenas números.')
            
            imagens = request.FILES.getlist('imagens')
            if not imagens:
                errors.append('Pelo menos uma imagem é obrigatória.')
            elif len(imagens) > 10:
                errors.append('Máximo de 10 imagens permitidas.')
            

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'criar_anuncio.html', {
                    'categorias': categorias,
                    'localizacoes': localizacoes,
                    'form_data': form_data
                })
            
            try:
                anuncio = Anuncio(
                    titulo=titulo,
                    descricao=descricao,
                    categoria=categoria,
                    valor=valor_final,
                    usuario=request.user,
                    localizacao=localizacao,
                    whatsapp=whatsapp_clean,  
                    status='ativo'
                )
                

                anuncio.full_clean()
                anuncio.save()
                print(f"DEBUG: Anúncio criado com ID: {anuncio.id}")
                

                for i, imagem_file in enumerate(imagens):
                    if i < 10:  
                        try:

                            if not imagem_file.content_type.startswith('image/'):
                                raise ValidationError('Arquivo não é uma imagem válida.')
                            
                            if imagem_file.size > 5 * 1024 * 1024:  
                                raise ValidationError('Imagem muito grande. Máximo: 5MB')
                            
                            imagem = Imagem(
                                anuncio=anuncio,
                                imagem=imagem_file,
                                capa=(i == 0)  
                            )
                            imagem.full_clean()
                            imagem.save()
                            print(f"DEBUG: Imagem {i+1} salva: {imagem_file.name}")
                            
                        except ValidationError as e:
                            print(f"DEBUG: Erro na imagem {i+1}: {str(e)}")
                            messages.warning(request, f'Erro na imagem {i+1}: {str(e)}')
                        except Exception as e:
                            print(f"DEBUG: Erro ao salvar imagem {i+1}: {str(e)}")
                            messages.warning(request, f'Erro ao processar imagem {i+1}')
                
             
                from django.urls import reverse
                Notificacao.objects.create(
                    usuario=request.user,
                    titulo='Anúncio publicado com sucesso! 🎉',
                    mensagem=f'Seu anúncio "{titulo}" foi publicado e já está ativo. '
                            f'Os clientes podem visualizá-lo agora mesmo.',
                    tipo='success',
                    lida=False,
                    url=reverse('anuncio-detail', kwargs={'anuncio_id': anuncio.id})
                )
                
        
                destaque = request.POST.get('destaque')
                if destaque == 'true':
                    Notificacao.objects.create(
                        usuario=request.user,
                        titulo='Anúncio em destaque! ⭐',
                        mensagem=f'Seu anúncio "{titulo}" está em posição de destaque por 7 dias. '
                                f'Isso aumentará sua visibilidade para os clientes.',
                        tipo='alert',
                        lida=False,
                        url=reverse('my-ads')
                    )
                
                print(f"DEBUG: Notificações criadas para usuário {request.user.email} sobre anúncio {titulo}")
                
                messages.success(request, 'Anúncio criado com sucesso!')
                return redirect('my-ads')
                
            except ValidationError as e:
             
                for field, field_errors in e.message_dict.items():
                    for error in field_errors:
                        messages.error(request, f"{field}: {error}")
            except Exception as e:
                print(f"DEBUG: Erro ao criar anúncio: {str(e)}")
                messages.error(request, f'Erro ao criar anúncio: {str(e)}')
        
        context = {
            'categorias': categorias,
            'localizacoes': localizacoes,
            'form_data': {}
        }
        return render(request, 'criar_anuncio.html', context)
    
    except Exception as e:
        print(f"DEBUG: Erro na view create_ad_view: {str(e)}")
        if settings.DEBUG:
            raise e
        messages.error(request, 'Erro interno do servidor. Tente novamente.')
        return redirect('home')

@login_required
@require_http_methods(["POST"])
def remover_imagem_view(request, imagem_id):
    """View para remover imagem de anúncio"""
    try:
        imagem = get_object_or_404(Imagem, pk=imagem_id)
        
        if imagem.anuncio.usuario != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para remover esta imagem.'
            }, status=403)
        
        if imagem.capa:
            outras_imagens = Imagem.objects.filter(
                anuncio=imagem.anuncio
            ).exclude(pk=imagem_id)
            
            if outras_imagens.exists():
                nova_capa = outras_imagens.first()
                nova_capa.capa = True
                nova_capa.save()
        
        imagem.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Imagem removida com sucesso!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao remover imagem: {str(e)}'
        }, status=500)

@login_required
def edit_ad_view(request, anuncio_id):
    """View COMPLETA para editar anúncio existente"""
    try:
        anuncio = get_object_or_404(Anuncio, pk=anuncio_id, usuario=request.user)
        categorias = Categoria.objects.filter(ativa=True)
        localizacoes = Localizacao.objects.all()
        
        if request.method == 'POST':
            print(f"DEBUG: POST request para editar anúncio {anuncio_id}")
            
            titulo = request.POST.get('titulo', '').strip()
            descricao = request.POST.get('descricao', '').strip()
            categoria_id = request.POST.get('categoria')
            valor_input = request.POST.get('valor', '').strip()
            localizacao_id = request.POST.get('localizacao')
            whatsapp_input = request.POST.get('whatsapp', '').strip()
            estado_produto = request.POST.get('estado_produto', 'usado')
            status = request.POST.get('status', 'ativo')
            destaque = request.POST.get('destaque') == 'on'
            
            errors = []
            

            if not titulo:
                errors.append('O título é obrigatório.')
            elif len(titulo) < 10:
                errors.append('O título deve ter pelo menos 10 caracteres.')
            elif len(titulo) > 200:
                errors.append('O título não pode ter mais de 200 caracteres.')
            

            if not descricao:
                errors.append('A descrição é obrigatória.')
            elif len(descricao) < 20:
                errors.append('A descrição deve ter pelo menos 20 caracteres.')
            elif len(descricao) > 2000:
                errors.append('A descrição não pode ter mais de 2000 caracteres.')
    
            if not categoria_id:
                errors.append('Selecione uma categoria.')
            else:
                try:
                    categoria = Categoria.objects.get(id=categoria_id, ativa=True)
                except Categoria.DoesNotExist:
                    errors.append('Categoria selecionada não existe ou está inativa.')
            

            if not localizacao_id:
                errors.append('Selecione uma localização.')
            else:
                try:
                    localizacao = Localizacao.objects.get(id=localizacao_id)
                except Localizacao.DoesNotExist:
                    errors.append('Localização selecionada não existe.')

            whatsapp_clean = ''
            if not whatsapp_input:
                errors.append('WhatsApp é obrigatório.')
            else:
                whatsapp_clean = ''.join(filter(str.isdigit, whatsapp_input))
                if len(whatsapp_clean) < 10:
                    errors.append('WhatsApp deve ter pelo menos 10 dígitos.')
                elif len(whatsapp_clean) > 11:
                    errors.append('WhatsApp deve ter no máximo 11 dígitos.')

            valor_final = 0.00
            if valor_input:
                try:
                    valor_limpo = ''.join(c for c in valor_input if c.isdigit() or c in ['.', ','])
                    if ',' in valor_limpo:
                        valor_limpo = valor_limpo.replace(',', '.')
                    
                    if valor_limpo and any(c.isdigit() for c in valor_limpo):
                        if valor_limpo.count('.') > 1:
                            partes = valor_limpo.split('.')
                            valor_limpo = partes[0] + '.' + ''.join(partes[1:])
                        
                        valor_final = float(valor_limpo)
                        
                        if valor_final < 0:
                            errors.append('O valor não pode ser negativo.')
                        elif valor_final > 9999999.99:
                            errors.append('Valor muito alto. Máximo permitido: R$ 9.999.999,99')
                except (ValueError, TypeError):
                    errors.append('Valor do preço inválido. Use apenas números.')
            

            novas_imagens = request.FILES.getlist('imagens')
            if novas_imagens and len(novas_imagens) > 10:
                errors.append('Máximo de 10 imagens permitidas.')
            
      
            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'editar_anuncio.html', {
                    'anuncio': anuncio,
                    'categorias': categorias,
                    'localizacoes': localizacoes,
                })
            
            try:
                anuncio.titulo = titulo
                anuncio.descricao = descricao
                anuncio.categoria = categoria
                anuncio.valor = valor_final if valor_final > 0 else None
                anuncio.localizacao = localizacao
                anuncio.whatsapp = whatsapp_clean
                anuncio.estado_produto = estado_produto
                anuncio.status = status
                anuncio.destaque = destaque
                
                anuncio.full_clean()
                anuncio.save()
                print(f"DEBUG: Anúncio {anuncio_id} atualizado com sucesso")
                
                if novas_imagens:
                    for i, imagem_file in enumerate(novas_imagens):
                        if i < 10:  # Limite de 10 imagens
                            try:
                                if not imagem_file.content_type.startswith('image/'):
                                    raise ValidationError('Arquivo não é uma imagem válida.')
                                
                                if imagem_file.size > 5 * 1024 * 1024:  # 5MB
                                    raise ValidationError('Imagem muito grande. Máximo: 5MB')
                                
                                tem_capa = anuncio.imagens.filter(capa=True).exists()
                                
                                imagem = Imagem(
                                    anuncio=anuncio,
                                    imagem=imagem_file,
                                    capa=not tem_capa  
                                )
                                imagem.full_clean()
                                imagem.save()
                                print(f"DEBUG: Nova imagem {i+1} adicionada: {imagem_file.name}")
                                
                            except ValidationError as e:
                                print(f"DEBUG: Erro na nova imagem {i+1}: {str(e)}")
                                messages.warning(request, f'Erro na nova imagem {i+1}: {str(e)}')
                            except Exception as e:
                                print(f"DEBUG: Erro ao salvar nova imagem {i+1}: {str(e)}")
                                messages.warning(request, f'Erro ao processar nova imagem {i+1}')
                
                messages.success(request, 'Anúncio atualizado com sucesso!')
                return redirect('my-ads')
                
            except ValidationError as e:
                for field, field_errors in e.message_dict.items():
                    for error in field_errors:
                        messages.error(request, f"{field}: {error}")
            except Exception as e:
                print(f"DEBUG: Erro ao atualizar anúncio: {str(e)}")
                messages.error(request, f'Erro ao atualizar anúncio: {str(e)}')

        context = {
            'anuncio': anuncio,
            'categorias': categorias,
            'localizacoes': localizacoes,
        }
        return render(request, 'editar_anuncio.html', context)
    
    except Anuncio.DoesNotExist:
        messages.error(request, 'Anúncio não encontrado ou você não tem permissão para editá-lo.')
        return redirect('my-ads')
    except Exception as e:
        print(f"DEBUG: Erro na view edit_ad_view: {str(e)}")
        if settings.DEBUG:
            raise e
        messages.error(request, 'Erro interno do servidor. Tente novamente.')
        return redirect('my-ads')

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
        print("📝 [DJANGO-REGISTRO] Recebendo dados:", request.data)
        
        try:
            data = request.data.copy()
            
            data['first_name'] = data.get('nome', '')
            data['password2'] = data.get('confirmPassword', '')
            data['termos_aceitos'] = True
            
            print("🔄 [DJANGO-REGISTRO] Dados adaptados:", {
                'first_name': data.get('first_name'),
                'email': data.get('email'),
                'telefone': data.get('telefone'),
                'password': '***',
                'password2': '***'
            })
            
            serializer = UsuarioRegistroSerializer(data=data)
            
            if serializer.is_valid():
                print("✅ [DJANGO-REGISTRO] Dados válidos, criando usuário...")
                user = serializer.save()
                
                refresh = RefreshToken.for_user(user)
                
                user_data = {
                    'id': user.id,
                    'nome': user.first_name or user.email.split('@')[0],
                    'email': user.email,
                    'telefone': user.telefone,
                    'data_criacao': user.date_joined.isoformat(),
                }
                
                print(f"🎉 [DJANGO-REGISTRO] Usuário criado: {user.email}")
                
                return Response({
                    'user': user_data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'Conta criada com sucesso!'
                }, status=status.HTTP_201_CREATED)
            else:
                print(f"❌ [DJANGO-REGISTRO] Erros de validação: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            print(f"💥 [DJANGO-REGISTRO] Erro interno: {str(e)}")
            return Response(
                {'error': 'Erro interno no servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LoginAPIView(APIView):
    """API para autenticação de usuários - VERSÃO CORRIGIDA"""
    permission_classes = [AllowAny]

    def post(self, request):
        print("🔐 [DJANGO-LOGIN] Iniciando processo de login...")
        
        serializer = UsuarioLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            user_data = {
                'id': user.id,
                'nome': user.first_name or user.email.split('@')[0],
                'email': user.email,
                'telefone': user.telefone,
                'data_criacao': user.date_joined.isoformat(),
            }
            
            print(f"✅ [DJANGO-LOGIN] Login bem-sucedido: {user.email}")
            
            return Response({
                'user': user_data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        
        print(f"❌ [DJANGO-LOGIN] Erros: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

class ServicoListAPIView(ListAPIView):
    """API para listagem de serviços com filtros"""
    serializer_class = ServicoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Servico.objects.filter(
            status='ativo'
        ).select_related('usuario', 'categoria', 'localizacao')
        
        categoria = self.request.query_params.get('categoria')
        if categoria:
            queryset = queryset.filter(categoria__slug=categoria)
            
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(titulo__icontains=search) |
                Q(descricao__icontains=search)
            )
            
        return queryset.order_by('-data_criacao')

class CategoriaListAPIView(ListAPIView):
    """API para listagem de categorias"""
    queryset = Categoria.objects.filter(ativa=True)
    serializer_class = CategoriaSerializer
    permission_classes = [AllowAny]

class NotificacaoListAPIView(ListAPIView):
    """API para listagem de notificações"""
    serializer_class = NotificacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notificacao.objects.filter(
            usuario=self.request.user
        ).order_by('-data_criacao')

class FavoritoListCreateDestroyView(APIView):
    """API para gerenciamento de favoritos"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favoritos = Favorito.objects.filter(
            usuario=request.user
        ).select_related('servico', 'servico__categoria')
        
        serializer = FavoritoSerializer(favoritos, many=True)
        return Response(serializer.data)

    def post(self, request):
        servico_id = request.data.get('servico_id')
        if not servico_id:
            return Response(
                {"error": "servico_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        servico = get_object_or_404(Servico, pk=servico_id)
        
        favorito, created = Favorito.objects.get_or_create(
            usuario=request.user,
            servico=servico
        )
        
        if created:
            return Response(
                {"status": "added"}, 
                status=status.HTTP_201_CREATED
            )
        else:
            favorito.delete()
            return Response({"status": "removed"})

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

class MensagemAPIView(APIView):
    """API para mensagens entre usuários"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversas = Mensagem.objects.filter(
            Q(remetente=request.user) | Q(destinatario=request.user)
        ).order_by('-data_envio').distinct('conversa_id')
        
        serializer = MensagemSerializer(conversas, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Enviar nova mensagem"""
        serializer = MensagemSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ConversaAPIView(APIView):
    """API para uma conversa específica"""
    permission_classes = [IsAuthenticated]

    def get(self, request, conversa_id):
        mensagens = Mensagem.objects.filter(
            conversa_id=conversa_id
        ).filter(
            Q(remetente=request.user) | Q(destinatario=request.user)
        ).order_by('data_envio')
        
        serializer = MensagemSerializer(mensagens, many=True)
        return Response(serializer.data)

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

from django.contrib.contenttypes.models import ContentType
from produtos.models import Anuncio  

@require_http_methods(["POST"])
@login_required
def toggle_favorito_view(request, anuncio_id):
    """View para toggle favorito com salvamento no histórico"""
    try:
        from django.contrib.contenttypes.models import ContentType
        
        anuncio = get_object_or_404(Anuncio, pk=anuncio_id)
        anuncio_content_type = ContentType.objects.get_for_model(Anuncio)
        
        favorito_existente = Favorito.objects.filter(
            usuario=request.user,
            content_type=anuncio_content_type,
            object_id=anuncio.id
        ).first()
        
        if favorito_existente:
            favorito_existente.delete()
            favoritado = False
            action = "removed"
            message = "Anúncio removido dos favoritos"
        else:
            Favorito.objects.create(
                usuario=request.user,
                content_type=anuncio_content_type,
                object_id=anuncio.id
            )
            favoritado = True
            action = "added"
            message = "Anúncio adicionado aos favoritos!"
            
            HistoricoBusca.objects.create(
                usuario=request.user,
                termo=f"Favorito: {anuncio.titulo}",
                tipo='favorite',
                content_type=anuncio_content_type,
                object_id=anuncio.id
            )
        
        total_favoritos = Favorito.objects.filter(usuario=request.user).count()
        
        return JsonResponse({
            'status': 'success', 
            'action': action,
            'favoritado': favoritado,
            'message': message,
            'total_favoritos': total_favoritos,
            'anuncio_id': anuncio_id,
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro: {str(e)}'
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Endpoint simples para verificar saúde da aplicação"""
    return Response({"status": "healthy"})

@login_required
def atualizar_perfil(request):
    """View para atualizar o perfil do usuário"""
    if request.method == 'POST':
        try:
            usuario = request.user
            
            usuario.nome = request.POST.get('nome', usuario.nome)
            usuario.nome_utilizador = request.POST.get('nome_utilizador', usuario.nome_utilizador)
            usuario.telefone = request.POST.get('telefone', usuario.telefone)
            
            data_nascimento = request.POST.get('data_nascimento')
            if data_nascimento:
                usuario.data_nascimento = data_nascimento
            
            localizacao_id = request.POST.get('localizacao')
            if localizacao_id:
                try:
                    localizacao = Localizacao.objects.get(id=localizacao_id)
                    usuario.localizacao = localizacao
                except Localizacao.DoesNotExist:
                    pass
            
            usuario.save()
            
            return JsonResponse({'success': True, 'message': 'Perfil atualizado com sucesso!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
def upload_foto_perfil(request):
    """View para upload de foto de perfil"""
    if request.method == 'POST' and request.FILES.get('foto_perfil'):
        try:
            usuario = request.user
            usuario.foto_perfil = request.FILES['foto_perfil']
            usuario.save()
            
            return JsonResponse({
                'success': True, 
                'foto_url': usuario.foto_perfil.url,
                'message': 'Foto de perfil atualizada com sucesso!'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Nenhuma imagem enviada'})

@login_required
def alterar_senha(request):
    """View para alterar a senha do usuário"""
    if request.method == 'POST':
        try:
            usuario = request.user
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not usuario.check_password(current_password):
                return JsonResponse({'success': False, 'error': 'Senha atual incorreta'})
            
            if new_password != confirm_password:
                return JsonResponse({'success': False, 'error': 'As novas senhas não coincidem'})
            
            if len(new_password) < 6:
                return JsonResponse({'success': False, 'error': 'A senha deve ter pelo menos 6 caracteres'})
            
            usuario.set_password(new_password)
            usuario.save()
            
            update_session_auth_hash(request, usuario)
            
            return JsonResponse({'success': True, 'message': 'Senha alterada com sucesso!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

@login_required
def atualizar_configuracoes(request):
    """View para atualizar configurações do usuário"""
    if request.method == 'POST':
        try:
            usuario = request.user
            
            configuracao, created = ConfiguracaoUsuario.objects.get_or_create(usuario=usuario)
            
            configuracao.receber_email = request.POST.get('receber_email', 'true') == 'true'
            configuracao.modo_escuro = request.POST.get('modo_escuro', 'false') == 'true'
            configuracao.notificacoes_push = request.POST.get('notificacoes_push', 'true') == 'true'
            configuracao.mostrar_localizacao = request.POST.get('mostrar_localizacao', 'true') == 'true'
            configuracao.idioma = request.POST.get('idioma', 'pt-br')
            
            configuracao.save()
            
            return JsonResponse({'success': True, 'message': 'Configurações atualizadas com sucesso!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'})

def help_view(request):
    """View para página de ajuda"""
    try:
        return render(request, 'ajuda.html')
    except Exception as e:
        if settings.DEBUG:
            raise e
        return render(request, '500.html', status=500)

class NotificacaoAPIView(APIView):
    """API View para notificações"""
    
    def get(self, request):
        try:
            notificacoes = Notificacao.objects.filter(
                usuario=request.user
            ).order_by('-data_criacao')
            
            serializer = NotificacaoSerializer(notificacoes, many=True)
            
            return Response({
                'notificacoes': serializer.data,
                'total': notificacoes.count(),
                'unread': notificacoes.filter(lida=False).count()
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@login_required
def notifications_view(request):
    """View para listar notificações - retorna HTML sempre"""
    try:
        notificacoes = Notificacao.objects.filter(
            usuario=request.user
        ).order_by('-data_criacao')
        
        if notificacoes.filter(lida=False).exists():
            notificacoes.filter(lida=False).update(lida=True)
        
        context = {
            'notificacoes': notificacoes,
            'unread_notifications': 0,
        }
        
        try:
            from django.template.loader import get_template
            get_template('notificacoes.html')
            return render(request, 'notificacoes.html', context)
        except:
            notificacoes_data = []
            for notificacao in notificacoes:
                notificacoes_data.append({
                    'id': notificacao.id,
                    'mensagem': notificacao.mensagem,
                    'lida': notificacao.lida,
                    'data_criacao': notificacao.data_criacao.isoformat(),
                    'tipo': notificacao.tipo,
                })
            
            return JsonResponse({
                'notificacoes': notificacoes_data,
                'total': notificacoes.count(),
                'message': 'Template notificacoes.html não encontrado. Retornando JSON.',
                'status': 'success'
            })
    
    except Exception as e:
        if settings.DEBUG:
            raise e
        
        return JsonResponse({
            'error': 'Erro interno do servidor',
            'status': 'error'
        }, status=500)


@login_required
def favorites_view(request):
    """View CORRIGIDA para favoritos - AGORA FUNCIONANDO PERFEITAMENTE"""
    try:
        from django.contrib.contenttypes.models import ContentType
        from produtos.models import Anuncio
        
        anuncio_content_type = ContentType.objects.get_for_model(Anuncio)
        
        favoritos_list = Favorito.objects.filter(
            usuario=request.user,
            content_type=anuncio_content_type
        ).select_related('content_type').order_by('-data_criacao')
        
        paginator = Paginator(favoritos_list, 12)
        page = request.GET.get('page', 1)
        
        try:
            favoritos = paginator.page(page)
        except PageNotAnInteger:
            favoritos = paginator.page(1)
        except EmptyPage:
            favoritos = paginator.page(paginator.num_pages)
        
        favoritos_processados = []
        for favorito in favoritos:
            try:
                anuncio = favorito.content_object
                if anuncio and hasattr(anuncio, 'status') and anuncio.status in ['ativo', 'pendente']:
                    if hasattr(anuncio, 'imagens') and anuncio.imagens.exists():
                        imagem_capa = anuncio.imagens.filter(capa=True).first()
                        if imagem_capa:
                            anuncio.first_image = imagem_capa
                        else:
                            anuncio.first_image = anuncio.imagens.first()
                    else:
                        anuncio.first_image = None
                    
                    if hasattr(anuncio, 'valor') and anuncio.valor:
                        anuncio.valor_formatado = f"R$ {anuncio.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    else:
                        anuncio.valor_formatado = "A combinar"
                
                    anuncio.localizacao_str = "Localização não informada"
                    if hasattr(anuncio, 'localizacao') and anuncio.localizacao:
                        if hasattr(anuncio.localizacao, 'cidade') and hasattr(anuncio.localizacao, 'estado'):
                            anuncio.localizacao_str = f"{anuncio.localizacao.cidade}, {anuncio.localizacao.estado}"
                        elif hasattr(anuncio.localizacao, 'nome'):
                            anuncio.localizacao_str = anuncio.localizacao.nome
                    
                    anuncio.tipo = 'anuncio'
                    
                    favoritos_processados.append({
                        'favorito': favorito,
                        'item': anuncio
                    })
                    
            except Exception as e:
                print(f"❌ Erro ao processar favorito {favorito.id}: {str(e)}")
                continue
        
        context = {
            'favoritos_processados': favoritos_processados,
            'total_favoritos': favoritos_list.count(),
            'page_obj': favoritos,
        }
        
        return render(request, 'favoritos.html', context)
    
    except Exception as e:
        print(f"🔥 ERRO GRAVE na view de favoritos: {str(e)}")
        if settings.DEBUG:
            raise e
        messages.error(request, 'Erro ao carregar favoritos.')
        return render(request, 'favoritos.html', {
            'favoritos_processados': [],
            'total_favoritos': 0,
            'page_obj': None,
        })
    
@require_http_methods(["POST"])
@login_required
def remover_favorito_view(request, favorito_id):
    try:
        print(f"🔍 Tentando remover favorito ID: {favorito_id} para usuário: {request.user.id}")
        
        favorito = get_object_or_404(Favorito, pk=favorito_id, usuario=request.user)
        item_titulo = "Item"
        
        try:
            item = favorito.content_object
            if item and hasattr(item, 'titulo'):
                item_titulo = item.titulo
        except:
            pass
        
        favorito.delete()
        print(f"✅ Favorito {favorito_id} removido")
        
        total_favoritos = Favorito.objects.filter(usuario=request.user).count()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Favorito removido com sucesso!',
            'total_favoritos': total_favoritos,
            'favorito_id': favorito_id,
            'item_titulo': item_titulo
        })
        
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Erro ao remover favorito.'
        }, status=500)
    
class MeusFavoritosAPIView(APIView):
    """API para obter favoritos do usuário autenticado"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        favoritos = Favorito.objects.filter(
            usuario=request.user
        ).select_related('servico', 'servico__categoria', 'servico__usuario')
        
        favoritos_data = []
        for favorito in favoritos:
            servico = favorito.servico
            if servico:
                favoritos_data.append({
                    'id': favorito.id,
                    'servico_id': servico.id,
                    'titulo': servico.titulo,
                    'valor': servico.valor,
                    'categoria': servico.categoria.titulo if servico.categoria else '',
                    'data_criacao': favorito.data_criacao.isoformat()
                })
        
        return Response({
            'favoritos': favoritos_data,
            'total': len(favoritos_data)
        })
        
@login_required
def editar_anuncio_view(request, anuncio_id):
    """View para editar anúncio existente"""
    anuncio = get_object_or_404(Anuncio, pk=anuncio_id, usuario=request.user)
    
    if request.method == 'POST':
        pass
    
    categorias = Categoria.objects.filter(ativa=True)
    localizacoes = Localizacao.objects.all()
    
    context = {
        'anuncio': anuncio,
        'categorias': categorias,
        'localizacoes': localizacoes,
    }
    return render(request, 'editar_anuncio.html', context)

@login_required
@require_http_methods(["POST"])
def delete_anuncio_view(request, anuncio_id):
    """View para excluir anúncio - Versão Corrigida"""
    try:
        anuncio = get_object_or_404(Anuncio, pk=anuncio_id, usuario=request.user)
        
        print(f"DEBUG: Tentando excluir anúncio ID {anuncio_id}, Título: {anuncio.titulo}")
        
        anuncio.delete()
        
        print(f"DEBUG: Anúncio {anuncio_id} excluído com sucesso")
        
        messages.success(request, 'Anúncio excluído com sucesso!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Anúncio excluído com sucesso!',
                'anuncio_id': anuncio_id
            })
            
        return redirect('my-ads')
        
    except Anuncio.DoesNotExist:
        error_msg = 'Anúncio não encontrado ou você não tem permissão para excluí-lo'
        print(f"DEBUG: {error_msg}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=404)
            
        messages.error(request, error_msg)
        return redirect('my-ads')
        
    except Exception as e:
        error_msg = f'Erro ao excluir anúncio: {str(e)}'
        print(f"DEBUG: {error_msg}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=500)
            
        messages.error(request, error_msg)
        return redirect('my-ads')

@login_required
@require_http_methods(["POST"])
def toggle_status_view(request, anuncio_id):
    """View para alterar status do anúncio"""
    anuncio = get_object_or_404(Anuncio, pk=anuncio_id, usuario=request.user)
    novo_status = request.POST.get('novo_status')
    
    if novo_status in ['ativo', 'pendente', 'inativo']:
        anuncio.status = novo_status
        anuncio.save()
        messages.success(request, f'Status alterado para {novo_status.capitalize()}!')
    else:
        messages.error(request, 'Status inválido')
    
    return redirect('my-ads')

@login_required
@require_http_methods(["POST"])
def enviar_mensagem_view(request):
    """View para enviar mensagem através do sistema de conversas - COM HISTÓRICO"""
    try:
        logger.info(f"Iniciando envio de mensagem - User: {request.user.id}")
        
        destinatario_id = request.POST.get('destinatario_id')
        conversa_id = request.POST.get('conversa_id')
        mensagem_texto = request.POST.get('mensagem', '').strip()
        tipo = request.POST.get('tipo', 'texto')
        
        logger.info(f"Valores: destinatario_id={destinatario_id}, conversa_id={conversa_id}, "
                   f"mensagem='{mensagem_texto}', tipo={tipo}")
        
        if not destinatario_id and not conversa_id:
            logger.error("Nenhum destinatário ou conversa especificado")
            return JsonResponse({
                'success': False,
                'error': 'Destinatário ou conversa não especificado.'
            }, status=400)
        
        if not mensagem_texto and tipo == 'texto':
            logger.error("Mensagem vazia")
            return JsonResponse({
                'success': False,
                'error': 'A mensagem não pode estar vazia.'
            }, status=400)
        
        chat = None
        destinatario = None
        
 
        if conversa_id:
            try:
                logger.info(f"Buscando chat com ID: {conversa_id}")
                chat = Chat.objects.get(id=conversa_id)
                logger.info(f"Chat encontrado: {chat.id}")
                
             
                if request.user not in chat.participantes.all():
                    logger.error(f"Usuário {request.user.id} não é participante do chat {chat.id}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Você não tem acesso a esta conversa.'
                    }, status=403)
                
       
                destinatario = chat.participantes.exclude(id=request.user.id).first()
                
            except Chat.DoesNotExist:
                logger.warning(f"Chat não encontrado: {conversa_id}")
                chat = None
            except Exception as e:
                logger.error(f"Erro ao buscar chat: {e}")
                chat = None
        
   
        if not chat and destinatario_id:
            try:
                logger.info(f"Buscando destinatário: {destinatario_id}")
                destinatario = get_object_or_404(CustomUser, pk=destinatario_id)
                logger.info(f"Destinatário encontrado: {destinatario.id}")
         
                if request.user == destinatario:
                    logger.error("Tentativa de enviar mensagem para si mesmo")
                    return JsonResponse({
                        'success': False,
                        'error': 'Você não pode enviar mensagem para si mesmo.'
                    }, status=400)
                

                logger.info("Procurando chat existente entre usuários")
                chat = Chat.objects.filter(participantes=request.user) \
                                 .filter(participantes=destinatario) \
                                 .first()
                
                if chat:
                    logger.info(f"Chat existente encontrado: {chat.id}")
                else:
                    logger.info("Criando novo chat")
                    chat = Chat.objects.create()
                    chat.participantes.add(request.user, destinatario)
                    chat.save()
                    logger.info(f"Novo chat criado: {chat.id}")
                    
            except Exception as e:
                logger.error(f"Erro ao processar destinatário: {e}")
                return JsonResponse({
                    'success': False,
                    'error': 'Destinatário inválido.'
                }, status=400)
        
        if not chat:
            logger.error("Chat não pôde ser criado/encontrado")
            return JsonResponse({
                'success': False,
                'error': 'Não foi possível criar/encontrar a conversa.'
            }, status=400)
        
  
        if not destinatario:
            destinatario = chat.participantes.exclude(id=request.user.id).first()
        
    
        try:
            logger.info("Criando mensagem no banco de dados")
            mensagem = Mensagem.objects.create(
                chat=chat,
                remetente=request.user,
                conteudo=mensagem_texto,
                tipo=tipo
            )
            
    
            if 'arquivo' in request.FILES:
                arquivo = request.FILES['arquivo']
                mensagem.arquivo = arquivo
                mensagem.save()
                logger.info(f"Arquivo salvo: {arquivo.name}")
            
            logger.info(f"Mensagem criada com ID: {mensagem.id}")
            
   
            chat.ultima_mensagem = mensagem
            chat.save()
            logger.info("Última mensagem atualizada no chat")
            
        except Exception as e:
            logger.error(f"Erro ao criar mensagem: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Erro ao salvar mensagem.'
            }, status=500)
        
   
        try:
            logger.info(f"Salvando mensagem no histórico - User: {request.user.id}")
            
  
            nome_destinatario = destinatario.get_full_name() or destinatario.username or destinatario.email
   
            historico_mensagem = HistoricoBusca.objects.create(
                usuario=request.user,
                termo=f"Mensagem para {nome_destinatario}",
                tipo='message',
                content_type=ContentType.objects.get_for_model(Mensagem),
                object_id=mensagem.id
            )
            
            logger.info(f"✅ Histórico de mensagem salvo: ID {historico_mensagem.id}")
            
        except Exception as e:
            logger.error(f"⚠️ Erro ao salvar mensagem no histórico: {str(e)}")
    
        try:
            if destinatario:
                logger.info(f"Criando notificação para destinatário: {destinatario.id}")
                Notificacao.objects.create(
                    usuario=destinatario,
                    titulo='Nova mensagem recebida',
                    mensagem=f'{request.user.get_full_name() or request.user.username} enviou uma mensagem para você',
                    tipo='mensagem',
                    url=reverse('messages-view') + f'?chat={chat.id}'
                )
                logger.info("✅ Notificação criada com sucesso")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao criar notificação: {e}")
        
        logger.info("✅ Mensagem enviada com sucesso!")

        html_content = ""
        if mensagem.tipo == 'imagem' and mensagem.arquivo:
            html_content = f"""
                <div class="message sent">
                    <div class="message-content message-imagem">
                        <img src="{mensagem.arquivo.url}" alt="Imagem enviada" 
                             onclick="openImageModal('{mensagem.arquivo.url}')">
                    </div>
                    <div class="message-time">
                        {mensagem.data_envio.strftime("%H:%M")}
                        <span class="message-status">
                            <i class="fas fa-check"></i>
                        </span>
                    </div>
                </div>
            """
        elif mensagem.tipo == 'arquivo' and mensagem.arquivo:
            html_content = f"""
                <div class="message sent">
                    <div class="message-content message-arquivo">
                        <i class="fas fa-file-pdf"></i>
                        <div class="message-arquivo-info">
                            <div class="message-arquivo-nome">{mensagem.arquivo.name.split('/')[-1]}</div>
                            <div class="message-arquivo-tamanho">{mensagem.arquivo.size}</div>
                        </div>
                        <a href="{mensagem.arquivo.url}" download class="message-arquivo-download">
                            <i class="fas fa-download"></i>
                        </a>
                    </div>
                    <div class="message-time">
                        {mensagem.data_envio.strftime("%H:%M")}
                        <span class="message-status">
                            <i class="fas fa-check"></i>
                        </span>
                    </div>
                </div>
            """
        elif mensagem.tipo == 'audio' and mensagem.arquivo:
            html_content = f"""
                <div class="message sent">
                    <div class="message-content message-audio">
                        <i class="fas fa-volume-up"></i>
                        <audio controls class="audio-player">
                            <source src="{mensagem.arquivo.url}" type="audio/mpeg">
                            Seu navegador não suporta áudio.
                        </audio>
                    </div>
                    <div class="message-time">
                        {mensagem.data_envio.strftime("%H:%M")}
                        <span class="message-status">
                            <i class="fas fa-check"></i>
                        </span>
                    </div>
                </div>
            """
        else:
            html_content = f"""
                <div class="message sent">
                    <div class="message-content">{mensagem_texto}</div>
                    <div class="message-time">
                        {mensagem.data_envio.strftime("%H:%M")}
                        <span class="message-status">
                            <i class="fas fa-check"></i>
                        </span>
                    </div>
                </div>
            """
        
        response_data = {
            'success': True,
            'message': 'Mensagem enviada com sucesso!',
            'chat_id': str(chat.id),
            'mensagem_id': str(mensagem.id),
            'html': html_content,
            'historico_salvo': True 
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"❌ ERRO GRAVE ao enviar mensagem: {str(e)}", exc_info=True)
        
        error_msg = 'Erro interno ao enviar mensagem. Tente novamente.'
        
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=500)
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_notifications_count(request):
    """API para obter contador de notificações não lidas"""
    count = Notificacao.objects.filter(usuario=request.user, lida=False).count()
    return Response({'count': count})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_notifications(request):
    """API para obter notificações recentes"""
    notificacoes = Notificacao.objects.filter(
        usuario=request.user
    ).order_by('-data_criacao')[:10]
    
    serializer = NotificacaoSerializer(notificacoes, many=True)
    return Response({'notificacoes': serializer.data})

def user_ads_view(request, user_id):
    """View para listar todos os anúncios de um usuário específico."""
    try:
        usuario = get_object_or_404(CustomUser, pk=user_id)
        anuncios_usuario = Anuncio.objects.filter(
            usuario=usuario,
            status='ativo'
        ).select_related('localizacao', 'categoria').prefetch_related(
            Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
        ).order_by('-data_criacao')

        context = {
            'usuario_perfil': usuario,
            'anuncios_usuario': anuncios_usuario,
            'anuncios_count': anuncios_usuario.count(),
        }
        return render(request, 'user_ads.html', context)

    except CustomUser.DoesNotExist:
        messages.error(request, "Usuário não encontrado.")
        return redirect('home')
    except Exception as e:
        messages.error(request, "Ocorreu um erro ao carregar os anúncios do usuário.")
        if settings.DEBUG:
            raise e
        return redirect('home')
    
@login_required
def conversa_view(request, anunciante_id):
    """View para exibir uma conversa usando anunciante_id - CORRIGIDA"""
    try:
        chat = Chat.objects.filter(participantes=request.user) \
                         .filter(participantes__id=anunciante_id) \
                         .first()
        
        if not chat:
            anunciante = get_object_or_404(CustomUser, pk=anunciante_id)
            
            if request.user == anunciante:
                messages.warning(request, "Você não pode iniciar uma conversa consigo mesmo.")
                return redirect('home')
            
            chat = Chat.objects.create()
            chat.participantes.add(request.user, anunciante)
            chat.save()
        
        mensagens = chat.mensagens_chat.all().order_by('data_envio')
        
        if request.method == 'POST':
            texto = request.POST.get('conteudo', '').strip()
            if texto:
                Mensagem.objects.create(
                    chat=chat,
                    remetente=request.user,
                    conteudo=texto,
                    tipo='texto'
                )
                return redirect('conversa', anunciante_id=anunciante_id)
        
        outro_usuario = get_object_or_404(CustomUser, pk=anunciante_id)
        
        context = {
            'chat': chat,
            'mensagens': mensagens,
            'outro_usuario': outro_usuario
        }
        return render(request, 'mensagens.html', context)
        
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, f"Erro ao carregar conversa: {str(e)}")
        return redirect('messages-view')
    
def view_user_profile(request, user_id):
    """View para visualizar perfil de outro usuário"""
    try:
        usuario = get_object_or_404(CustomUser, pk=user_id)
        
        is_own_profile = (request.user == usuario)
        
        anuncios_usuario = Anuncio.objects.filter(
            usuario=usuario,
            status='ativo'
        ).select_related('categoria', 'localizacao').prefetch_related(
            Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
        )[:6]
        
        total_anuncios = Anuncio.objects.filter(usuario=usuario, status='ativo').count()
        member_since = usuario.date_joined
        
        context = {
            'profile_user': usuario,
            'is_own_profile': is_own_profile,
            'anuncios_usuario': anuncios_usuario,
            'total_anuncios': total_anuncios,
            'member_since': member_since,
        }
        
        return render(request, 'view_profile.html', context)
        
    except CustomUser.DoesNotExist:
        messages.error(request, "Usuário não encontrado.")
        return redirect('home')
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, "Erro ao carregar perfil.")
        return redirect('home')

def category_view(request, slug):
    categoria = get_object_or_404(Categoria, slug=slug)
    
    anuncios = Anuncio.objects.filter(categoria=categoria).order_by('-data_criacao')
    
    context = {
        'categoria': categoria,
        'anuncios': anuncios
    }
    
    return render(request, 'categoria.html', context)
    
def search_results(request):
    query = request.GET.get('q')
    category_slug = request.GET.get('category')
    
    anuncios = Anuncio.objects.all()
    
    if query:
        anuncios = anuncios.filter(titulo__icontains=query)
    
    if category_slug:
        try:
            categoria = Categoria.objects.get(slug=category_slug)
            anuncios = anuncios.filter(categoria=categoria)
        except Categoria.DoesNotExist:
            pass 
            
    context = {
        'anuncios': anuncios,
        'query': query,
        'category_slug': category_slug
    }
    
    return render(request, 'search_results.html', context)

@login_required
def iniciar_conversa_view(request, anunciante_id, anuncio_id=None):
    """
    Inicia ou redireciona para uma conversa existente entre o usuário logado e um anunciante.
    """
    try:
        anunciante = get_object_or_404(CustomUser, pk=anunciante_id)

        if request.user == anunciante:
            messages.warning(request, "Você não pode iniciar uma conversa consigo mesmo.")
            return redirect('home')

        chat = Chat.objects.filter(participantes=request.user) \
                          .filter(participantes=anunciante) \
                          .first()

        if not chat:
            chat = Chat.objects.create()
            chat.participantes.add(request.user, anunciante)
            chat.save()

            if anuncio_id:
                anuncio = get_object_or_404(Anuncio, pk=anuncio_id, usuario=anunciante)
                mensagem_inicial = f"Olá! Tenho interesse no seu anúncio: {anuncio.titulo}"
                
                Mensagem.objects.create(
                    chat=chat,
                    remetente=request.user,
                    conteudo=mensagem_inicial
                )

        return redirect(reverse('messages-view') + f'?chat={chat.id}')
        
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, f"Erro ao iniciar conversa: {str(e)}")
        return redirect('home')

def search_view(request):
    """View COMPLETA para pesquisa - com histórico funcionando"""
    try:
        query = request.GET.get('q', '').strip()
        categoria_filter = request.GET.get('categoria', '')
        localizacao_filter = request.GET.get('localizacao', '')
        ordenar_filter = request.GET.get('ordenar', 'recentes')
        preco_min = request.GET.get('preco_min', '')
        preco_max = request.GET.get('preco_max', '')
        
        print(f"🔍 DEBUG Pesquisa - Query: {query}, Categoria: {categoria_filter}")
        
        if query and request.user.is_authenticated:
            try:
                historico_busca = HistoricoBusca(
                    usuario=request.user,
                    termo=query,
                    tipo='search'
                )
                
                if categoria_filter:
                    try:
                        categoria = Categoria.objects.get(slug=categoria_filter)
                        historico_busca.categoria = categoria
                    except Categoria.DoesNotExist:
                        pass
                
                if localizacao_filter:
                    try:
                        localizacao = Localizacao.objects.get(id=localizacao_filter)
                        historico_busca.localizacao = localizacao
                    except Localizacao.DoesNotExist:
                        pass
                
                historico_busca.save()
                print(f"📝 Histórico salvo: {query} para usuário {request.user.email}")
                
            except Exception as e:
                print(f"⚠️ Erro ao salvar histórico: {str(e)}")
        
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
            print(f"✅ Filtro por query aplicado: {query}")
        
        if categoria_filter:
            anuncios = anuncios.filter(categoria__slug=categoria_filter)
            print(f"✅ Filtro por categoria: {categoria_filter}")
        
        if localizacao_filter:
            anuncios = anuncios.filter(localizacao__id=localizacao_filter)
            print(f"✅ Filtro por localização: {localizacao_filter}")
        
        if preco_min:
            try:
                anuncios = anuncios.filter(valor__gte=float(preco_min))
                print(f"✅ Preço mínimo: {preco_min}")
            except (ValueError, TypeError):
                print("❌ Erro no preço mínimo")
                pass
        
        if preco_max:
            try:
                anuncios = anuncios.filter(valor__lte=float(preco_max))
                print(f"✅ Preço máximo: {preco_max}")
            except (ValueError, TypeError):
                print("❌ Erro no preço máximo")
                pass
        
        if ordenar_filter == 'recentes':
            anuncios = anuncios.order_by('-data_criacao')
        elif ordenar_filter == 'antigos':
            anuncios = anuncios.order_by('data_criacao')
        elif ordenar_filter == 'menor-preco':
            anuncios = anuncios.order_by('valor')
        elif ordenar_filter == 'maior-preco':
            anuncios = anuncios.order_by('-valor')
        elif ordenar_filter == 'mais-vistos':
            anuncios = anuncios.order_by('-visualizacoes')
        
        print(f"📊 Total de anúncios encontrados: {anuncios.count()}")
        
        page = request.GET.get('page', 1)
        paginator = Paginator(anuncios, 12)
        
        try:
            anuncios_paginados = paginator.page(page)
        except PageNotAnInteger:
            anuncios_paginados = paginator.page(1)
        except EmptyPage:
            anuncios_paginados = paginator.page(paginator.num_pages)

        for anuncio in anuncios_paginados:
            if request.user.is_authenticated:
                anuncio.favoritado = Favorito.objects.filter(
                    usuario=request.user,
                    content_type=ContentType.objects.get_for_model(Anuncio),
                    object_id=anuncio.id
                ).exists()
            else:
                anuncio.favoritado = False
            
            if anuncio.valor:
                anuncio.valor_formatado = f"R$ {anuncio.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            else:
                anuncio.valor_formatado = "A combinar"
        
        categorias = Categoria.objects.filter(ativa=True)
        localizacoes = Localizacao.objects.all()
        
        context = {
            'anuncios': anuncios_paginados,
            'query': query,
            'categorias': categorias,
            'localizacoes': localizacoes,
            'total_resultados': anuncios.count(),
            'categoria_filtro': categoria_filter,
            'localizacao_filtro': localizacao_filter,
            'ordenar_filtro': ordenar_filter,
            'preco_min_filtro': preco_min,
            'preco_max_filtro': preco_max,
        }
        
        return render(request, 'search_results.html', context)
        
    except Exception as e:
        print(f"🔥 ERRO na pesquisa: {str(e)}")
        if settings.DEBUG:
            raise e
        
        context = {
            'anuncios': [],
            'query': query,
            'categorias': Categoria.objects.filter(ativa=True),
            'localizacoes': Localizacao.objects.all(),
            'total_resultados': 0,
            'error': 'Ocorreu um erro na pesquisa. Tente novamente.'
        }
        return render(request, 'search_results.html', context)
    
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
    
class RegistroAPIView(APIView):
    """API para registro de novos usuários - VERSÃO CORRIGIDA"""
    permission_classes = [AllowAny]

    def post(self, request):
        print("📝 [DJANGO-REGISTRO] Recebendo dados:", request.data)
        
        try:
          
            data = request.data.copy()
            
         
            data['first_name'] = data.get('nome', '')
            data['password2'] = data.get('confirmPassword', '')
            data['termos_aceitos'] = True
            
            print("🔄 [DJANGO-REGISTRO] Dados adaptados:", {
                'first_name': data.get('first_name'),
                'email': data.get('email'),
                'telefone': data.get('telefone'),
                'password': '***',
                'password2': '***'
            })
            
            serializer = UsuarioRegistroSerializer(data=data)
            
            if serializer.is_valid():
                print("✅ [DJANGO-REGISTRO] Dados válidos, criando usuário...")
                user = serializer.save()
                
             
                refresh = RefreshToken.for_user(user)
                
               
                user_data = {
                    'id': user.id,
                    'nome': user.first_name or user.email.split('@')[0],
                    'email': user.email,
                    'telefone': user.telefone,
                    'data_criacao': user.date_joined.isoformat(),
                }
                
                print(f"🎉 [DJANGO-REGISTRO] Usuário criado: {user.email}")
                
                return Response({
                    'user': user_data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'Conta criada com sucesso!'
                }, status=status.HTTP_201_CREATED)
            else:
                print(f"❌ [DJANGO-REGISTRO] Erros de validação: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            print(f"💥 [DJANGO-REGISTRO] Erro interno: {str(e)}")
            return Response(
                {'error': 'Erro interno no servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
class FavoritosAPIView(APIView):
    """API para obter favoritos do usuário"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication] 

    def get(self, request):
        try:
            print(f"🔐 Usuário autenticado: {request.user.email}")
            
           
            anuncio_content_type = ContentType.objects.get_for_model(Anuncio)
            
          
            favoritos_list = Favorito.objects.filter(
                usuario=request.user,
                content_type=anuncio_content_type
            ).select_related('content_type').order_by('-data_criacao')
            
            print(f"📚 Encontrados {favoritos_list.count()} favoritos para {request.user.email}")
            
            favoritos_data = []
            for favorito in favoritos_list:
                try:
                    anuncio = favorito.content_object
                    if anuncio and hasattr(anuncio, 'status') and anuncio.status in ['ativo', 'pendente']:
                        
                        imagem_principal = None
                        if hasattr(anuncio, 'imagens') and anuncio.imagens.exists():
                            imagem_capa = anuncio.imagens.filter(capa=True).first()
                            if imagem_capa:
                                imagem_principal = request.build_absolute_uri(imagem_capa.imagem.url)
                            else:
                                primeira_imagem = anuncio.imagens.first()
                                if primeira_imagem:
                                    imagem_principal = request.build_absolute_uri(primeira_imagem.imagem.url)
                        
                        localizacao_str = "Localização não informada"
                        if hasattr(anuncio, 'localizacao') and anuncio.localizacao:
                            if hasattr(anuncio.localizacao, 'cidade') and hasattr(anuncio.localizacao, 'estado'):
                                localizacao_str = f"{anuncio.localizacao.cidade}, {anuncio.localizacao.estado}"
                        
                        valor_formatado = "A combinar"
                        if hasattr(anuncio, 'valor') and anuncio.valor:
                            valor_formatado = f"R$ {anuncio.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        
                        favoritos_data.append({
                            'id': favorito.id,
                            'anuncio': {
                                'id': anuncio.id,
                                'titulo': anuncio.titulo,
                                'descricao': anuncio.descricao,
                                'valor': float(anuncio.valor) if anuncio.valor else None,
                                'valor_formatado': valor_formatado,
                                'categoria': {
                                    'id': anuncio.categoria.id,
                                    'titulo': anuncio.categoria.titulo
                                },
                                'usuario': {
                                    'id': anuncio.usuario.id,
                                    'nome': anuncio.usuario.get_full_name() or anuncio.usuario.email.split('@')[0]
                                },
                                'localizacao_str': localizacao_str,
                                'imagem_principal': imagem_principal,
                                'data_criacao': anuncio.data_criacao.isoformat()
                            },
                            'data_criacao': favorito.data_criacao.isoformat()
                        })
                        
                except Exception as e:
                    print(f"❌ Erro ao processar favorito {favorito.id}: {str(e)}")
                    continue
            
            return Response({
                'favoritos': favoritos_data,
                'total': len(favoritos_data),
                'usuario': request.user.email
            })
            
        except Exception as e:
            print(f"❌ Erro na API de favoritos: {str(e)}")
            return Response({
                'error': 'Erro ao carregar favoritos',
                'favoritos': [],
                'total': 0
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remover_favorito_api(request, favorito_id):
    """API para remover favorito"""
    try:
        favorito = get_object_or_404(Favorito, pk=favorito_id, usuario=request.user)
        favorito.delete()
        
        return Response({
            'success': True,
            'message': 'Favorito removido com sucesso!'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erro ao remover favorito'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats_view(request):
    """API para estatísticas do usuário"""
    try:
        user = request.user
        
        servicos_count = Servico.objects.filter(usuario=user).count()
        
        favoritos_count = Favorito.objects.filter(usuario=user).count()
        
        total_visualizacoes = Servico.objects.filter(
            usuario=user
        ).aggregate(total=Sum('visualizacoes'))['total'] or 0
        
        return Response({
            'servicos_count': servicos_count,
            'favoritos_count': favoritos_count,
            'avaliacao_media': 5.0,  
            'total_visualizacoes': total_visualizacoes,
        })
        
    except Exception as e:
        return Response(
            {'error': 'Erro ao carregar estatísticas'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def anuncios_por_categoria(request, slug):
    """API para obter anúncios por categoria"""
    try:
        categoria = get_object_or_404(Categoria, slug=slug, ativa=True)
        
        anuncios = Anuncio.objects.filter(
            categoria=categoria,
            status='ativo'
        ).select_related('usuario', 'localizacao', 'categoria').prefetch_related(
            Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
        ).order_by('-data_criacao')
        
        serializer = AnuncioSerializer(anuncios, many=True, context={'request': request})
        
        return Response({
            'categoria': {
                'id': categoria.id,
                'titulo': categoria.titulo,
                'slug': categoria.slug,
                'imagem': categoria.imagem.url if categoria.imagem else None,
                'total_anuncios': anuncios.count()
            },
            'anuncios': serializer.data
        })
        
    except Exception as e:
        return Response(
            {'error': 'Erro ao carregar anúncios da categoria'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class MobileUserStatsAPIView(APIView):
    """API para estatísticas do usuário mobile"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            user = request.user
            
            servicos_count = Anuncio.objects.filter(usuario=user).count()
            
            anuncio_content_type = ContentType.objects.get_for_model(Anuncio)
            favoritos_count = Favorito.objects.filter(
                usuario=user,
                content_type=anuncio_content_type
            ).count()
            
            total_visualizacoes = Anuncio.objects.filter(
                usuario=user
            ).aggregate(total=Sum('visualizacoes'))['total'] or 0
            
            avaliacao_media = 5.0
            
            return Response({
                'servicos_count': servicos_count,
                'favoritos_count': favoritos_count,
                'avaliacao_media': avaliacao_media,
                'total_visualizacoes': total_visualizacoes,
            })
            
        except Exception as e:
            print(f"❌ Erro ao carregar estatísticas: {str(e)}")
            return Response(
                {'error': 'Erro ao carregar estatísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MobileUserAnunciosAPIView(APIView):
    """API para anúncios do usuário mobile"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            user = request.user
            
            anuncios = Anuncio.objects.filter(
                usuario=user
            ).select_related('categoria', 'localizacao').prefetch_related(
                Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
            ).order_by('-data_criacao')
            
            serializer = AnuncioSerializer(
                anuncios, 
                many=True, 
                context={'request': request}
            )
            
            return Response({
                'anuncios': serializer.data
            })
            
        except Exception as e:
            print(f"❌ Erro ao carregar anúncios: {str(e)}")
            return Response(
                {'error': 'Erro ao carregar anúncios'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MobileUserFavoritesAPIView(APIView):
    """API para favoritos do usuário mobile"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            user = request.user
            
            anuncio_content_type = ContentType.objects.get_for_model(Anuncio)
            
            favoritos = Favorito.objects.filter(
                usuario=user,
                content_type=anuncio_content_type
            ).select_related('content_type').order_by('-data_criacao')
            
            favoritos_data = []
            for favorito in favoritos:
                try:
                    anuncio = favorito.content_object
                    if anuncio and hasattr(anuncio, 'status') and anuncio.status in ['ativo', 'pendente']:
                        
                        imagem_principal = None
                        if hasattr(anuncio, 'imagens') and anuncio.imagens.exists():
                            imagem_capa = anuncio.imagens.filter(capa=True).first()
                            if imagem_capa:
                                imagem_principal = request.build_absolute_uri(imagem_capa.imagem.url)
                        
                        favoritos_data.append({
                            'id': favorito.id,
                            'anuncio': {
                                'id': anuncio.id,
                                'titulo': anuncio.titulo,
                                'descricao': anuncio.descricao,
                                'valor': float(anuncio.valor) if anuncio.valor else None,
                                'categoria': {
                                    'id': anuncio.categoria.id,
                                    'titulo': anuncio.categoria.titulo
                                },
                                'imagem_principal': imagem_principal,
                                'data_criacao': anuncio.data_criacao.isoformat()
                            }
                        })
                        
                except Exception as e:
                    print(f"❌ Erro ao processar favorito: {str(e)}")
                    continue
            
            return Response({
                'favoritos': favoritos_data
            })
            
        except Exception as e:
            print(f"❌ Erro ao carregar favoritos: {str(e)}")
            return Response(
                {'error': 'Erro ao carregar favoritos'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MobileUserProfileAPIView(APIView):
    """API para perfil completo do usuário mobile"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            user = request.user
            
            user_data = {
                'id': user.id,
                'nome': user.get_full_name() or user.email.split('@')[0],
                'email': user.email,
                'telefone': user.telefone or '',
                'avatar': request.build_absolute_uri(user.foto_perfil.url) if user.foto_perfil else None,
                'premium': user.premium if hasattr(user, 'premium') else False,
                'data_criacao': user.date_joined.isoformat(),
                'reputacao': user.reputacao if hasattr(user, 'reputacao') else 5.0,
            }
            
            return Response(user_data)
            
        except Exception as e:
            print(f"❌ Erro ao carregar perfil: {str(e)}")
            return Response(
                {'error': 'Erro ao carregar perfil'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserProfileDetailAPIView(APIView):
    """API para obter dados completos do perfil do usuário - ALINHADO COM SEU MODELO"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        try:
            user = request.user
            print(f"👤 [API-PROFILE] Carregando perfil para: {user.email}")
            
            user_data = {
                'id': user.id,
                'nome': user.nome,  
                'nome_utilizador': user.nome_utilizador,  
                'email': user.email,
                'telefone': user.telefone or '',
                'avatar': request.build_absolute_uri(user.foto_perfil.url) if user.foto_perfil else None,
                'data_criacao': user.data_criacao.isoformat(),  
                'ultima_atualizacao': user.ultima_atualizacao.isoformat() if user.ultima_atualizacao else None, 
                'premium': user.premium,  
                'reputacao': float(user.reputacao),  
                'creditos': user.creditos,  
                'email_verificado': user.email_verificado, 
                'cpf': user.cpf or '',  
                'data_nascimento': user.data_nascimento.isoformat() if user.data_nascimento else None,  
                'localizacao': {
                    'id': user.localizacao.id,
                    'nome': user.localizacao.nome
                } if user.localizacao else None,
                'ultimo_login': user.last_login.isoformat() if user.last_login else None,
            }

            anuncios_count = Anuncio.objects.filter(usuario=user).count()
            anuncios_ativos = Anuncio.objects.filter(usuario=user, status='ativo').count()
            
            anuncio_content_type = ContentType.objects.get_for_model(Anuncio)
            favoritos_count = Favorito.objects.filter(
                usuario=user,
                content_type=anuncio_content_type
            ).count()
            
            total_visualizacoes = Anuncio.objects.filter(
                usuario=user
            ).aggregate(total=Sum('visualizacoes'))['total'] or 0

            notificacoes_nao_lidas = Notificacao.objects.filter(
                usuario=user,
                lida=False
            ).count()

            anuncios_recentes = Anuncio.objects.filter(
                usuario=user
            ).select_related('categoria', 'localizacao').prefetch_related(
                Prefetch('imagens', queryset=Imagem.objects.filter(capa=True))
            ).order_by('-data_criacao')[:6]

            anuncios_data = []
            for anuncio in anuncios_recentes:
                imagem_principal = None
                if anuncio.imagens.exists():
                    imagem_capa = anuncio.imagens.filter(capa=True).first()
                    if imagem_capa:
                        imagem_principal = request.build_absolute_uri(imagem_capa.imagem.url)
                    else:
                        primeira_imagem = anuncio.imagens.first()
                        if primeira_imagem:
                            imagem_principal = request.build_absolute_uri(primeira_imagem.imagem.url)
                
                anuncios_data.append({
                    'id': anuncio.id,
                    'titulo': anuncio.titulo,
                    'descricao': anuncio.descricao,
                    'valor': float(anuncio.valor) if anuncio.valor else None,
                    'valor_formatado': f"R$ {anuncio.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if anuncio.valor else "A combinar",
                    'categoria': {
                        'id': anuncio.categoria.id,
                        'titulo': anuncio.categoria.titulo,
                        'slug': anuncio.categoria.slug
                    },
                    'status': anuncio.status,
                    'status_display': anuncio.get_status_display(),
                    'visualizacoes': anuncio.visualizacoes,
                    'imagem_principal': imagem_principal,
                    'data_criacao': anuncio.data_criacao.isoformat(),
                    'destaque': anuncio.destaque,
                    'localizacao': f"{anuncio.localizacao.cidade}, {anuncio.localizacao.estado}" if anuncio.localizacao else "Localização não informada",
                    'estado_produto': anuncio.estado_produto,
                    'whatsapp': anuncio.whatsapp,
                })

            favoritos_recentes = Favorito.objects.filter(
                usuario=user,
                content_type=anuncio_content_type
            ).select_related('content_type').order_by('-data_criacao')[:4]

            favoritos_data = []
            for favorito in favoritos_recentes:
                try:
                    anuncio = favorito.content_object
                    if anuncio and hasattr(anuncio, 'status') and anuncio.status in ['ativo', 'pendente']:
                        
                        imagem_principal = None
                        if hasattr(anuncio, 'imagens') and anuncio.imagens.exists():
                            imagem_capa = anuncio.imagens.filter(capa=True).first()
                            if imagem_capa:
                                imagem_principal = request.build_absolute_uri(imagem_capa.imagem.url)
                        
                        favoritos_data.append({
                            'id': favorito.id,
                            'anuncio': {
                                'id': anuncio.id,
                                'titulo': anuncio.titulo,
                                'valor': float(anuncio.valor) if anuncio.valor else None,
                                'valor_formatado': f"R$ {anuncio.valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if anuncio.valor else "A combinar",
                                'categoria': {
                                    'id': anuncio.categoria.id,
                                    'titulo': anuncio.categoria.titulo
                                },
                                'imagem_principal': imagem_principal,
                                'status': anuncio.status,
                            },
                            'data_criacao': favorito.data_criacao.isoformat()
                        })
                        
                except Exception as e:
                    print(f"❌ Erro ao processar favorito: {str(e)}")
                    continue

            historico_recente = HistoricoBusca.objects.filter(
                usuario=user
            ).select_related('localizacao').order_by('-data_busca')[:5]

            historico_data = []
            for item in historico_recente:
                historico_data.append({
                    'id': item.id,
                    'termo': item.termo,
                    'tipo': item.tipo,
                    'tipo_display': item.get_tipo_display(),
                    'data_busca': item.data_busca.isoformat(),
                    'item_titulo': item.get_titulo_item(),
                    'localizacao': item.localizacao.nome if item.localizacao else None,
                })

            configuracoes_data = {}
            try:
                config = ConfiguracaoUsuario.objects.get(usuario=user)
                configuracoes_data = {
                    'receber_email': config.receber_email,
                    'modo_escuro': config.modo_escuro,
                    'idioma': config.idioma,
                    'notificacoes_push': config.notificacoes_push,
                    'mostrar_localizacao': config.mostrar_localizacao,
                }
            except ConfiguracaoUsuario.DoesNotExist:
                configuracoes_data = {
                    'receber_email': True,
                    'modo_escuro': False,
                    'idioma': 'pt-br',
                    'notificacoes_push': True,
                    'mostrar_localizacao': True,
                }

            print(f"✅ [API-PROFILE] Perfil carregado com sucesso para {user.email}")
            
            return Response({
                'success': True,
                'user': user_data,
                'estatisticas': {
                    'anuncios_total': anuncios_count,
                    'anuncios_ativos': anuncios_ativos,
                    'favoritos_count': favoritos_count,
                    'total_visualizacoes': total_visualizacoes,
                    'notificacoes_nao_lidas': notificacoes_nao_lidas,
                    'avaliacao_media': float(user.reputacao),  # Usando a reputação do usuário
                    'creditos_disponiveis': user.creditos,
                },
                'anuncios_recentes': anuncios_data,
                'favoritos_recentes': favoritos_data,
                'historico_recente': historico_data,
                'configuracoes': configuracoes_data,
                'tempo_na_plataforma': self.calcular_tempo_na_plataforma(user.data_criacao),
                'membro_desde': user.data_criacao.strftime('%d/%m/%Y'),
            })
            
        except Exception as e:
            print(f"❌ [API-PROFILE] Erro ao carregar perfil: {str(e)}")
            import traceback
            print(f"🔍 [API-PROFILE] Traceback: {traceback.format_exc()}")
            
            return Response({
                'success': False,
                'error': f'Erro ao carregar perfil: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def calcular_tempo_na_plataforma(self, data_criacao):
        """Calcula o tempo que o usuário está na plataforma"""
        from datetime import datetime
        from django.utils import timezone
        
        now = timezone.now()
        delta = now - data_criacao
        
        if delta.days < 1:
            return "Hoje"
        elif delta.days == 1:
            return "1 dia"
        elif delta.days < 30:
            return f"{delta.days} dias"
        elif delta.days < 365:
            meses = delta.days // 30
            return f"{meses} {'mês' if meses == 1 else 'meses'}"
        else:
            anos = delta.days // 365
            return f"{anos} {'ano' if anos == 1 else 'anos'}"

class UserProfileUpdateAPIView(APIView):
    """API para atualizar dados do perfil do usuário - ALINHADO COM SEU MODELO"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def put(self, request):
        try:
            user = request.user
            data = request.data.copy()
            
            print(f"✏️ [API-PROFILE] Atualizando perfil para: {user.email}")
            print(f"📦 [API-PROFILE] Dados recebidos: {data}")
            
            allowed_fields = ['nome', 'telefone', 'data_nascimento', 'cpf']
            
            for field in allowed_fields:
                if field in data and data[field] is not None:
                    if field == 'data_nascimento' and data[field] == '':
                        setattr(user, field, None)
                    else:
                        setattr(user, field, data[field])
            
            if 'localizacao_id' in data and data['localizacao_id']:
                try:
                    localizacao = Localizacao.objects.get(id=data['localizacao_id'])
                    user.localizacao = localizacao
                except Localizacao.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': 'Localização não encontrada'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            if 'foto_perfil' in request.FILES:
                print("🖼️ [API-PROFILE] Atualizando foto de perfil")
                user.foto_perfil = request.FILES['foto_perfil']
            
            try:
                user.full_clean()
                user.save()
                print(f"✅ [API-PROFILE] Perfil atualizado com sucesso para {user.email}")
            except ValidationError as e:
                print(f"❌ [API-PROFILE] Erro de validação: {e}")
                return Response({
                    'success': False,
                    'error': 'Dados inválidos',
                    'validation_errors': e.message_dict
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user_data = {
                'id': user.id,
                'nome': user.nome,
                'nome_utilizador': user.nome_utilizador,
                'email': user.email,
                'telefone': user.telefone or '',
                'avatar': request.build_absolute_uri(user.foto_perfil.url) if user.foto_perfil else None,
                'data_criacao': user.data_criacao.isoformat(),
                'data_nascimento': user.data_nascimento.isoformat() if user.data_nascimento else None,
                'cpf': user.cpf or '',
                'localizacao': {
                    'id': user.localizacao.id,
                    'nome': user.localizacao.nome
                } if user.localizacao else None,
                'ultima_atualizacao': user.ultima_atualizacao.isoformat(),
            }
            
            return Response({
                'success': True,
                'message': 'Perfil atualizado com sucesso!',
                'user': user_data
            })
            
        except Exception as e:
            print(f"❌ [API-PROFILE] Erro ao atualizar perfil: {str(e)}")
            import traceback
            print(f"🔍 [API-PROFILE] Traceback: {traceback.format_exc()}")
            
            return Response({
                'success': False,
                'error': f'Erro ao atualizar perfil: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserProfilePhotoUpdateAPIView(APIView):
    """API apenas para atualizar foto de perfil"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            user = request.user
            
            if 'foto_perfil' not in request.FILES:
                return Response({
                    'success': False,
                    'error': 'Nenhuma imagem fornecida'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user.foto_perfil = request.FILES['foto_perfil']
            user.save()
            
            return Response({
                'success': True,
                'message': 'Foto de perfil atualizada com sucesso!',
                'avatar_url': request.build_absolute_uri(user.foto_perfil.url)
            })
            
        except Exception as e:
            print(f"❌ Erro ao atualizar foto: {str(e)}")
            return Response({
                'success': False,
                'error': 'Erro ao atualizar foto de perfil'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            

class CategoriasListAPIView(APIView):
    """API para listar categorias para o mobile"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            print("📋 [API] Buscando categorias...")
            categorias = Categoria.objects.filter(ativa=True).order_by('titulo')
            
            categorias_data = []
            for categoria in categorias:
                categorias_data.append({
                    'id': categoria.id,
                    'titulo': categoria.titulo,
                    'slug': categoria.slug,
                    'ativa': categoria.ativa,
                    'icone': categoria.icone.url if categoria.icone else None,
                    'cor': categoria.cor,
                })
            
            print(f"✅ [API] {len(categorias_data)} categorias encontradas")
            return Response(categorias_data)
            
        except Exception as e:
            print(f"❌ [API] Erro ao buscar categorias: {str(e)}")
            return Response(
                {'error': 'Erro ao carregar categorias'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LocalizacoesListAPIView(APIView):
    """API para listar localizações para o mobile"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            print("📍 [API] Buscando localizações...")
            localizacoes = Localizacao.objects.all().order_by('cidade', 'estado')
            
            localizacoes_data = []
            for localizacao in localizacoes:
                localizacoes_data.append({
                    'id': localizacao.id,
                    'cidade': localizacao.cidade,
                    'estado': localizacao.estado,
                    'nome': localizacao.nome,
                })
            
            print(f"✅ [API] {len(localizacoes_data)} localizações encontradas")
            return Response(localizacoes_data)
            
        except Exception as e:
            print(f"❌ [API] Erro ao buscar localizações: {str(e)}")
            return Response(
                {'error': 'Erro ao carregar localizações'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CriarAnuncioAPIView(APIView):
    """API para criar anúncio via mobile"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        try:
            print("📱 [API-CRIAR-ANUNCIO] Recebendo dados do anúncio...")
            
            data_dict = dict(request.data)
            if 'imagens' in data_dict:
                data_dict['imagens'] = f"{len(request.FILES.getlist('imagens'))} imagens"
            print("📦 Dados recebidos:", data_dict)
            
            data = request.data
            imagens = request.FILES.getlist('imagens')
            
            campos_obrigatorios = ['titulo', 'categoria', 'descricao', 'localizacao', 'whatsapp']
            campos_faltantes = [campo for campo in campos_obrigatorios if not data.get(campo)]
            
            if campos_faltantes:
                return Response(
                    {'error': f'Campos obrigatórios faltando: {", ".join(campos_faltantes)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                categoria = Categoria.objects.get(id=data['categoria'], ativa=True)
            except Categoria.DoesNotExist:
                return Response(
                    {'error': 'Categoria não encontrada ou inativa'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                localizacao = Localizacao.objects.get(id=data['localizacao'])
            except Localizacao.DoesNotExist:
                return Response(
                    {'error': 'Localização não encontrada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            valor_final = None
            if data.get('valor'):
                try:
                    
                    valor_str = str(data['valor']).replace('R$', '').replace('.', '').replace(',', '.').strip()
                    valor_final = float(valor_str)
                    if valor_final <= 0:
                        valor_final = None
                except (ValueError, TypeError) as e:
                    print(f" Erro ao converter valor: {data['valor']} - {e}")
                    
                    valor_final = None

            whatsapp_clean = ''.join(filter(str.isdigit, str(data['whatsapp'])))
            if len(whatsapp_clean) < 10:
                return Response(
                    {'error': 'WhatsApp deve ter pelo menos 10 dígitos'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            tags_list = []
            if data.get('tags'):
                if isinstance(data['tags'], str):
                    tags_list = [tag.strip() for tag in data['tags'].split(',') if tag.strip()]
                elif isinstance(data['tags'], list):
                    tags_list = data['tags']
            
            anuncio = Anuncio(
                titulo=data['titulo'].strip(),
                descricao=data['descricao'].strip(),
                categoria=categoria,
                valor=valor_final,
                usuario=request.user,
                localizacao=localizacao,
                whatsapp=whatsapp_clean,
                estado_produto=data.get('estado_produto', 'usado'),
                tipo_anuncio=data.get('tipo_anuncio', 'servico'),
                destaque=data.get('destaque', 'false') == 'true',
                disponivel_24h=data.get('disponivel_24h', 'false') == 'true',
                orcamento_gratis=data.get('orcamento_gratis', 'false') == 'true',
                garantia=data.get('garantia', 'false') == 'true',
                status='ativo'
            )
            
            anuncio.full_clean()
            anuncio.save()
            
            imagens_salvas = []
            for i, imagem_file in enumerate(imagens):
                if i < 10:  
                    try:
                        if not imagem_file.content_type.startswith('image/'):
                            print(f" Arquivo não é imagem: {imagem_file.name}")
                            continue
                        
                        if imagem_file.size > 5 * 1024 * 1024:
                            print(f" Imagem muito grande: {imagem_file.name}")
                            continue
                        
                        imagem = Imagem(
                            anuncio=anuncio,
                            imagem=imagem_file,
                            capa=(i == 0)  
                        )
                        imagem.save()
                        
                        imagens_salvas.append({
                            'id': imagem.id,
                            'url': request.build_absolute_uri(imagem.imagem.url),
                            'capa': imagem.capa
                        })
                        
                        print(f" Imagem {i+1} salva: {imagem_file.name}")
                        
                    except Exception as e:
                        print(f" Erro ao salvar imagem {i}: {str(e)}")
                        continue
            
            anuncio_data = {
                'id': anuncio.id,
                'titulo': anuncio.titulo,
                'descricao': anuncio.descricao,
                'valor': float(anuncio.valor) if anuncio.valor else None,
                'categoria': {
                    'id': categoria.id,
                    'titulo': categoria.titulo
                },
                'localizacao': {
                    'id': localizacao.id,
                    'cidade': localizacao.cidade,
                    'estado': localizacao.estado
                },
                'whatsapp': anuncio.whatsapp,
                'estado_produto': anuncio.estado_produto,
                'tipo_anuncio': anuncio.tipo_anuncio,
                'destaque': anuncio.destaque,
                'disponivel_24h': anuncio.disponivel_24h,
                'orcamento_gratis': anuncio.orcamento_gratis,
                'garantia': anuncio.garantia,
                'status': anuncio.status,
                'imagens': imagens_salvas,
                'tags': tags_list,
                'data_criacao': anuncio.data_criacao.isoformat(),
            }
            
            print(f" [API-CRIAR-ANUNCIO] Anúncio criado com sucesso: {anuncio.id}")
            
            return Response({
                'success': True,
                'message': 'Anúncio criado com sucesso!',
                'anuncio': anuncio_data
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            print(f" [API-CRIAR-ANUNCIO] Erro de validação: {e.message_dict}")
            return Response(
                {'error': 'Dados inválidos', 'validation_errors': e.message_dict},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(f" [API-CRIAR-ANUNCIO] Erro interno: {str(e)}")
            import traceback
            print(f" Traceback: {traceback.format_exc()}")
            return Response(
                {'error': 'Erro interno ao criar anúncio'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class CriarPaginaView(LoginRequiredMixin, CreateView):
    model = PaginaPessoal
    fields = ['nome_pagina', 'bio', 'foto_capa', 'visibilidade']
    template_name = 'criar_pagina.html'
    
    def dispatch(self, request, *args, **kwargs):
        if hasattr(request.user, 'pagina_pessoal'):
            messages.info(request, 'Você já possui uma página pessoal!')
            return redirect('minha-pagina')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.usuario = self.request.user
        response = super().form_valid(form)
        
        self.request.user.pagina_criada = True
        self.request.user.save()
        
        messages.success(self.request, 'Página criada com sucesso!')
        return response
    
    def get_success_url(self):
        return reverse_lazy('minha-pagina')

class PaginaDetailView(DetailView):
    model = PaginaPessoal
    template_name = 'detalhe_pagina.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pagina = self.object
        
        postagens = pagina.postagens.filter(
            ativa=True, 
            status='publicado'
        ).order_by('-data_publicacao')
        
        context['postagens'] = postagens
        context['total_postagens'] = postagens.count()
        context['total_seguidores'] = pagina.total_seguidores()
        
        if self.request.user.is_authenticated:
            context['segue_pagina'] = pagina.seguidores.filter(id=self.request.user.id).exists()
            context['is_owner'] = self.request.user == pagina.usuario
        else:
            context['segue_pagina'] = False
            context['is_owner'] = False
            
        return context

class GerenciarPaginaView(LoginRequiredMixin, UpdateView):
    model = PaginaPessoal
    fields = ['nome_pagina', 'bio', 'foto_capa', 'visibilidade']
    template_name = 'gerenciar_pagina.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'pagina_pessoal'):
            messages.error(request, 'Você precisa criar uma página primeiro!')
            return redirect('criar-pagina')
        return super().dispatch(request, *args, **kwargs)
    
    def get_object(self):
        try:
            return self.request.user.pagina_pessoal
        except PaginaPessoal.DoesNotExist:
            raise Http404("Você não possui uma página pessoal.")
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['nome_pagina'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nome da sua página'
        })
        form.fields['bio'].widget.attrs.update({
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Conte sobre você e seus produtos...'
        })
        form.fields['foto_capa'].widget.attrs.update({
            'class': 'form-control'
        })
        form.fields['visibilidade'].widget.attrs.update({
            'class': 'form-select'
        })
        return form
    
    def form_valid(self, form):
        messages.success(self.request, 'Página atualizada com sucesso! ✅')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrija os erros no formulário.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('minha-pagina')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Gerenciar Página'
        return context

class CriarPostagemView(LoginRequiredMixin, CreateView):
    model = PostagemProduto
    form_class = CriarPostagemForm
    template_name = 'criar_postagem.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'pagina_pessoal'):
            messages.error(request, 'Você precisa criar uma página pessoal primeiro!')
            return redirect('criar-pagina')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.pagina = self.request.user.pagina_pessoal
        form.instance.status = 'publicado'
        
        self.object = form.save()
        
        files = self.request.FILES.getlist('midias')
        if files:
            for i, file in enumerate(files):
                if file.content_type.startswith('image/'):
                    file_type = 'imagem'
                elif file.content_type.startswith('video/'):
                    file_type = 'video'
                else:
                    file_type = 'imagem'
                
                MidiaPostagem.objects.create(
                    postagem=self.object,
                    arquivo=file,
                    tipo=file_type,
                    ordem=i
                )
        
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Postagem criada com sucesso!',
                'redirect_url': str(self.get_success_url())
            })
        else:
            messages.success(self.request, 'Postagem criada com sucesso!')
            return redirect(self.get_success_url())
    
    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors.get_json_data()
            })
        else:
            messages.error(self.request, 'Por favor, corrija os erros no formulário.')
            return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('minha-pagina')

class FeedPostagensView(ListView):
    model = PostagemProduto
    template_name = 'feed.html'
    paginate_by = 12
    context_object_name = 'postagens'
    
    def get_queryset(self):
        return PostagemProduto.objects.filter(
            ativa=True,
            status='publicado',
            data_publicacao__isnull=False,
            pagina__ativa=True
        ).select_related('pagina', 'pagina__usuario').prefetch_related('midias').order_by('-data_publicacao')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_postagens'] = self.get_queryset().count()
        return context

@login_required
def minha_pagina_view(request):
    """View para a página pessoal do usuário - VERSÃO CORRIGIDA"""
    try:
        if not hasattr(request.user, 'pagina_pessoal'):
            messages.info(request, 'Crie sua página pessoal para começar a compartilhar seus produtos!')
            return redirect('criar-pagina')
        
        pagina = request.user.pagina_pessoal
        
        postagens = pagina.postagens.filter(
            ativa=True, 
            status='publicado'
        ).select_related('pagina').prefetch_related('midias').order_by('-data_publicacao')
        
        total_postagens = postagens.count()
        total_seguidores = pagina.total_seguidores()
        
        total_visualizacoes = sum(post.visualizacoes for post in postagens)
        total_curtidas = sum(post.curtidas.count() for post in postagens)  
        
        total_comentarios = 0
        total_compartilhamentos = 0
        
        try:
            if hasattr(postagens.first(), 'comentarios'):
                total_comentarios = sum(post.comentarios.count() for post in postagens)
            elif hasattr(postagens.first(), 'comentarios_count'):
                total_comentarios = sum(post.comentarios_count for post in postagens)
        except:
            total_comentarios = 0
        
        try:
            if hasattr(postagens.first(), 'compartilhamentos'):
                total_compartilhamentos = sum(post.compartilhamentos.count() for post in postagens)
            elif hasattr(postagens.first(), 'compartilhamentos_count'):
                total_compartilhamentos = sum(post.compartilhamentos_count for post in postagens)
        except:
            total_compartilhamentos = 0
        
        context = {
            'pagina': pagina,
            'postagens': postagens,
            'total_postagens': total_postagens,
            'total_seguidores': total_seguidores,
            'total_visualizacoes': total_visualizacoes,
            'total_curtidas': total_curtidas,
            'total_comentarios': total_comentarios,
            'total_compartilhamentos': total_compartilhamentos,
            'is_owner': True,
        }
        
        return render(request, 'minha_pagina.html', context)
        
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, 'Erro ao carregar sua página.')
        return redirect('home')

@login_required
def seguir_pagina(request, slug):
    """View para seguir uma página"""
    pagina = get_object_or_404(PaginaPessoal, slug=slug)
    
    if request.user == pagina.usuario:
        messages.error(request, 'Você não pode seguir sua própria página!')
        return redirect('pagina-detail', slug=slug)
    
    seguidor, created = SeguidorPagina.objects.get_or_create(
        pagina=pagina,
        usuario=request.user
    )
    
    if created:
        messages.success(request, f'Você começou a seguir {pagina.nome_pagina}!')
    else:
        messages.info(request, f'Você já segue {pagina.nome_pagina}.')
    
    return redirect('pagina-detail', slug=slug)
@login_required
def deixar_seguir_pagina(request, slug):
    """View para deixar de seguir uma página"""
    pagina = get_object_or_404(PaginaPessoal, slug=slug)
    
    SeguidorPagina.objects.filter(
        pagina=pagina,
        usuario=request.user
    ).delete()
    
    messages.success(request, f'Você deixou de seguir {pagina.nome_pagina}.')
    return redirect('pagina-detail', slug=slug)

def food_view(request):
    """View para solicitar comida - REDIRECIONA PARA HOME"""
    messages.info(request, 'Funcionalidade em desenvolvimento. Em breve você poderá solicitar comida!')
    return redirect('home')

@login_required
def feed_view(request):
    """View para o feed personalizado - REDIRECIONA PARA FEED-POSTAGENS"""
    return redirect('feed-postagens')

def termos_condicoes_view(request):
    return render(request, 'termos_condicoes.html')

@login_required
def excluir_postagem(request, postagem_id):
    """View para excluir uma postagem - VERSÃO CORRIGIDA"""
    if request.method == 'POST':
        try:
            postagem = get_object_or_404(PostagemProduto, id=postagem_id)
            
            # Verificar se o usuário é o dono da página da postagem
            if postagem.pagina.usuario != request.user:
                return JsonResponse({
                    'success': False,
                    'message': 'Você não tem permissão para excluir esta postagem.'
                }, status=403)
            
            titulo_postagem = postagem.titulo or "Postagem sem título"
            
            # Deletar a postagem
            postagem_id = postagem.id
            postagem.delete()
            
            print(f"✅ Postagem {postagem_id} excluída com sucesso por {request.user.email}")
            
            return JsonResponse({
                'success': True,
                'message': f'Postagem "{titulo_postagem}" excluída com sucesso!'
            })
                
        except PostagemProduto.DoesNotExist:
            print(f"❌ Postagem {postagem_id} não encontrada")
            return JsonResponse({
                'success': False,
                'message': 'Postagem não encontrada.'
            }, status=404)
        except Exception as e:
            print(f"❌ Erro ao excluir postagem {postagem_id}: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Erro ao excluir postagem: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido.'
    }, status=405)