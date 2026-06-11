import sys
try:
    from app import create_app
    print('1. App factory OK')
    app = create_app()
    print('2. App created OK')
    print('3. Blueprints registered OK')
    print('4. DB init OK')
    print('All good! Run: python app.py')
except Exception as e:
    print('ERROR:', str(e), file=sys.stderr)
    import traceback
    traceback.print_exc()

