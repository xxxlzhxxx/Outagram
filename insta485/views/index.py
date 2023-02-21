"""
Insta485 index (main) view.

URLs include:
/
"""
import os
import arrow
import flask
from flask import (abort, redirect, request, send_from_directory, session,
                   url_for)

import insta485
from insta485.utils import check_password, hash_password, save_current_file
from insta485.utils import is_user_exists, get_file_path


def is_following(username1, username2):
    """If user1 is following user2."""
    connection = insta485.model.get_db()
    res = connection.execute(
        "SELECT * FROM following WHERE username1 == ? AND username2 == ?",
        [username1, username2],
    )
    return res.fetchone() is not None


def get_fullname(username):
    """Get fullname of user."""
    connection = insta485.model.get_db()
    res = connection.execute(
        "SELECT fullname FROM users WHERE username = ?", [username]
    )
    return res.fetchone()["fullname"]


@insta485.app.route("/")
def show_index():
    """Display / route."""
    if "username" in flask.session:
        logged_name = flask.session["username"]
    else:
        return flask.redirect(flask.url_for("login"))
    # Add database info to context
    context = {"logname": logged_name}
    return flask.render_template("index.html", **context)


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


@insta485.app.route("/accounts/login/", methods=["GET"])
def login():
    """Display /accounts/login/ route."""
    if "username" in session:
        return redirect(url_for("show_index"))
    return flask.render_template("login.html")


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


@insta485.app.route("/users/<username>/", methods=["POST", "GET"])
def user_page(username):
    """Tbh have no idea what this does lol."""
    connection = insta485.model.get_db()
    if "username" not in session or not is_user_exists(session["username"]):
        return redirect(url_for("login"))
    if "username" not in session:
        return redirect(url_for("show_index"))
    # number of followers
    ret = connection.execute(
        "SELECT COUNT(*) AS num_followers" +
        " FROM following WHERE username2 == ?",
        [username],
    )
    num_followers = ret.fetchone()["num_followers"]

    # number of following
    ret = connection.execute(
        "SELECT COUNT(*) AS num_following" +
        " FROM following WHERE username1 == ?",
        [username],
    )
    num_following = ret.fetchone()["num_following"]

    # query posts
    ret = connection.execute(
        "SELECT postid, filename, owner, created" +
        " FROM posts WHERE owner == ?",
        [username],
    )
    posts = ret.fetchall()
    # add to context
    context = {}
    context["logname"] = session["username"]
    context["username"] = username
    context["logname_follows_username"] =\
        is_following(session["username"], username)
    context["fullname"] = get_fullname(username)
    context["following"] = num_following
    context["followers"] = num_followers
    context["total_posts"] = len(posts)
    context["posts"] = []
    for post in posts:
        context["posts"].append(
            {"postid": post["postid"], "img_url":
                get_file_path(post["filename"])}
        )
    return flask.render_template("user.html", **context)


@insta485.app.route("/explore/", methods=["GET"])
def explore():
    """Explore page."""
    if "username" not in session or \
            not is_user_exists(session["username"]):
        return redirect(url_for("login"))
    connection = insta485.model.get_db()
    logname = session["username"]
    # find all unfollowed users
    ret = connection.execute(
        "SELECT * FROM users"
        + " WHERE username != ? AND username NOT IN"
        + " (SELECT username2 FROM following WHERE username1 == ?)",
        [logname, logname],
    )
    users = ret.fetchall()
    context = {}
    context["logname"] = logname
    context["not_following"] = []
    for user in users:
        context["not_following"].append(
            {
                "username": user["username"],
                "user_img_url": get_file_path(user["filename"]),
            }
        )
    return flask.render_template("explore.html", **context)


@insta485.app.route("/users/<user_url_slug>/followers/",
                    methods=["POST", "GET"])
def show_followers(user_url_slug):
    """Display /users/<user_url_slug>/followers/ route."""
    if "username" not in session or not is_user_exists(session["username"]):
        return redirect(url_for("login"))

    connection = insta485.model.get_db()
    logname = session["username"]

    # Query database
    cur = connection.execute(
        "SELECT username, filename FROM users "
        + "WHERE username IN "
        + "(SELECT username1 FROM following WHERE username2 = ?)",
        (user_url_slug,),
    )
    followers = cur.fetchall()

    for follower in followers:
        follower["logname_follows_user"] = is_following(logname,
                                                        follower["username"])

    # Add database info to context
    context = {"followers": followers, "logname": logname}

    return flask.render_template("followers.html", **context)


@insta485.app.route("/users/<user_url_slug>/following/", methods=["GET"])
def following(user_url_slug):
    """Display users/<user_url_slug>/following/ route."""
    if "username" not in session or not is_user_exists(session["username"]):
        return redirect(url_for("login"))

    logged_name = flask.session["username"]

    # Connect to database
    connection = insta485.model.get_db()

    # Checking to see if someone is trying to
    # access a user that doesn't exist
    cur = connection.execute(
        "SELECT username, filename "
        "FROM users "
        "WHERE username = ?", (logged_name,)
    )
    current_user = cur.fetchone()
    if current_user is None:
        flask.abort(404)

    # If request just wants to display information
    # Need to show people that user_url_slug is following
    # The following relation is username1 (user_url_slug)
    # follows username2 (people following)
    follow = connection.execute(
        "SELECT users.username, users.filename AS profile_pic, "
        "EXISTS (SELECT 1 FROM following WHERE following.username1 = ? "
        "AND following.username2 = users.username) AS is_following "
        "FROM following, users "
        "WHERE following.username1 = ? AND "
        "following.username2 = users.username",
        (logged_name, user_url_slug),
    )

    # Returns a tuple in format: (<username>, <profile_pic>, <is_following>)
    all_following = follow.fetchall()

    # Add database info to context
    context = {
        "following": all_following,
        "page_owner": user_url_slug,
        "current_user": logged_name,
    }
    return flask.render_template("following.html", **context)


@insta485.app.route("/posts/<postid_url_slug>/")
def show_post(postid_url_slug):
    """Display / route."""
    if "username" not in session or not is_user_exists(session
                                                       ["username"]):
        return redirect(url_for("login"))
    connection = insta485.model.get_db()
    # Query database
    logname = session["username"]
    cur = connection.execute("SELECT * FROM posts WHERE postid = "
                             + postid_url_slug)
    post = cur.fetchall()
    post[0]["created"] = arrow.get(post[0]["created"],
                                   "YYYY-MM-DD HH:mm:ss").humanize()

    cur = connection.execute(
        "SELECT * "
        "FROM comments "
        "WHERE postid = " + postid_url_slug)
    all_comments = cur.fetchall()

    cur = connection.execute(
        "SELECT * "
        "FROM likes "
        "WHERE postid = " + postid_url_slug)
    all_likes = cur.fetchall()

    user_liked = 0
    for like in all_likes:
        if like["owner"] == logname:
            user_liked = 1

    cur = connection.execute(
        "SELECT filename FROM users WHERE username = ?", (post[0]["owner"],)
    )
    user = cur.fetchall()

    # Add database info to context
    context = {
        "post": post,
        "comments": all_comments,
        "likes": all_likes,
        "user": user,
        "user_liked": user_liked,
        "logname": logname,
    }
    return flask.render_template("post.html", **context)


@insta485.app.route("/following/", methods=["POST"])
def post_following():
    """Update the following page."""
    if "username" not in session or not is_user_exists(session["username"]):
        return redirect(url_for("login"))
    target_url = request.args.get("target")
    connection = insta485.model.get_db()
    logname = session["username"]
    target_name = request.form["username"]
    operation = request.form["operation"]
    if operation == "follow":
        ret = connection.execute(
            "SELECT * FROM following "
            "WHERE username1 == ?"
            " AND username2 == ?",
            [logname, target_name],
        )
        if ret.fetchone() is None:
            connection.execute(
                "INSERT INTO following (username1, username2) "
                "VALUES (?, ?)",
                [logname, target_name],
            )
        else:
            abort(409)
    elif operation == "unfollow":
        ret = connection.execute(
            "SELECT * FROM following WHERE username1 == ?"
            "AND username2 == ?",
            [logname, target_name],
        )
        if ret.fetchone() is not None:
            connection.execute(
                "DELETE FROM following WHERE username1 == ? "
                "AND username2 == ?",
                [logname, target_name],
            )
        else:
            abort(409)
    if target_url is None:
        return redirect(url_for("show_index"))
    return redirect(target_url)


@insta485.app.route("/posts/", methods=["POST"])
def post_posts():
    """Update posts when something changes."""
    target_url = request.args.get("target")
    if "username" not in session or not is_user_exists(session["username"]):
        return redirect(url_for("login"))
    connection = insta485.model.get_db()
    logname = session["username"]
    operation = request.form["operation"]
    if operation == "create":
        if "file" not in request.files:
            abort(400)
        file_path = str(save_current_file())
        ret = connection.execute(
            "INSERT INTO posts (owner, filename) "
            "VALUES (?, ?)", (logname, file_path)
        )
    elif operation == "delete":
        postid = request.form["postid"]
        ret = connection.execute(
            "SELECT * FROM posts WHERE postid = ? "
            "AND owner = ?", [postid, logname]
        )
        if ret.rowcount == 0:
            abort(403)
        img_path = ret.fetchone()["filename"]
        # remove the image
        img_path = os.path.join(insta485.app.config["UPLOAD_FOLDER"], img_path)
        os.remove(img_path)
        connection.execute("DELETE FROM posts WHERE postid = ?", [postid])
        connection.execute("DELETE FROM comments WHERE postid = ?", [postid])
        connection.execute("DELETE FROM likes WHERE postid = ?", [postid])
    if target_url is None:
        return redirect(f"/users/{logname}/")
    return redirect(target_url)


@insta485.app.route("/comments/", methods=["POST"])
def comments():
    """Post comments to page."""
    if "username" not in session or not is_user_exists(session["username"]):
        return redirect(url_for("login"))
    target_url = request.args.get("target")

    connection = insta485.model.get_db()
    logname = session["username"]

    if request.form["operation"] == "create":
        # Get values from form
        postid = request.form["postid"]
        owner = logname
        text = request.form["text"]

        if text == "":
            abort(400)

        # Insert comment into db
        connection.execute(
            "INSERT INTO comments(owner, postid, text) " + "VALUES (?, ?, ?)",
            (owner, postid, text),
        )
        if target_url is None:
            return redirect("/")
        return redirect(target_url)
    # Get value from form
    commentid = request.form["commentid"]

    # Delete comment from db
    connection.execute(
        "DELETE FROM comments "
        "WHERE commentid = ?", [commentid]
    )
    if target_url is None:
        return redirect("/")
    return redirect(target_url)


@insta485.app.route("/uploads/<file_name>")
def share_file(file_name):
    """Update uploads if new change in feed."""
    if file_name != "instaLogo.png":
        if 'username' not in session:
            abort(403)
        if not is_user_exists(session['username']):
            abort(403)
    file_path = os.path.join(insta485.app.config["UPLOAD_FOLDER"], file_name)
    if os.path.isfile(file_path):
        return send_from_directory(
            insta485.app.config["UPLOAD_FOLDER"], file_name, as_attachment=True
        )
    abort(404)
    return None


@insta485.app.route("/likes/", methods=["POST"])
def likes():
    """Update likes."""
    if "username" not in session or not is_user_exists(session["username"]):
        return redirect(url_for("login"))
    target_url = request.args.get("target")

    if target_url is None:
        return redirect(url_for("show_index"))

    connection = insta485.model.get_db()
    logname = session["username"]
    postid = request.form["postid"]

    if request.form["operation"] == "like":
        # Get likes on post from db, then check if user has liked post
        cur = connection.execute(
            "SELECT * FROM likes "
            "WHERE postid = " + postid
        )
        all_likes = cur.fetchall()

        for like in all_likes:
            if like["owner"] == logname:
                abort(409)

        # Add like to db
        connection.execute(
            "INSERT INTO likes(owner, postid) " +
            "VALUES (?, ?)", (logname, postid)
        )
        return redirect(target_url)
    # Get likes on post from db, then check if user has liked post
    cur = connection.execute(
        "SELECT * FROM likes "
        "WHERE postid = " + postid)
    all_likes = cur.fetchall()

    count = 0
    for like in all_likes:
        if like["owner"] == logname:
            count = 1
    if count != 1:
        abort(409)

    # Delete like from db
    connection.execute(
        "DELETE FROM likes "
        "WHERE postid = ? AND owner = ?", (postid, logname)
    )
    return redirect(target_url)
