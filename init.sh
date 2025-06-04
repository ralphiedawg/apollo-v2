#!/bin/bash
# Initializes Apollo Env

printf "Initializing python environment \n" 
python3.10 -m venv venv
source venv/bin/activate
printf "Installing Dependencies \n" 
python3 -m pip install -r requirements.txt
printf "Installing LLM Dependencies \n"
ollama pull llama3.2

mkdir -p cache
printf '{ \n "facts":[ \n ] \n }' > cache/long_term_memory.json
touch cache/output.wav

printf "Crating Go Environment \n"
cd go
go mod init 
go build -o apolloctl cmd/apolloctl/main.go

printf "Initialization completed. Run the following commands to run Apollo: \n source venv/bin/activate \n python3 main.py  "
