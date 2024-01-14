import os

from flask import Flask, redirect, render_template, request, url_for, send_from_directory
from flaskr import db
from flaskr import dcf, bsm, swp
from werkzeug.exceptions import InternalServerError


app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(SECRET_KEY="c01a9df280f6d5bb42e36781c7738112b942f9d02ce700ac97877c2067ec9f99",
                        DATABASE=os.path.join(app.instance_path, "flaskr.sqlite"))

try:
    os.makedirs(app.instance_path)
except OSError:
    pass

app.register_blueprint(dcf.bp)
app.register_blueprint(bsm.bp)
app.register_blueprint(swp.bp)

with app.app_context():
    db.init_db()


@app.route("/", methods=("GET", "POST"))
def projects():
    if request.method == "POST":
        project_type = request.form["project_type"]

        if project_type == "DCF":
            return redirect(url_for("dcf.index"))
        elif project_type == "BSM":
            return redirect(url_for("bsm.index"))
        elif project_type == "SWP":
            return redirect(url_for("swp.index"))

    return render_template("projects.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"), "favicon/favicon.ico", mimetype="image/vnd.microsoft.icon")


@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    return send_from_directory(os.path.join(app.root_path, "static"), "favicon/apple-touch-icon.png", mimetype="image/vnd.microsoft.icon")


@app.errorhandler(Exception)
def handle_error(error):
    return render_template("projects.html")


@app.errorhandler(InternalServerError)
def handle_internal_server_error(error):
    return render_template("projects.html")


@app.errorhandler(KeyError)
def handle_key_error(error):
    return render_template("projects.html")


if __name__ == "__main__":
    app.run(debug=True)