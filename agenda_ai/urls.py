from django.contrib import admin
from django.urls import path, include
from core import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from core.views import home_view, servico_detail_view, create_ad, categories_view, anuncio_detail_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home_view, name='home'),
    path('anuncio/criar/', create_ad, name='create_ad'),
    
    path('anuncio/<int:anuncio_id>/', anuncio_detail_view, name='anuncio-detail'), 
    
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/core/', include('core.urls')),
    path('api/produtos/', include('produtos.urls')),
    path('categorias/<slug:slug>/', categories_view, name='category_list'),
    path('travel/', views.travel_view, name='travel'),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)