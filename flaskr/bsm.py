from flask import Blueprint, redirect, render_template, request, session, url_for

bp = Blueprint("bsm", __name__, url_prefix="/bsm")


@bp.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        app_mode = request.form["app_mode"]

        if app_mode == "BSM":
            return redirect(url_for("bsm.bsm"))
        elif app_mode == "MC":
            return redirect(url_for("bsm.mc"))

    return render_template("bsm/index.html")
