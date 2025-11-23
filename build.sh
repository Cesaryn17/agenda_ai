#!/usr/bin/env bash
set -o errexit

echo "🎯 Instalando dependências..."
pip install -r requirements.txt

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "🚀 Aplicando migrações na ordem correta..."

python manage.py migrate auth --noinput
python manage.py migrate contenttypes --noinput
python manage.py migrate sessions --noinput
python manage.py migrate admin --noinput

python manage.py migrate core --noinput

python manage.py migrate produtos --noinput
python manage.py migrate chat --noinput

python manage.py migrate --noinput

echo "✅ Build concluído!"