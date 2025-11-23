from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.http import HttpRequest
from django.core.exceptions import ValidationError
from .models import CustomUser

class CustomAccountAdapter(DefaultAccountAdapter):
    
    def is_open_for_signup(self, request: HttpRequest):
        return True

    def save_user(self, request, user, form, commit=True):
        """
        Sobrescreve o método save_user para evitar referências ao campo username
        """
        user = super().save_user(request, user, form, commit=False)

        if form.cleaned_data.get('nome'):
            user.nome = form.cleaned_data['nome']
        if form.cleaned_data.get('telefone'):
            user.telefone = form.cleaned_data['telefone']
        if form.cleaned_data.get('termos_aceitos'):
            user.termos_aceitos = form.cleaned_data['termos_aceitos']
        
        if not user.nome_utilizador and user.nome:
            user.nome_utilizador = CustomUser.objects.generate_username(user.nome)
        elif not user.nome_utilizador:
            user.nome_utilizador = CustomUser.objects.generate_username('user')
        
        if commit:
            user.save()
        return user

    def populate_username(self, request, user):
        """
        Sobrescreve para evitar tentativas de popular username
        """
        pass

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    
    def is_open_for_signup(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        """
        Popula o usuário para login social sem referências a username
        """
        user = super().populate_user(request, sociallogin, data)
        
        extra_data = sociallogin.account.extra_data
        
        if not user.nome:
            if extra_data.get('name'):
                user.nome = extra_data.get('name')
            elif extra_data.get('given_name') and extra_data.get('family_name'):
                user.nome = f"{extra_data.get('given_name')} {extra_data.get('family_name')}"
            elif extra_data.get('given_name'):
                user.nome = extra_data.get('given_name')
            else:
                user.nome = user.email.split('@')[0]
        
        if not user.nome_utilizador:
            user.nome_utilizador = CustomUser.objects.generate_username(user.nome)
        
        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Salva o usuário de login social sem referências a username
        """
        user = sociallogin.user
    
        if not user.nome:
            user.nome = user.email.split('@')[0]
        
        if not user.nome_utilizador:
            user.nome_utilizador = CustomUser.objects.generate_username(user.nome)
        
        try:
            user.full_clean()
        except ValidationError as e:
            print(f"Validation error during social login: {e}")
        
        sociallogin.save(request)
        return user

    def pre_social_login(self, request, sociallogin):
        """
        Conecta contas sociais existentes
        """
        if sociallogin.is_existing:
            return

        try:
            user = CustomUser.objects.get(email=sociallogin.user.email)
            sociallogin.connect(request, user)
        except CustomUser.DoesNotExist:
            pass

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        User = get_user_model()
        
        # Preenche o email
        if not user.email and data.get('email'):
            user.email = data.get('email')
        
        # Gera um nome_utilizador único baseado no email
        if not user.nome_utilizador and user.email:
            base_username = user.email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(nome_utilizador=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            user.nome_utilizador = username
        
        # Preenche o nome se disponível
        if not user.nome:
            user.nome = data.get('name', 'Usuário')
            
        return user