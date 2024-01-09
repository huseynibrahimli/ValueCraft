import os
import secrets

from flask import Blueprint, redirect, render_template, request, session, url_for
from flaskr.dcf_sub import public, private, wacc


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


@bp.route("/public/statement", methods=("GET", "POST"))
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


@bp.route("/public/income-statement")
def income_statement():
    html_template_path = f"dcf/temp/IS_{session['ticker']}{session['user_id']}.html"
    return render_template("dcf/public/income_statement.html", html_template_path=html_template_path)


@bp.route("/public/cash-flow")
def cash_flow():
    html_template_path = f"dcf/temp/CF_{session['ticker']}{session['user_id']}.html"
    return render_template("dcf/public/cash_flow.html", html_template_path=html_template_path)


@bp.route("/public/balance-sheet")
def balance_sheet():
    html_template_path = f"dcf/temp/BS_{session['ticker']}{session['user_id']}.html"
    return render_template("dcf/public/balance_sheet.html", html_template_path=html_template_path)


@bp.route("/public/fcf", methods=("GET", "POST"))
def public_fcf():
    if request.method == "POST":
        session["fcf"] = public.engine.project_fcf(session["ticker"], session["user_id"], session["revenue_g"]).to_json()
        return render_template("dcf/public/fcf.html", ticker=session["ticker"],
                               revenue_g="{:.2%}".format(session["revenue_g"]), fcf=True)

    session["revenue_g"] = float(public.engine.project_revenue(session["ticker"]))

    return render_template("dcf/public/fcf.html", ticker=session["ticker"],
                           revenue_g="{:.2%}".format(session["revenue_g"]), fcf=False)


@bp.route("/public/fcf-statement")
def fcf_statement():
    html_template_path = f"dcf/temp/FCF_{session['ticker']}{session['user_id']}.html"
    return render_template("dcf/public/fcf_statement.html", html_template_path=html_template_path)


@bp.route("/public/wacc", methods=("GET", "POST"))
def public_wacc():
    if request.method == "POST":
        wacc_type = request.form["type"]
        if wacc_type == "auto":
            wacc_calc = wacc.engine.calculate_wacc(session["ticker"])
            session["wacc"] = float(wacc_calc[0])
            risk_free = "{:.2%}".format(wacc_calc[1])
            credit_spread = "{:.2%}".format(wacc_calc[2])
            market_return = "{:.2%}".format(wacc_calc[3])
            beta = "{:.2f}".format(wacc_calc[4])
            tax_rate = "{:.2%}".format(wacc_calc[5])
            equity_ratio = "{:.2%}".format(wacc_calc[6])
            return render_template("dcf/public/wacc.html", wacc="{:.2%}".format(session["wacc"]),
                                   type=None, risk_free=risk_free, credit_spread=credit_spread, market_return=market_return,
                                   beta=beta, tax_rate=tax_rate, equity_ratio=equity_ratio)

        elif wacc_type == "manual":
            risk_free = request.form["risk_free"]
            if risk_free is None:
                return render_template("dcf/public/wacc.html", wacc=None, type=wacc_type, risk_free=None,
                                       credit_spread=None, market_return=None, beta=None, tax_rate=None, equity_ratio=None)
            else:
                risk_free = float(request.form["risk_free"])
                credit_spread = float(request.form["credit_spread"])
                market_return = float(request.form["market_return"])
                beta = float(request.form["beta"])
                tax_rate = float(request.form["tax_rate"])
                equity_ratio = float(request.form["equity_ratio"])
                cost_debt = risk_free + credit_spread
                cost_equity = risk_free + (beta * (market_return - risk_free))
                session["wacc"] = (cost_debt * (1 - tax_rate) * (1 - equity_ratio)) + (cost_equity * equity_ratio)
                return render_template("dcf/public/wacc.html", wacc="{:.2%}".format(session["wacc"]),
                                       type=None, risk_free="{:.2%}".format(risk_free),
                                       credit_spread="{:.2%}".format(credit_spread),
                                       market_return="{:.2%}".format(market_return), beta="{:.2f}".format(beta),
                                       tax_rate="{:.2%}".format(tax_rate), equity_ratio="{:.2%}".format(equity_ratio))

    return render_template("dcf/public/wacc.html", wacc=None, type=None, risk_free=None,
                           credit_spread=None, market_return=None, beta=None, tax_rate=None, equity_ratio=None)


@bp.route("/public/terminal", methods=("GET", "POST"))
def public_terminal():
    if request.method == "POST":
        session["growth"] = float(request.form["growth"])
        try:
            session["tv_discounted"] = public.engine.calc_tv(session["growth"], session["wacc"], session["fcf"])
            assert session["growth"] < session["wacc"]
        except AssertionError or OverflowError:
            return render_template("dcf/public/terminal.html", ticker=session["ticker"],
                                   revenue_g="{:.2%}".format(session["revenue_g"]),
                                   wacc="{:.2%}".format(session["wacc"]), growth="ERROR", tv=None)

        else:
            return render_template("dcf/public/terminal.html", ticker=session["ticker"],
                                   revenue_g="{:.2%}".format(session["revenue_g"]),
                                   wacc="{:.2%}".format(session["wacc"]),
                                   growth="{:.2%}".format(session["growth"]),
                                   tv="{:,.0f}".format(session["tv_discounted"]))

    return render_template("dcf/public/terminal.html", ticker=session["ticker"],
                           revenue_g="{:.2%}".format(session["revenue_g"]),
                           wacc="{:.2%}".format(session["wacc"]), growth=None, tv=None)


@bp.route("/public/value", methods=("GET", "POST"))
def public_value():
    dcf_value = public.engine.calc_dcf(session["ticker"], session["wacc"], session["fcf"], session["tv_discounted"])
    target_price = "{:,.2f}".format(dcf_value[0])
    market_price = "{:,.2f}".format(dcf_value[1])
    firm_value = "{:,.0f}".format(dcf_value[2])
    total_debt = "{:,.0f}".format(dcf_value[3])
    equity_value = "{:,.0f}".format(dcf_value[4])
    n_shares = "{:,.0f}".format(dcf_value[5])

    folder_path = "flaskr/templates/dcf/temp"
    files = os.listdir(folder_path)
    for file in files:
        if session["user_id"] in file:
            file_path = os.path.join(folder_path, file)
            os.remove(file_path)

    return render_template("dcf/public/value.html", ticker=session["ticker"],
                           wacc="{:.2%}".format(session["wacc"]), g="{:.2%}".format(session["growth"]),
                           tv="{:,.0f}".format(session["tv_discounted"]), target_price=target_price,
                           market_price=market_price, firm_value=firm_value, total_debt=total_debt,
                           equity_value=equity_value, n_shares=n_shares)