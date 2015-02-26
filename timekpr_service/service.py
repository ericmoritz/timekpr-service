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
        CONTEXT = {
            "vocab": url_for("vocab", _external=True) + "#",
            "hydra": "http://www.w3.org/ns/hydra/core#",
            "operation": "hydra:operation",
            "method": "hydra:method",
            "expects": "hydra:expects", 
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "User": "vocab:User",
            "Index": "vocab:Index",
            "TimeStatus": "vocab:TimeStatus",
            "user": "vocab:user",
            "time": "vocab:time",
            "locked": "vocab:locked",
            "timestatus": "vocab:timestatus",
            "start": "xhtml:start",
            "xhtml": "http://www.w3.org/1999/xhtml/vocab#",
        }
        if data:
            data['@context'] = CONTEXT
            data['start'] = url_for("index", _external=True)
            return jsonify(data)
        else:
            return Response(status=404)
    return inner

def App():

    app = Flask(__name__)

    @app.route("/vocab")
    @service_response
    def vocab():
        return {
            "hydra:supportedClass": [
                {
                    "@id": "Index",
                    "hydra:supportedProperty": [
                        {
                            "@id": "user", 
                            "@type": "hydra:Link"
                        }
                    ]
                },
                {
                    "@id": "User",
                    "hydra:supportedProperty": [
                        {
                            "@id": "timestatus", 
                            "@type": "hydra:Link",
                            "rdfs:range": "TimeStatus"
                        },
                        {
                            "@id": "username"
                        }
                    ]
                },
                {
                    "@id": "TimeStatus",
                    "hydra:supportedProperty": [
                        {
                            "@id": "time", 
                            "rdfs:domain": "TimeStatus",
                            "rdfs:comment": "used time in seconds",
                        },
                        {
                            "@id": "locked", 
                            "rdfs:domain": "TimeStatus",
                            "rdfs:comment": "is the user currently locked out"
                        },
                        {
                            "@id": "user", 
                            "@type": "hydra:Link"
                        },
                    ]
                },
                
                
            ]
    }

    @app.route("/")
    @service_response
    def index():
        return _index_data(
            app.config['q'],
            url_for("index", _external=True), 
            lambda u: url_for("user", username=u.username, _external=True)
        )


    @app.route("/user/<username>")
    @service_response
    def user(username):
        return _user_data(
            app.config['q'], 
            username,
            url_for("user", username=username, _external=True),
            url_for("put_timestatus", username=username, _external=True), 
        )


    @app.route("/user/<username>/timestatus")
    @service_response
    def timestatus(username):
        q = app.config['q']
        user = q.io_user(username)
        if user:
            return _map_time_status(
                url_for("user", username=username, _external=True),
                url_for("timestatus", username=username, _external=True),
                q.io_timestatus(username)
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


def _index_data(q, url, user_url_cb):
    """
    >>> q = MockQ([queries.User("eric")], {})
    
    >>> _index_data(q, "/", lambda u: "/users/" + u.username)
    {'@type': 'Index', 'user': [{'username': 'eric', '@id': '/users/eric', '@type': 'User'}]}
    """
    return {
        "@type": "Index", 
        "@id": url,
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
    {'username': 'eric', 'timestatus': {'locked': False, 'operation': [{'@type': 'hydra:CreateResourceOperation', 'method': 'PUT'}], '@id': '/user/eric/timestatus', '@type': 'TimeStatus', 'time': 10}, '@id': '/user/eric', '@type': 'User'}
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
            user_url,
            timestatus_url,
            q.io_timestatus(user_record.username)
        )
        return user


def _map_user(url, user):
    return {
        "@id": url,
        "@type": "User", 
        "username": user.username
    }


def _map_time_status(user_url, url, timestatus):
    return {
        "@id": url,
        "@type": "TimeStatus",
        "user": user_url,
        "time": timestatus.time,
        "locked": timestatus.locked,
        "operation": [
            {
                "@type": "hydra:CreateResourceOperation",
                "method": "PUT",
                "expects": "TimeStatus"
            }
        ]
    }


def _json_to_timestatus(data):
    return queries.TimeStatus(
        data.get('time'),
        data.get('locked')
    )
