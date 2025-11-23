#!/usr/bin/env bash
set -o errexit

echo "🎯 Instalando dependências..."
pip install -r requirements.txt

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "🗃️ Criando migrações para TODOS os apps..."
python manage.py makemigrations --noinput

echo "🚀 Aplicando TODAS as migrações..."
python manage.py migrate --noinput

echo "✅ Build concluído com migrações aplicadas!"