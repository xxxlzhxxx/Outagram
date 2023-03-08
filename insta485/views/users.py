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
from flask import *
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
