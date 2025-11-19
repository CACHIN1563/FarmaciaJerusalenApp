import sys
import os
import streamlit.web.cli as stcli
from streamlit.web import bootstrap

# El nombre del archivo principal de Streamlit de tu proyecto
STREAMLIT_SCRIPT = "web_app.py" 

def main():
    """Ejecuta el script de Streamlit directamente, evitando el bucle de reinicio."""
    
    # 1. Chequea si Streamlit está en el proceso de "reinicio"
    # Streamlit usa este indicador interno al empaquetarse para saber si ya se reinició.
    if os.environ.get("STREAMLIT_RUN_IN_PROCESS") == "true":
        # Si está en el proceso de reinicio, NO hacemos nada más, permitimos que se ejecute.
        return 
    
    # 2. Verificar si estamos dentro del .exe de PyInstaller
    if getattr(sys, 'frozen', False):
        # Establece la variable de entorno para que el próximo reinicio (si ocurre)
        # sepa que ya estamos dentro del EXE.
        os.environ["STREAMLIT_RUN_IN_PROCESS"] = "true"
        
        print("--- Iniciando Streamlit (Versión EXE) ---")
        
        # Llama directamente a la función de arranque de Streamlit
        # Esto hace el trabajo de "streamlit run web_app.py"
        bootstrap.run(STREAMLIT_SCRIPT, is_hello=False, args=[], flag_options={})
        
    else:
        # Estamos en un entorno normal de Python (para desarrollo)
        print("Ejecutando en modo de desarrollo.")
        sys.argv = ["streamlit", "run", STREAMLIT_SCRIPT]
        sys.exit(stcli.main())

if __name__ == '__main__':
    main()