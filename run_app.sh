#!/bin/bash

# 1. Cargar librerías locales extraídas sin sudo
export LD_LIBRARY_PATH=$HOME/my_libs/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# 2. Forzar a Qt a usar el backend X11
export QT_QPA_PLATFORM=xcb

# 3. Activar el entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# 4. Validar si el display está activo
if [ -z "$DISPLAY" ]; then
    echo "⚠️ ERROR: Variable DISPLAY vacía. Asegúrate de conectar con 'ssh -Y'."
    exit 1
fi

echo "🚀 Iniciando aplicación en DISPLAY=$DISPLAY..."
python3 main.py