from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Prefetch
from .models import Chat, Mensagem
from .serializers import (
    ChatSerializer, MensagemSerializer, CriarMensagemSerializer,
    CriarChatSerializer
)

class ChatListView(generics.ListAPIView):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Chat.objects.filter(
            participantes=user
        ).prefetch_related(
            'participantes',
            Prefetch('mensagens_chat', queryset=Mensagem.objects.order_by('-data_envio')[:1])
        ).order_by('-ultima_mensagem__data_envio')
        
        for chat in queryset:
            chat.outro_usuario = chat.participantes.exclude(id=user.id).first()
            chat.mensagens_nao_lidas = chat.mensagens_chat.filter(lida=False).exclude(remetente=user).count()
            
        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class MensagemListView(generics.ListCreateAPIView):
    serializer_class = MensagemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        chat_id = self.kwargs['chat_id']
        return Mensagem.objects.filter(
            chat_id=chat_id,
            chat__participantes=self.request.user,
            excluida=False
        ).select_related('remetente').prefetch_related('visualizacoes__usuario').order_by('data_envio')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CriarMensagemSerializer
        return MensagemSerializer

    def perform_create(self, serializer):
        chat = Chat.objects.get(id=self.kwargs['chat_id'])
        mensagem = serializer.save(
            remetente=self.request.user,
            chat=chat
        )
        chat.atualizar_ultima_mensagem()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class CriarChatView(generics.CreateAPIView):
    serializer_class = CriarChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        participantes_ids = serializer.validated_data.pop('participantes_ids')
        chat = serializer.save()
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        participantes = User.objects.filter(id__in=participantes_ids)
        chat.participantes.add(self.request.user)
        for participante in participantes:
            chat.participantes.add(participante)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def marcar_mensagens_lidas(request, chat_id):
    Mensagem.objects.filter(
        chat_id=chat_id,
        chat__participantes=request.user
    ).exclude(remetente=request.user).update(lida=True)
    
    return Response({'status': 'success'})

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def excluir_mensagem(request, mensagem_id):
    try:
        mensagem = Mensagem.objects.get(id=mensagem_id, remetente=request.user)
        mensagem.excluida = True
        mensagem.conteudo = "Mensagem excluída"
        mensagem.arquivo = None
        mensagem.save()
        return Response({'status': 'success'})
    except Mensagem.DoesNotExist:
        return Response({'error': 'Mensagem não encontrada'}, status=404)