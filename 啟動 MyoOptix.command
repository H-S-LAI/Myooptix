#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
cd myooptix_app
python main.py
