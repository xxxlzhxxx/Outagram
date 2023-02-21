"""API for comments."""
import flask
from flask import abort, request,  jsonify
import insta485
from insta485 import utils


@insta485.app.route('/api/v1/comments/', methods=['POST'])
def post_comment():
    """Add a comment to a post."""
    message, logname = utils.authenicate()
    if not logname:
        return flask.jsonify(message), 403
    connection = insta485.model.get_db()

    postid = request.args.get('postid')
    text = request.json['text']
    connection.execute(
        "INSERT INTO comments(owner, postid, text) "
        "VALUES "
        "(?, ?, ?)",
        (logname, postid, text,)
    )
    commentid = connection.execute(
        "SELECT last_insert_rowid() "
        "FROM comments "
    ).fetchone()['last_insert_rowid()']

    context = {
        "commentid": commentid,
        "lognameOwnsThis": True,
        "owner": logname,
        "ownerShowUrl": f"/users/{format(logname)}/",
        "text": text,
        "url": f"/api/v1/comments/{format(commentid)}/"
    }

    return jsonify(**context), 201


@insta485.app.route('/api/v1/comments/<commentid>/', methods=['DELETE'])
def delete_comment(commentid):
    """Delete a comment."""
    message, logname = utils.authenicate()
    if not logname:
        return flask.jsonify(message), 403
    connection = insta485.model.get_db()

    cursor = connection.execute(
        "SELECT owner "
        "FROM comments "
        "WHERE commentid = ?",
        (commentid,)
    )
    owner = cursor.fetchone()
    if not owner:
        abort(404)
    elif owner['owner'] != logname:
        abort(403)

    cursor = connection.execute(
        "DELETE "
        "FROM comments "
        "WHERE commentid = ?",
        (commentid,)
    )

    return '', 204
