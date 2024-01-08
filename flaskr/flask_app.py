import os

from flask import Flask, redirect, render_template, request, url_for
from flaskr import db
from flaskr import dcf, bsm, swp

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(SECRET_KEY="dev", DATABASE=os.path.join(app.instance_path, "flaskr.sqlite"))

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


if __name__ == "__main__":
    app.run(debug=True)
