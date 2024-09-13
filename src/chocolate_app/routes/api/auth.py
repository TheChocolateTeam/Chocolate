import os
import jwt
import base64
import datetime

from PIL import Image
from io import BytesIO
from functools import wraps
from flask import Blueprint, request, current_app

from chocolate_app import get_dir_path
from chocolate_app.tables import Users
from chocolate_app.utils.utils import generate_response, Codes

dir_path = get_dir_path()
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def image_to_base64(
    image_path: str, width: int | None = None, height: int | None = None
) -> str:
    image_base64 = None
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    if width and height:
        image = Image.open(BytesIO(base64.b64decode(image_base64)))
        image = image.resize((width, height))
        buffered = BytesIO()

        image.save(buffered, format="JPEG")

        image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return image_base64


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        access_token = None

        if "Authorization" in request.headers:
            access_token = request.headers["Authorization"]

        if not access_token:
            return generate_response(Codes.MISSING_DATA, True)

        splited_token = access_token.split(" ")

        if len(splited_token) != 2:
            return generate_response(Codes.INVALID_TOKEN, True)

        access_token = splited_token[1]
        try:
            data = jwt.decode(
                access_token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            current_user = Users.query.filter_by(id=data["id"]).first()
        except Exception as e:
            return generate_response(Codes.INVALID_TOKEN, True)

        if "current_user" in f.__code__.co_varnames:
            return f(current_user, *args, **kwargs)
        else:
            return f(*args, **kwargs)

    return decorated


@auth_bp.route("/check", methods=["POST"])
@token_required
def check_auth(current_user):
    profile_picture = os.path.join(dir_path, current_user.profile_picture)
    return generate_response(
        Codes.SUCCESS,
        False,
        {
            "username": current_user.name,
            "account_type": current_user.account_type,
            "account_id": current_user.id,
            "profile_picture": f"data:image/jpeg;base64,{image_to_base64(profile_picture, 200, 200)}",
        },
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    account_name = ""
    if "name" not in request.get_json() and not "username" in request.get_json():
        return generate_response(Codes.MISSING_DATA, True)
    elif "name" not in request.get_json():
        account_name = request.get_json()["username"]
    else:
        account_name = request.get_json()["name"]

    account_password = request.get_json()["password"]
    user = Users.query.filter_by(name=account_name).first()

    if not user:
        return generate_response(Codes.USER_NOT_FOUND, True)

    if not Users.verify_password(user, account_password):
        return generate_response(Codes.WRONG_PASSWORD, True)

    access_token = jwt.encode(
        {
            "id": user.id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=3),
        },
        current_app.config["SECRET_KEY"],
    )

    refresh_token = jwt.encode(
        {"id": user.id, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=2)},
        current_app.config["SECRET_KEY"],
    )

    profile_picture = os.path.join(dir_path, user.profile_picture)

    user_object = {
        "username": user.name,
        "account_type": user.account_type,
        "account_id": user.id,
        "profile_picture": f"data:image/jpeg;base64,{image_to_base64(profile_picture, 200, 200)}",
    }

    return generate_response(
        Codes.SUCCESS,
        False,
        {
            "user": user_object,
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    )


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    token = request.get_json()["refresh_token"]
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        current_user = Users.query.filter_by(id=data["id"]).first()
    except:
        return generate_response(Codes.INVALID_TOKEN, True)

    access_token = jwt.encode(
        {
            "id": current_user.id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=3),
        },
        current_app.config["SECRET_KEY"],
    )

    img_path = os.path.join(dir_path, current_user.profile_picture)

    user_object = {
        "username": current_user.name,
        "account_type": current_user.account_type,
        "account_id": current_user.id,
        "profile_picture": f"data:image/jpeg;base64,{image_to_base64(img_path, 200, 200)}",
    }

    return generate_response(
        Codes.SUCCESS,
        False,
        {
            "id": current_user.id,
            "name": current_user.name,
            "account_type": current_user.account_type,
            "access_token": access_token,
            "user": user_object,
        },
    )


@auth_bp.route("/accounts", methods=["GET"])
def get_accounts():
    all_users = Users.query.filter().all()
    all_users_list = []
    for user in all_users:
        profile_picture = user.profile_picture
        if not os.path.exists(dir_path + profile_picture):
            profile_picture = "/static/img/avatars/defaultUserProfilePic.png"

        image_base64 = None
        with open(dir_path + profile_picture, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

        image = Image.open(BytesIO(base64.b64decode(image_base64)))
        image = image.resize((200, 200))
        buffered = BytesIO()

        image.save(buffered, format="JPEG")

        user_dict = {
            "name": user.name,
            "profile_picture": "data:image/jpeg;base64,"
            + base64.b64encode(buffered.getvalue()).decode("utf-8"),
            "account_type": user.account_type,
            "password_empty": True if not user.password else False,
            "id": user.id,
        }
        all_users_list.append(user_dict)
    return generate_response(Codes.SUCCESS, False, all_users_list)
