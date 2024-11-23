#/bin/bash

if [ -f .env ]; then
  set -a
  source ./.env
  set +a
else
  echo ".env file not found!"
  exit 1
fi

python3 bot.py