#!/usr/bin/env bash
set -o errexit

echo "🚀 Iniciando build..."

echo "📦 Instalando dependências..."
pip install -r requirements.txt

echo "📊 Aplicando migrações (pulando verificação)..."
python manage.py migrate --noinput

echo "🧹 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "✅ Build concluído!"