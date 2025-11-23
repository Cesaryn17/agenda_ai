from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from .models import CustomUser
from django import forms
from .models import PostagemProduto

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'nome', 'nome_utilizador')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'nome', 'nome_utilizador', 'is_active', 'is_staff', 'is_superuser')

class CustomSignupForm(SignupForm):
    username = None
    
    nome = forms.CharField(max_length=255, label="Nome Completo", required=True)
    telefone = forms.CharField(max_length=20, required=False, label="Telefone")
    termos_aceitos = forms.BooleanField(required=True, label="Aceito os termos de uso")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']

    def save(self, request):
        user = super().save(request)
        
        user.nome = self.cleaned_data['nome']
        user.telefone = self.cleaned_data['telefone']
        user.termos_aceitos = self.cleaned_data['termos_aceitos']
    
        user.nome_utilizador = CustomUser.objects.generate_username(user.nome)
        
        user.save()
        return user

class CustomSignupForm(SignupForm):
    nome = forms.CharField(
        max_length=255, 
        required=True, 
        label="Nome Completo",
        widget=forms.TextInput(attrs={'placeholder': 'Seu nome completo'})
    )
    
    # Remove o campo username do formulário
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']
    
    def save(self, request):
        # Chama o save original mas não usa username
        user = super().save(request)
        user.nome = self.cleaned_data['nome']
        
        # Gera um nome_utilizador único baseado no email
        base_username = user.email.split('@')[0]
        username = base_username
        counter = 1
        while CustomUser.objects.filter(nome_utilizador=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.nome_utilizador = username
        
        user.save()
        return user

class CriarPostagemForm(forms.ModelForm):
    # Não vamos usar um campo de mídias no form Django
    # Vamos lidar com isso manualmente na view
    
    class Meta:
        model = PostagemProduto
        fields = ['titulo', 'descricao', 'produto_relacionado', 'localizacao', 'hashtags']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite um título atraente...',
                'maxlength': '200'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Conte mais sobre seu produto ou serviço...',
                'rows': 4,
                'maxlength': '2200'
            }),
            'produto_relacionado': forms.Select(attrs={
                'class': 'form-select'
            }),
            'localizacao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Onde você está?'
            }),
            'hashtags': forms.HiddenInput()
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Importar Anuncio do app produtos
        try:
            from produtos.models import Anuncio
            if user and hasattr(user, 'pagina_pessoal'):
                self.fields['produto_relacionado'].queryset = Anuncio.objects.filter(usuario=user)
        except ImportError:
            # Se o app produtos não existir, deixar o queryset vazio
            self.fields['produto_relacionado'].queryset = self.fields['produto_relacionado'].queryset.none()