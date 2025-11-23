import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Chat, Mensagem, MensagemVisualizacao
from .serializers import MensagemSerializer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.room_group_name = f'chat_{self.chat_id}'
        self.user = self.scope["user"]

        if await self.verificar_acesso_chat():
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_join',
                    'user_id': str(self.user.id),
                    'username': self.user.username
                }
            )
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_leave',
                'user_id': str(self.user.id),
                'username': self.user.username
            }
        )

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                data = json.loads(text_data)
                message_type = data.get('type')
                
                if message_type == 'chat_message':
                    await self.processar_mensagem_texto(data)
                elif message_type == 'typing':
                    await self.processar_digitando(data)
                elif message_type == 'message_read':
                    await self.marcar_mensagem_lida(data)
                elif message_type == 'delete_message':
                    await self.excluir_mensagem(data)
                    
            elif bytes_data:
                await self.processar_arquivo(bytes_data)
                
        except Exception as e:
            await self.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def processar_mensagem_texto(self, data):
        mensagem_data = {
            'chat': self.chat_id,
            'conteudo': data.get('message'),
            'tipo': data.get('tipo', 'texto'),
            'respondendo_a': data.get('respondendo_a')
        }
        
        mensagem = await self.salvar_mensagem(mensagem_data)
        serializer = MensagemSerializer(mensagem)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': serializer.data,
                'user_id': str(self.user.id)
            }
        )

    async def processar_arquivo(self, bytes_data):
        pass

    async def processar_digitando(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing',
                'user_id': str(self.user.id),
                'username': self.user.username,
                'is_typing': data['is_typing']
            }
        )

    async def marcar_mensagem_lida(self, data):
        mensagem_id = data.get('message_id')
        await self.marcar_mensagem_como_lida(mensagem_id)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_read',
                'message_id': mensagem_id,
                'user_id': str(self.user.id)
            }
        )

    async def excluir_mensagem(self, data):
        mensagem_id = data.get('message_id')
        success = await self.excluir_mensagem_db(mensagem_id)
        
        if success:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': mensagem_id,
                    'user_id': str(self.user.id)
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user_id': event['user_id']
        }))

    async def typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def message_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'user_id': event['user_id']
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'user_id': event['user_id']
        }))

    async def user_join(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'user_id': event['user_id'],
            'username': event['username']
        }))

    async def user_leave(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'user_id': event['user_id'],
            'username': event['username']
        }))

    @database_sync_to_async
    def verificar_acesso_chat(self):
        if isinstance(self.user, AnonymousUser):
            return False
        return Chat.objects.filter(id=self.chat_id, participantes=self.user).exists()

    @database_sync_to_async
    def salvar_mensagem(self, data):
        chat = Chat.objects.get(id=data['chat'])
        mensagem = Mensagem.objects.create(
            chat=chat,
            remetente=self.user,
            conteudo=data['conteudo'],
            tipo=data['tipo']
        )
        chat.atualizar_ultima_mensagem()
        return mensagem

    @database_sync_to_async
    def marcar_mensagem_como_lida(self, mensagem_id):
        try:
            mensagem = Mensagem.objects.get(id=mensagem_id, chat__participantes=self.user)
            mensagem.marcar_como_lida()
            MensagemVisualizacao.objects.get_or_create(
                mensagem=mensagem,
                usuario=self.user
            )
            return True
        except:
            return False

    @database_sync_to_async
    def excluir_mensagem_db(self, mensagem_id):
        try:
            mensagem = Mensagem.objects.get(id=mensagem_id, remetente=self.user)
            mensagem.excluida = True
            mensagem.conteudo = "Mensagem excluída"
            mensagem.arquivo = None
            mensagem.save()
            return True
        except:
            return False