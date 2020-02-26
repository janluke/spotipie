# flake8: noqa F401
try:
    from .app import start_authorization_app
except ImportError as exc:
    raise ImportError(f"""
        An import error was raised while trying to import the authorization app.
        This error is likely due to the fact you did not install the optional 
        dependencies required to run the app with the following command:
        
            pip install spotipie[auth-app]
        
        Note that if you
        The error is: {exc}.
    """)
