@echo off
git stash
echo Сложили локальные изменения.
git fetch
git pull
echo Стянули обновления.
start python JSON_RPC_Server.py
echo Запустили JSON_RPC_Server.py
start python BFF_FASTAPI_Server.py
echo Запустили BFF_FASTAPI_Server.py