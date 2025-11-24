#!/usr/bin/env bash
set -o errexit

echo "🚀 Iniciando build..."

echo "📦 Instalando dependências..."
pip install -r requirements.txt

echo "📊 Aplicando migrações..."
python manage.py migrate --noinput

echo "🧹 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "👤 Verificando/Criando superusuário..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    user = User.objects.create_superuser(
        email='admin@agenda.ai',
        password='admin123',
        nome='Administrador'
    )
    print('✅ Superusuário criado: admin@agenda.ai / admin123')
else:
    print('✅ Superusuário já existe')
"

echo "✅ Build concluído!"