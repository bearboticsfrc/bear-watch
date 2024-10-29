#!/bin/bash

if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root"
  exit 1
fi

# Check if inside venv, if not, create one and or activate
if [ "$VIRTUAL_ENV" == "" ]; then
  if [ ! -f .venv/bin/activate ]; then
    echo "Virtual environment not found. Installing..."
    python3 -m venv .venv
  fi

  echo "Activating virtual environment"
  source .venv/bin/activate
fi

# Check and install Python requirements
if ! python3 -m pip list --disable-pip-version-check | (grep -q "asqlite" && grep -q "aiohttp"); then
  echo "Python requirements not found. Installing..."
  python3 -m pip install -r requirements.txt
fi

# Check and install Nmap
if ! command -v nmap &> /dev/null; then
  echo "Nmap not found. Installing..."
  apt-get update && apt-get install -y nmap
fi

# Start the web server
python3 .
