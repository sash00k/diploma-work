@echo off
git stash
echo Local changes stashed.

git fetch
git pull
echo Updates fetched and pulled.

start python JSON_RPC_Server.py
echo Running JSON_RPC_Server.py

start python BFF_FASTAPI_Server.py
echo Running BFF_FASTAPI_Server.py