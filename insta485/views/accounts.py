"""
Accounts.
/accounts/login/
/accounts/logout/
/accounts/create/
/accounts/delete/
/accounts/edit/
/accounts/password/
/accounts/?target=URL
"""

import uuid
import pathlib
import hashlib
import os
import flask
from flask import (abort, redirect, request, send_from_directory, session,
                   url_for)
import insta485
from insta485.utils import check_password, hash_password, save_current_file
from insta485.utils import is_user_exists, get_file_path



def update_the_password(connection, destination):
    """Update password."""
    if "username" not in session:
        abort(403)
    if request.form["password"] != "":
        password = request.form["password"]
    else:
        abort(400)
    if request.form["new_password1"] != "":
        new_password1 = request.form["new_password1"]
    else:
        abort(400)
    if request.form["new_password2"] != "":
        new_password2 = request.form["new_password2"]
    else:
        abort(400)

    # Query database
    ret = connection.execute(
        "SELECT password" + " FROM users WHERE username == ?",
        [session["username"]]
    )
    gt_password_db_string = ret.fetchone()
    if gt_password_db_string is not None:
        gt_password_db_string = gt_password_db_string["password"]
    else:
        abort(403)

    if check_password(password, gt_password_db_string):
        if new_password1 == new_password2:
            connection.execute(
                "UPDATE users SET password = ? " + "WHERE username = ?",
                (hash_password(new_password1), session["username"]),
            )
            return redirect(destination)
        abort(401)  # Else abort
    else:
        abort(403)
    return None


def delete_this_account(connection, destination):
    """Delete an account."""
    if "username" not in session:
        abort(403)

    # Get users' posts from db
    cur = connection.execute(
        "SELECT filename FROM posts " +
        "WHERE owner = ?", (session["username"],)
    )
    posts = cur.fetchall()

    # Delete posts files
    for post in posts:
        img_path = post["filename"]
        img_path = os.path.join(insta485.app.config
                                ["UPLOAD_FOLDER"], img_path)
        os.remove(img_path)

    # Get user pic from db and delete
    cur = connection.execute(
        "SELECT * FROM users WHERE " +
        "username == ?",
        [session["username"]]
    )
    img_path = cur.fetchone()["filename"]
    img_path = os.path.join(insta485.app.config["UPLOAD_FOLDER"], img_path)
    os.remove(img_path)

    # Delete table entries for user
    connection.execute("DELETE FROM posts "
                       "WHERE owner == ?", [session["username"]])
    connection.execute(
        "DELETE FROM comments WHERE owner == ?", [session["username"]]
    )
    connection.execute("DELETE FROM likes " +
                       "WHERE owner == ?",
                       [session["username"]])
    connection.execute(
        "DELETE FROM following WHERE username1 == ? " +
        "OR username2 == ?",
        [session["username"], session["username"]],
    )
    connection.execute(
        "DELETE FROM users WHERE username == ?", [session["username"]]
    )

    # Clear session and redirect
    session.clear()
    return redirect(destination)


def create_new_account(connection, destination):
    """Create a new account."""
    username = request.form["username"]
    password = request.form["password"]
    fullname = request.form["fullname"]
    email = request.form["email"]
    if "file" not in request.files:
        abort(400)
    # Checks to make sure none of the fields are empty
    if username is None or password is None \
            or fullname is None or email is None:
        abort(400)

    # Query to find username in database
    cur = connection.execute(
        "SELECT users.username " +
        "FROM users " +
        "WHERE users.username = ? ",
        (username,),
    )

    user_results = cur.fetchall()

    # If user_results is not empty, user must
    # already exist in the database.
    if user_results:
        abort(409)
    # If the user_results is empty, we insert all
    # the necessary data to the database
    else:
        # Encrypt the password
        password_db_string = hash_password(password)
        filename = str(save_current_file())

        # Inserts new user data to the users table
        connection.execute(
            "INSERT INTO users(username, password, fullname, "
            " email, filename, created) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (username, password_db_string, fullname, email, filename),
        )

        # Log in the user
        session["username"] = username
        return redirect(destination)
    return None


def edit_account(connection, destination):
    """Edit an account."""
    if "username" not in session or \
            not is_user_exists(session["username"]):
        abort(403)

    # Get form information
    fullname = request.form["fullname"]
    email = request.form["email"]

    # Check if fullname or email is empty
    if fullname == "" or email == "":
        abort(400)

    # If no file is provided
    if "file" not in request.files:
        connection.execute(
            "UPDATE users SET fullname = ?, email = ? " +
            "WHERE username = ?",
            [fullname, email, session["username"]],
        )
    # If file is provided, delete old file and update
    else:
        cur = connection.execute(
            "SELECT * FROM users " +
            "WHERE username == ?",
            [session["username"]]
        )
        img_path = cur.fetchone()["filename"]
        img_path = os.path.join(insta485.app.config
                                ["UPLOAD_FOLDER"], img_path)
        os.remove(img_path)

        file_path = str(save_current_file())

        connection.execute(
            "UPDATE users SET fullname = ?, email = ?, filename = ? "
            + "WHERE username = ?",
            [fullname, email, file_path, session["username"]],
        )
    ret = connection.execute("SELECT * FROM users ")
    users = ret.fetchall()
    for user in users:
        print(user)
    return redirect(destination)


def start_login(connection, destination):
    """Initiate login."""
    username = request.form["username"]
    password = request.form["password"]

    # Query database
    ret = connection.execute(
        "SELECT password" +
        " FROM users WHERE username == ?",
        (username, )
    )
    gt_password_db_string = ret.fetchone()
    if gt_password_db_string is not None:
        gt_password_db_string = gt_password_db_string["password"]
    else:
        abort(403)
    if check_password(password, gt_password_db_string):
        # if password is correct
        session["username"] = username
        return redirect(destination)
    # if user does not exist, or password is incorrect
    print(f"Incorrect username or password {username} {password}")
    abort(403)
    return None


@insta485.app.route("/accounts/", methods=["POST"])
def account_login():
    """Handle all things accounts (and there's a lot)."""
    # Dealing with some variables ahead of time
    # Connect to database
    connection = insta485.model.get_db()
    destination = request.args.get("target")
    if destination is None:
        destination = url_for("show_index")

    if request.form["operation"] == "login":
        destination = url_for("show_index")
        final_destination = start_login(connection, destination)

    if request.form["operation"] == "update_password":
        final_destination = update_the_password(connection, destination)

    if request.form["operation"] == "create":
        destination = url_for("show_index")
        final_destination = create_new_account(connection, destination)

    if request.form["operation"] == "delete":
        final_destination = delete_this_account(connection, destination)

    if request.form["operation"] == "edit_account":
        final_destination = edit_account(connection, destination)

    return final_destination



@insta485.app.route("/accounts/login/", methods=["GET"])
def login():
    """Display /accounts/login/ route."""
    if "username" in session:
        return redirect(url_for("show_index"))
    return flask.render_template("login.html", )


@insta485.app.route("/accounts/logout/", methods=["POST"])
def logout():
    """Display /accounts/logout/ route."""
    session.pop("username", None)
    return redirect(url_for("login"))


@insta485.app.route("/accounts/create/", methods=["GET"])
def create_account():
    """Display /accounts/create/ route."""
    return flask.render_template("create.html")


@insta485.app.route("/accounts/delete/")
def delete():
    """Display /accounts/create/ route."""
    context = {"logname": session["username"]}
    return flask.render_template("delete.html", **context)


@insta485.app.route("/accounts/edit/")
def edit():
    """Display /accounts/edit/ route."""
    if "username" not in session or \
            not is_user_exists(session["username"]):
        return redirect(url_for("show_index"))

    connection = insta485.model.get_db()
    cur = connection.execute(
        "SELECT * FROM users WHERE username = ?", [session["username"]]
    )
    user = cur.fetchone()

    context = {"logname": session["username"], "user": user}
    return flask.render_template("edit.html", **context)


@insta485.app.route("/accounts/password/")
def edit_password():
    """Display /accounts/password route."""
    if "username" not in session:
        return redirect(url_for("show_index"))
    context = {"logname": session["username"]}
    return flask.render_template("password.html", **context)
