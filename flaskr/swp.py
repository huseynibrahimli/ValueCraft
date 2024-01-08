from flask import Blueprint, redirect, render_template, request, session, url_for

bp = Blueprint("swp", __name__, url_prefix="/swp")


@bp.route("/", methods=("GET", "POST"))
def index():
    if request.method == "POST":
        app_mode = request.form["app_mode"]

        if app_mode == "IRS":
            return redirect(url_for("swp.ois"))
        elif app_mode == "FX":
            return redirect(url_for("swp.irs"))

    return render_template("swp/index.html")
