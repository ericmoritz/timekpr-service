from timekpr_service.service import App
from timekpr_service import queries
import os
from logging import basicConfig, DEBUG, INFO

if __name__ == '__main__':
    app = App()

    os.environ.setdefault("ADMIN_USERS", "")
    os.environ.setdefault("PORT", "5000")
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("DEBUG", "false")

    # parse out the granted users
    app.config["ADMIN_USERS"] = os.environ['ADMIN_USERS'].split(":")
    app.config['q'] = queries
    app.config['DEBUG'] = os.environ['DEBUG'] == 'true'

    if app.config['DEBUG']:
        basicConfig(level=DEBUG)
    else:
        basicConfig(level=INFO)

    app.run(
        host=os.environ['HOST'],
        port=int(os.environ['PORT'])
    )
