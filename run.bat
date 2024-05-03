@echo off
git stash
echo Сложили локальные изменения.
git fetch
git pull
echo Стянули обновления.

IF NOT EXIST .env (
    echo HOST_IP='127.0.0.1' > .env
    echo Создали .env файл.
)

start python JSON_RPC_Server.py
echo Запустили JSON_RPC_Server.py
start python BFF_FASTAPI_Server.py
echo Запустили BFF_FASTAPI_Server.py