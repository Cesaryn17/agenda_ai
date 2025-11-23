#!/usr/bin/env bash
set -o errexit

echo "🎯 Instalando dependências..."
pip install -r requirements.txt

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "🚀 Configurando migrações..."

# Criar migrações para cada app individualmente
python manage.py makemigrations core --noinput || echo "⚠️ Nenhuma migração para core"
python manage.py makemigrations produtos --noinput || echo "⚠️ Nenhuma migração para produtos"
python manage.py makemigrations chat --noinput || echo "⚠️ Nenhuma migração para chat"

# Aplicar todas as migrações
python manage.py migrate --noinput

echo "✅ Build concluído!"