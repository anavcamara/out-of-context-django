#!/usr/bin/env bash
# Executado pelo Render a cada deploy. Para na primeira falha.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py importar_cenas dados/cenas.json

# Cria o administrador na primeira vez (o plano gratuito não tem Shell).
# Usa as variáveis DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL e
# DJANGO_SUPERUSER_PASSWORD. Se o usuário já existe, o comando falha e segue.
if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" ]]; then
  python manage.py createsuperuser --no-input || true
fi
