import os
import datetime
import json

from flask import abort

from chocolate import all_auth_tokens, get_dir_path
from chocolate.tables import *

dir_path = get_dir_path()

def generate_log(request, component):
    method = request.method

    token = request.headers.get("Authorization")

    path = request.path

    try:
        data = request.get_json()
    except:
        data = None

    if token and token in all_auth_tokens:
        user = all_auth_tokens[token]["user"]
        if user:
            try:
                user = Users.query.filter_by(name=user).first()
                if user:
                    username = user.name
                else:
                    username = f"token {token}"
            except:
                username = f"token {token}"
        else:
            username = f"token {token}"
    else:
        username = f"Token {token}"

    if username == "Token Bearer null":
        username = "Unknown"

    if not data:
        message = f"Request {method} at {path} from {username}"
    else:
        if "password" in data:
            data["password"] = "********"
        message = (
            f"Request {method} at {path} from {username} with data: {json.dumps(data)}"
        )

    log("INFO", component, message)


def log(log_type, log_composant, log_message):
    the_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log = f"{the_time} - [{log_type}] [{log_composant}] {log_message}\n"
    
    #if file does not exist, create it
    if not os.path.exists(path_join(dir_path, "server.log")):
        with open(path_join(dir_path, "server.log"), "w") as logs:
            logs.write(log)
        return

    with open(path_join(dir_path, "server.log"), "r") as logs:
        if log in logs.read():
            return

    with open(path_join(dir_path, "server.log"), "a") as logs:
        logs.write(log)
    

def path_join(*args):
    return "/".join(args).replace("\\", "/")


def check_authorization(request, token, library=None):
    if token not in all_auth_tokens:
        generate_log(request, "UNAUTHORIZED")
        abort(401)

    username = all_auth_tokens[token]["user"]

    if library:
        the_lib = Libraries.query.filter_by(lib_name=library).first()

        if not the_lib:
            generate_log(request, "ERROR")
            abort(404)

        user = Users.query.filter_by(name=username).first()
        user_in_the_lib = user_in_lib(user.id, the_lib)

        if not user_in_the_lib:
            generate_log(request, "UNAUTHORIZED")
            abort(401)

        if the_lib is None or user is None:
            generate_log(request, "ERROR")
            abort(404)

def user_in_lib(user_id, lib):
    user = Users.query.filter_by(id=user_id).first()

    if not user:
        return False
    
    user_id = str(user.id)

    if type(lib) != dict:
        lib = lib.__dict__

    available_for = str(lib["available_for"]).split(",")

    if lib["available_for"] == None or user_id in available_for:
        return True
    return False