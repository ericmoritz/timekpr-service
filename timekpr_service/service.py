from timekpr_service import queries
from flask import Flask, url_for, request, jsonify, Response
from functools import wraps
from logging import getLogger

log = getLogger(__name__)

def trace(val):
    log.debug(val)
    return val

def service_response(f):
    @wraps(f)
    def inner(*args, **kwargs):
        data = f(*args, **kwargs)
        if data:
            return jsonify(data)
        else:
            return Response(status=404)
    return inner

def App():

    app = Flask(__name__)

    @app.route("/")
    @service_response
    def index():
        return _index_data(
            app.config['q'],
            lambda u: url_for("user", username=u.username)
        )


    @app.route("/user/<username>")
    @service_response
    def user(username):
        return _user_data(
            app.config['q'], 
            username,
            url_for("user", username=username),
            url_for("put_timestatus", username=username), 
        )


    @app.route("/user/<username>/timestatus", methods=["PUT"])
    def put_timestatus(username):
        q = app.config['q']

        timestatus = _json_to_timestatus(trace(request.get_json(force=True)))

        q.io_update_timestatus(username, timestatus)
        return no_content()

    return app

def bad_request(body):
    return Response(body, status=400)

def no_content():
    return Response(status=204)

###############################################################################
## Internal
###############################################################################

class MockQ(object):
    def __init__(self, user_list, timestatus):
        self.data = {
            'user_list': user_list,
            'timestatus': timestatus
        }

    def io_user(self, username):
        return next(
            (user for user in self.data['user_list']
            if user.username == username),
            None
        )

    def io_user_list(self):
        return self.data['user_list']

    def io_timestatus(self, username):
        return self.data['timestatus'].get(username)

    def io_update_timestatus(self, username, timestatus):
        self.data['timestatus'][username] = timestatus


def _index_data(q, user_url_cb):
    """
    >>> q = MockQ([queries.User("eric")], {})
    
    >>> _index_data(q, lambda u: "/users/" + u.username)
    {'user': [{'username': 'eric', '@id': '/users/eric'}]}
    """
    return {
        "user": map(
            lambda user: _map_user(user_url_cb(user), user),
            q.io_user_list()
        )
    }


def _user_data(q, username, user_url, timestatus_url):
    """
    >>> q = MockQ(
    ...    [queries.User("eric")], 
    ...    {"eric": queries.TimeStatus(10, False)}
    ... )
    >>> _user_data(
    ...   q,
    ...   "eric",
    ...   "/user/eric",
    ...   "/user/eric/timestatus"
    ... )
    {'username': 'eric', 'timestatus': {'locked': False, 'operation': [{'@type': 'hydra:CreateResourceOperation', 'method': 'PUT'}], '@id': '/user/eric/timestatus', 'time': 10}, '@id': '/user/eric'}

    >>> _user_data(
    ...   q,
    ...   "nobody", 
    ...   "/user/nobody",
    ...   "/user/nobody/timestatus"
    ... ) is None
    True
    """
    user_record = q.io_user(username)
    if user_record:
        user = _map_user(user_url, user_record)
        user['timestatus'] = _map_time_status(
            timestatus_url,
            q.io_timestatus(user_record.username)
        )
        return user


def _map_user(url, user):
    return {
        "@id": url,
        "username": user.username
    }


def _map_time_status(url, timestatus):
    return {
        "@id": url,
        "time": timestatus.time,
        "locked": timestatus.locked,
        "operation": [
            {
                "@type": "hydra:CreateResourceOperation",
                "method": "PUT"
            }
        ]
    }


def _json_to_timestatus(data):
    return queries.TimeStatus(
        data.get('time'),
        data.get('locked')
    )
