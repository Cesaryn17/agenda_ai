from django.urls import path, include
from django.conf import settings
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import views as auth_views
from . import views
from .api_views import SearchAPIView

from .views import (
    home_view, search_view, servico_detail_view, registro_view, login_view,
    anuncio_detail_view, perfil_view, toggle_favorito_view, contact_view,
    about_view, my_ads_view, notifications_view, messages_view, favorites_view,
    history_view, settings_view, categories_view, category_view,
    featured_ads_view, recent_ads_view, create_ad_view, atualizar_perfil,
    upload_foto_perfil, alterar_senha, atualizar_configuracoes, notifications_view,
    help_view, health_check,
    enviar_mensagem_view, editar_anuncio_view, delete_anuncio_view, toggle_status_view,
    edit_ad_view,
    conversa_view,
    view_user_profile,
    clear_history_view, export_history_view, filter_history_view, 
    remove_history_item_view,
    CriarPaginaView,
    PaginaDetailView,
    GerenciarPaginaView,
    CriarPostagemView,
    FeedPostagensView,
    termos_condicoes_view,
    minha_pagina_view,
    seguir_pagina,
    deixar_seguir_pagina,
    feed_view,
    food_view,
    
    MobileRegistroAPIView,
    MobileUserStatsAPIView,
    MobileUserAnunciosAPIView,
    MobileUserFavoritesAPIView,
    MobileUserProfileAPIView,
    UserProfileDetailAPIView,
    UserProfileUpdateAPIView,
    UserProfilePhotoUpdateAPIView,
    CategoriasListAPIView, LocalizacoesListAPIView, CriarAnuncioAPIView
    
)

try:
    from .views import (
        NotificacaoAPIView, UsuarioAPIView, RegistroAPIView, 
        LoginAPIView, HistoricoAPIView, api_clear_history  
    )
    API_VIEWS_AVAILABLE = True
except ImportError:
    NotificacaoAPIView = None
    UsuarioAPIView = None
    RegistroAPIView = None
    LoginAPIView = None
    HistoricoAPIView = None  
    api_clear_history = None  
    API_VIEWS_AVAILABLE = False

urlpatterns = [

    path('', home_view, name='home'),
    path('search/', search_view, name='search'),
    path('servico/<int:servico_id>/', servico_detail_view, name='servico-detail'),
    path('registro/', registro_view, name='registro'),
    path('login/', login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('anuncio/<int:anuncio_id>/', anuncio_detail_view, name='anuncio-detail'),
    path('perfil/', perfil_view, name='perfil'),
    path('favoritos/toggle/<int:anuncio_id>/', toggle_favorito_view, name='toggle-favorito'),
    path('contact/', contact_view, name='contact'),
    path('about/', about_view, name='about'),
    path('meus-anuncios/', my_ads_view, name='my-ads'),
    path('anuncios/editar/<int:anuncio_id>/', editar_anuncio_view, name='editar-anuncio'),
    path('anuncios/delete/<int:anuncio_id>/', delete_anuncio_view, name='delete-anuncio'),
    path('anuncios/toggle-status/<int:anuncio_id>/', toggle_status_view, name='toggle-status'),
    path('criar-anuncio/', create_ad_view, name='create-ad'),
    path('editar-anuncio/<int:anuncio_id>/', edit_ad_view, name='edit-ad'),
    path('anuncio/<int:anuncio_id>/enviar-mensagem/', enviar_mensagem_view, name='enviar-mensagem'),
    path('perfil/<int:pk>/', views.servico_detail_view, name='perfil-detail'),
    path('search/', views.search_results, name='search_results'),
    path('iniciar-conversa/<int:anunciante_id>/', views.iniciar_conversa_view, name='iniciar-conversa'),
    path('iniciar-conversa/<int:anunciante_id>/<int:anuncio_id>/', views.iniciar_conversa_view, name='iniciar-conversa-anuncio'),
    path('enviar-mensagem/', enviar_mensagem_view, name='enviar-mensagem'),
    path('api/search/', SearchAPIView.as_view(), name='api-search'),
    path('api/auth/registro/', RegistroAPIView.as_view(), name='api-registro'),
    path('api/anuncios/categoria/<str:slug>/', views.anuncios_por_categoria, name='anuncios-por-categoria'),
     path('api/categorias/', CategoriasListAPIView.as_view(), name='api-categorias'),
    path('api/localizacoes/', LocalizacoesListAPIView.as_view(), name='api-localizacoes'),
    path('api/anuncios/criar/', CriarAnuncioAPIView.as_view(), name='api-criar-anuncio'),
    path('favoritos/remover/<int:favorito_id>/', views.remover_favorito_view, name='remover-favorito'),
    
    path('historico/', history_view, name='history-view'),
    path('historico/limpar/', clear_history_view, name='clear-history'),
    path('historico/exportar/', export_history_view, name='export-history'),
    path('historico/filtrar/<str:filter_type>/', filter_history_view, name='filter-history'),
    path('historico/remover/<int:item_id>/', remove_history_item_view, name='remove-history-item'),
    path('remover-imagem/<int:imagem_id>/', views.remover_imagem_view, name='remover-imagem'),
    path('api/auth/mobile-registro/', MobileRegistroAPIView.as_view(), name='mobile-registro'),

    path('api/auth/me/stats/', views.user_stats_view, name='user-stats'),

    path('api/mobile/user/stats/', MobileUserStatsAPIView.as_view(), name='mobile-user-stats'),
    path('api/mobile/user/anuncios/', MobileUserAnunciosAPIView.as_view(),  name='mobile-user-anuncios'),
    path('api/mobile/user/favoritos/', MobileUserFavoritesAPIView.as_view(), name='mobile-user-favoritos'),
    path('api/mobile/auth/me/', MobileUserProfileAPIView.as_view(), name='mobile-user-profile'),
    
    path('notificacoes/', notifications_view, name='notifications'),
    path('mensagens/', messages_view, name='messages-view'),
    path('favoritos/', favorites_view, name='favorites'),
    path('configuracoes/', settings_view, name='settings'),
    path('ajuda/', help_view, name='help'),
    path('categorias/', categories_view, name='categories'),
    path('categoria/<slug:slug>/', category_view, name='category'),
    path('destaques/', featured_ads_view, name='featured'),
    path('recentes/', recent_ads_view, name='recent-ads'),
    path('atualizar-perfil/', atualizar_perfil, name='atualizar_perfil'),
    path('upload-foto-perfil/', upload_foto_perfil, name='upload_foto_perfil'),
    path('alterar-senha/', alterar_senha, name='alterar_senha'),
    path('atualizar-configuracoes/', atualizar_configuracoes, name='atualizar_configuracoes'),
    path('anuncios/usuario/<int:user_id>/', views.user_ads_view, name='user_ads'),
    path('conversa/<int:anunciante_id>/', conversa_view, name='conversa'),
    path('perfil/', perfil_view, name='perfil'),
    path('perfil/<int:user_id>/', views.view_user_profile, name='view-user-profile'),
    
    path('api/mobile/user/profile/complete/', UserProfileDetailAPIView.as_view(),name='mobile-user-profile-complete'),
    path('api/mobile/user/profile/update/', UserProfileUpdateAPIView.as_view(), name='mobile-user-profile-update'),
    path('api/mobile/user/profile/photo/', UserProfilePhotoUpdateAPIView.as_view(), name='mobile-user-profile-photo'),
    
    path('pagina/gerenciar/', views.GerenciarPaginaView.as_view(), name='gerenciar-pagina'),
    
    # Ações de seguir/deixar de seguir
    path('pagina/<slug:slug>/seguir/', views.seguir_pagina, name='seguir-pagina'),
    path('pagina/<slug:slug>/deixar-seguir/', views.deixar_seguir_pagina, name='deixar-seguir-pagina'),
    
    # URL de detalhe da página (DEVE VIR POR ÚLTIMO)
   
    
    path('minha-pagina/', minha_pagina_view, name='minha-pagina'),
    path('pagina/criar/', CriarPaginaView.as_view(), name='criar-pagina'),
    path('pagina/<slug:slug>/', PaginaDetailView.as_view(), name='pagina-detail'),
    path('pagina/gerenciar/', GerenciarPaginaView.as_view(), name='gerenciar-pagina'),
    path('postagem/criar/', CriarPostagemView.as_view(), name='criar-postagem'),
    path('feed/', FeedPostagensView.as_view(), name='feed-postagens'),

# Ações de seguir/deixar de seguir
    path('pagina/<slug:slug>/seguir/', seguir_pagina, name='seguir-pagina'),
    path('pagina/<slug:slug>/deixar-seguir/', deixar_seguir_pagina, name='deixar-seguir-pagina'),
    path('termos-condicoes/', termos_condicoes_view, name='termos_condicoes'),
    path('postagem/<int:postagem_id>/excluir/', views.excluir_postagem, name='excluir-postagem'),
    path('pagina/<slug:slug>/', views.PaginaDetailView.as_view(), name='pagina-detail'),
    path('excluir-postagem/<int:postagem_id>/', views.excluir_postagem, name='excluir-postagem'),

# URLs de redirecionamento (para compatibilidade)
    path('comida/', food_view, name='food'),
    path('feed/', views.feed_view, name='feed'),
]

api_patterns = [
    path('health/', health_check, name='health-check'),
]

if API_VIEWS_AVAILABLE and HistoricoAPIView is not None:
    api_patterns += [
        path('historico/', HistoricoAPIView.as_view(), name='api-history'),
        path('historico/limpar/', api_clear_history, name='api-clear-history'),
        
        path('auth/', include([
            path('me/', UsuarioAPIView.as_view(), name='usuario-detalhes'),
            path('registro/', RegistroAPIView.as_view(), name='api-registro'),
            path('login/', LoginAPIView.as_view(), name='api-login'),
            path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
        ])),
        
        path('notificacoes/', NotificacaoAPIView.as_view(), name='api-notificacoes'),
    ]

urlpatterns += [
    path('api/', include(api_patterns)),
]

if settings.DEBUG:
    from django.urls import get_resolver
    from django.http import HttpResponse
    
    def debug_urls(request):
        """View para debug de todas as URLs registradas"""
        resolver = get_resolver()
        urls = []
        
        def extract_urls(pattern_list, base=''):
            for pattern in pattern_list:
                if hasattr(pattern, 'url_patterns'):
                    extract_urls(pattern.url_patterns, base + str(pattern.pattern))
                else:
                    url_info = {
                        'pattern': base + str(pattern.pattern),
                        'name': getattr(pattern, 'name', 'Nenhum'),
                        'callback': str(pattern.callback),
                    }
                    url_info['name'] = url_info['name'] or 'Nenhum'
                    urls.append(url_info)
        
        extract_urls(resolver.url_patterns)
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Debug URLs - Agenda AI</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .url-pattern { font-family: monospace; }
                .url-name { color: #007bff; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>URLs Registradas - Agenda AI</h1>
            <table>
                <tr>
                    <th>Padrão URL</th>
                    <th>Nome</th>
                    <th>Callback</th>
                </tr>
        """
        
        for url_info in sorted(urls, key=lambda x: x['pattern']):
            html_content += f"""
                <tr>
                    <td class="url-pattern">{url_info['pattern']}</td>
                    <td class="url-name">{url_info['name']}</td>
                    <td>{url_info['callback']}</td>
                </tr>
            """
        
        html_content += """
            </table>
        </body>
        </html>
        """
        
        return HttpResponse(html_content)
    
    urlpatterns += [
        path('debug/urls/', debug_urls, name='debug-urls'),
    ]