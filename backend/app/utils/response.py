from flask import jsonify


def json_response(payload=None, status=200):
    return jsonify(payload or {}), status
