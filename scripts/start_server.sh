#!/bin/bash

REPO_NAME=pdf-api

# Navigate to the deployment directory
cd /home/ubuntu/$REPO_NAME

# Installing dependencies and setting environment
sudo apt-get update
sudo apt-get install -y python3-venv make
make docker-up
