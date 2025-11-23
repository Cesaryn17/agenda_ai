from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# ✅ USE APENAS ESTA LINHA - remova a importação direta do CustomUser
CustomUser = get_user_model()


@receiver(user_signed_up)
def handle_user_signed_up(request, user, **kwargs):
    """
    Manipula o sinal de usuário registrado
    """
    if not user.nome_utilizador:
        base_name = user.nome.split()[0].lower() if user.nome else 'user'
        user.nome_utilizador = CustomUser.objects.generate_username(base_name)
        user.save()

@receiver(post_save, sender=CustomUser)
def enviar_email_boas_vindas(sender, instance, created, **kwargs):
    """
    Envia email de boas-vindas para novos usuários
    """
    if created:
        try:
            subject = '🎉 Bem-vindo ao Agenda AI!'
            
            html_message = render_to_string('emails/boas_vindas.html', {
                'usuario': instance,
                'nome': instance.nome or instance.email.split('@')[0],
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                'Agenda AI <noreply@agendaai.com>',
                [instance.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erro ao enviar email de boas-vindas: {e}")