import secrets

from flask import Blueprint, redirect, render_template, request, session, url_for
from dcf_sub import public


bp = Blueprint("dcf", __name__, url_prefix="/dcf")


@bp.route("/", methods=("GET", "POST"))
def index():
    session.clear()
    session["user_id"] = secrets.token_hex()
    public.sp500_list(session["user_id"])

    if request.method == "POST":
        app_mode = request.form["app_mode"]

        if app_mode == "Public":
            return redirect(url_for("dcf.public_statement"))
        elif app_mode == "Private":
            return redirect(url_for("dcf.private_statement"))

    return render_template("dcf/index.html")


@bp.route("/sp500")
def sp500():
    html_template_path = f"dcf/temp/SP_{session['user_id']}.html"
    return render_template("dcf/sp500.html", html_template_path=html_template_path)


@bp.route("/public-statement", methods=("GET", "POST"))
def public_statement():
    if request.method == "POST":
        session["ticker"] = request.form["ticker"]
        try:
            public.engine.import_data(session["ticker"], session['user_id'])
        except ValueError or TypeError:
            return render_template("dcf/public/statement.html", ticker="ERROR")
        else:
            return render_template("dcf/public/statement.html", ticker=session["ticker"])

    return render_template("dcf/public/statement.html", ticker=None)


@bp.route("/income-statement")
def income_statement():
    html_template_path = f"dcf/temp/IS_{session['ticker']}{session['user_id']}.html"
    return render_template("dcf/public/income_statement.html", html_template_path=html_template_path)


@bp.route("/cash-flow")
def cash_flow():
    html_template_path = f"dcf/temp/CF_{session['ticker']}{session['user_id']}.html"
    return render_template("dcf/public/cash_flow.html", html_template_path=html_template_path)


@bp.route("/balance-sheet")
def balance_sheet():
    html_template_path = f"dcf/temp/BS_{session['ticker']}{session['user_id']}.html"
    return render_template("dcf/public/balance_sheet.html", html_template_path=html_template_path)


