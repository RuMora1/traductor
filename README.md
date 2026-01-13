# Ventana - Captura con PyQt6 + dxcam

Instrucciones rápidas para ejecutar la aplicación en Windows (entorno virtual recomendado).

Requisitos
- Python 3.10+ (recomendado)
- Git

1) Crear y activar venv (PowerShell)

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
```

2) Instalar dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3) Ejecutar la aplicación

```powershell
.\\.venv\\Scripts\\python.exe main.py
```

Notas
- El script guarda capturas en la carpeta `screenshots/` (se crea automáticamente).
- Si `dxcam` falla en tu sistema, considera instalar `mss` como alternativa (se puede añadir un fallback).
- `requirements.txt` fue generado desde el venv actual; si agregas paquetes actualiza el archivo con `python -m pip freeze > requirements.txt`.

Contacto
- Repo: https://github.com/RuMora1/traductor/tree/develop
