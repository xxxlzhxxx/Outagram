"""
Insta485 index (main) view.

URLs include:
/
"""
import os
import arrow
import flask
from flask import (abort, redirect, request, send_from_directory, session,
                   url_for, Flask)

import insta485
from insta485.utils import check_password, hash_password, save_current_file
from insta485.utils import is_user_exists, get_file_path



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
