from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import CustomUser

CustomUser = get_user_model()

@receiver(pre_save, sender=CustomUser)
def ensure_nome_utilizador(sender, instance, **kwargs):
    """
    Garante que todo usuário tenha um nome_utilizador antes de salvar
    """
    if not instance.nome_utilizador:
        if instance.nome:
            instance.nome_utilizador = CustomUser.objects.generate_username(instance.nome)
        else:
            instance.nome_utilizador = CustomUser.objects.generate_username('user')

@receiver(user_signed_up)
def handle_user_signed_up(request, user, **kwargs):
    """
    Manipula o sinal de usuário registrado
    """
    if not user.nome_utilizador:
        user.nome_utilizador = CustomUser.objects.generate_username(user.nome or 'user')
        user.save()

@receiver(post_save, sender=CustomUser)
def enviar_email_boas_vindas(sender, instance, created, **kwargs):
    if created:
        # Assunto do email
        subject = '🎉 Bem-vindo ao Agenda AI!'
        
        # Renderiza o template HTML
        html_message = render_to_string('emails/boas_vindas.html', {
            'usuario': instance,
            'nome': instance.nome or instance.email.split('@')[0],
        })
        
        # Versão texto simples
        plain_message = strip_tags(html_message)
        
        # Envia o email
        send_mail(
            subject,
            plain_message,
            'Agenda AI <noreply@agendaai.com>',
            [instance.email],
            html_message=html_message,
            fail_silently=False,
        )