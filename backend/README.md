# Musikii Backend Server
## Developement
Download/Update dependencies :
``uv sync``

Run the development server : 
``uv run fastapi run app.py --reload``

Run unit tests :
``uv run pytest -v``
## Libraries
- [fastapi](https://pypi.org/project/fastapi/) for the REST API
- [aioboto3](https://pypi.org/project/aioboto3/) for S3 file handling
- [SQLAlchemy](https://pypi.org/project/SQLAlchemy/) for database management