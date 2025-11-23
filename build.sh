#!/usr/bin/env bash
set -o errexit

echo "🎯 Instalando dependências..."
pip install -r requirements.txt

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "🚀 Aplicando migrações existentes..."
python manage.py migrate --noinput

echo "✅ Build concluído!"