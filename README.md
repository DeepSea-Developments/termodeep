# Creación de Ejecutables .exe

Se debe instalar pyinstaller

    pip install -r requirements.txt

Crear el ejecutable:

    pyinstaller -F -c termodeep.spec

El ejecutable se crea en la carpeta `dist`. En esta carpeta se creo un archivo `run.bat` que permite configurar los parametros de calibración.
