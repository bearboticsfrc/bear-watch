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
if ! python3 -m pip list --disable-pip-version-check | (grep -q "aiohttp" && grep -q "asqlite" && grep -q "scapy"); then
  echo "Python requirements not found. Installing..."
  python3 -m pip install -r requirements.txt
fi

# Start the web server
python3 .
