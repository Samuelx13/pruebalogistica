try:
    from flask_sqlalchemy import SQLAlchemy
except ImportError as e:
    raise ImportError("Flask-SQLAlchemy is required. Install it with `pip install flask_sqlalchemy`.") from e

db = SQLAlchemy()
