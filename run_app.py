import streamlit.web.cli as stcli
import sys

# La ruta al script principal de Streamlit
STREAMLIT_SCRIPT = "web_app.py" 

if __name__ == "__main__":
    # Comando que Streamlit espera para iniciar la aplicación
    # Nota: El argumento '--server.headless=True' es a menudo útil
    # para evitar problemas al abrir el navegador en algunas configuraciones.
    sys.argv = ["streamlit", "run", STREAMLIT_SCRIPT]
    sys.exit(stcli.main())
    