#!/usr/bin/env bash
set -o errexit

echo "🎯 Instalando dependências..."
pip install -r requirements.txt

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "🗃️ Aplicando migrações..."
python manage.py migrate

echo "👤 Criando superusuário se não existir..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@agenda.ai').exists():
    User.objects.create_superuser('admin@agenda.ai', 'admin123')
"

echo "✅ Build concluído!"