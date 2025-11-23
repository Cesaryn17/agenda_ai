import django_filters
from .models import Anuncio

class AnuncioFilter(django_filters.FilterSet):
    min_valor = django_filters.NumberFilter(field_name="valor", lookup_expr='gte')
    max_valor = django_filters.NumberFilter(field_name="valor", lookup_expr='lte')
    categoria = django_filters.CharFilter(field_name='categoria__slug')
    tipo = django_filters.CharFilter(field_name='tipo')
    
    class Meta:
        model = Anuncio
        fields = ['categoria', 'tipo', 'destaque']