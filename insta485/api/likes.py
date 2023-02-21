"""API for likes operations."""
import flask
from flask import abort
import insta485
from insta485 import utils


@insta485.app.route("/api/v1/likes/", methods=["POST"])
def add_like():
    """Create a new like with the specific postid."""
    message, logname = utils.authenicate()
    if not logname:
        return flask.jsonify(message), 403

    postid = flask.request.args.get("postid", type=int)
    connection = insta485.model.get_db()
    # check if the postid is valid
    cursor = connection.execute(
        "SELECT postid FROM posts WHERE postid = ?", (postid,))
    if not cursor.fetchone():
        return flask.jsonify({"message": "Invalid postid"}), 403

    # check if the user has already liked the post
    cursor = connection.execute(
        "SELECT likeid FROM likes WHERE owner = ? AND postid = ?", (
            logname, postid)
    )
    ret = cursor.fetchone()
    if ret:
        # already liked the post, return the likeid
        likeid = ret["likeid"]
        return flask.jsonify({
            "likeid": likeid, "url": f"/api/v1/likes/{likeid}/"
        }), 200

    # create a new like
    connection.execute(
        "INSERT INTO likes(owner, postid) " +
        "VALUES (?, ?)", (logname, postid)
    )
    likeid = connection.execute(
        "SELECT likeid "
        " FROM likes WHERE owner = ? AND postid = ?",
        (logname, postid),
    ).fetchone()["likeid"]
    return flask.jsonify({"likeid": likeid,
                          "url": f"/api/v1/likes/{likeid}/"}), 201


@insta485.app.route("/api/v1/likes/<likeid>/", methods=["DELETE"])
def delete_like(likeid):
    """Delete the like with the specific likeid."""
    mess, logname = utils.authenicate()
    if not logname:
        return flask.jsonify(mess), 403

    connection = insta485.model.get_db()
    cursor = connection.execute(
        "SELECT owner FROM likes WHERE likeid = ?", (likeid,)
    )

    owner = cursor.fetchone()

    if not owner:
        abort(404)
    elif owner["owner"] != logname:
        abort(403)

    connection.execute("DELETE FROM likes WHERE likeid = ?", (likeid,))

    return "", 204
