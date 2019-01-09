# -*- coding: utf-8 -*-
import os
import hashlib
from share import logger
from flask import Blueprint, request, abort

wx = Blueprint("wx", __name__)


def auth():
    signature = request.args.get("signature")
    timestamp = request.args.get("timestamp")
    nonce = request.args.get("nonce")
    echostr = request.args.get("echostr")
    token = os.getenv("WX_TOKEN")
    logger.debug("wx token=%s" % token)
    if not token:
        abort(500)
    _list = [token, timestamp, nonce]
    _list.sort()
    sha1 = hashlib.sha1()
    map(sha1.update, _list)
    hash_code = sha1.hexdigest()
    if hash_code == signature:
        logger.debug("Auth success")
        return echostr
    else:
        return ""


@wx.route("/", methods=["GET", "POST"])
def auth():
    if request.method == "GET":
        return auth()
    else:
        return ""
