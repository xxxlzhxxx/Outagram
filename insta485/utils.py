"""Untiles."""
import hashlib
import pathlib
import uuid
import flask
from flask import request

import insta485


def save_current_file():
    """Save current flask request file to uploads folder."""
    # Unpack flask object
    fileobj = flask.request.files["file"]
    filename = fileobj.filename
    # Compute base name (filename without directory).  We use a UUID to avoid
    # clashes with existing files, and ensure that the name is compatible
    # with the filesystem. For best practive, we ensure uniform file
    # extensions (e.g. lowercase).
    stem = uuid.uuid4().hex
    suffix = pathlib.Path(filename).suffix.lower()
    uuid_basename = f"{stem}{suffix}"
    # Save to disk
    path = insta485.app.config["UPLOAD_FOLDER"] / uuid_basename
    fileobj.save(path)
    # print(f"====== {uuid_basename} =====")
    # print(f"====== {path} =====")
    return uuid_basename


def is_user_exists(username):
    """If user exists in database."""
    connection = insta485.model.get_db()
    res = connection.execute(
        "SELECT username FROM users WHERE username == ?", [username]
    )
    return res.fetchone() is not None


def get_file_path(filename):
    """Get file path of file."""
    return "/uploads/" + filename


def hash_password(password, salt=None):
    """Hash password."""
    algorithm = "sha512"
    if salt is None:
        salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + password
    hash_obj.update(password_salted.encode("utf-8"))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])
    return password_db_string


def check_password(password, password_db_string):
    """Check if password is correct, adds salt."""
    salt = password_db_string.split("$")[1]
    password_db_string_new = hash_password(password, salt)
    return password_db_string == password_db_string_new


def authenicate():
    """Check if the user is logged in or not."""
    auth = request.authorization
    if not auth:
        if "username" not in flask.session:
            return {"message": "Forbidden: auth needed"}, None

        if not is_user_exists(flask.session["username"]):
            return {"message": "Forbidden: user name does not exist"}, None
        return {"message": f"Auth: {flask.session['username']}"
                }, flask.session["username"]

    username, password = auth.username, auth.password
    connection = insta485.model.get_db()
    ret = connection.execute(
        "SELECT password" + " FROM users WHERE username == ?", (username,)
    )
    gt_password_db_string = ret.fetchone()
    if gt_password_db_string is not None:
        gt_password_db_string = gt_password_db_string["password"]
        if check_password(password, gt_password_db_string):
            # if password is correct
            return {
                "message": f"Auth: {username}",
            }, username
        return {
            "message": "Forbidden: password is incorrect",
        }, None
    return {
        "message": "Forbidden: user name does not exist",
    }, None
