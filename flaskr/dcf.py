import os
import secrets

from flask import Blueprint, redirect, render_template, request, session, url_for, make_response
from werkzeug.utils import secure_filename
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
            public.engine.import_data(session["ticker"], session["user_id"])
        except Exception as e:
            print(f"Error in data import: {e}")
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
        except Exception as e:
            print(f"Error in calculating terminal value: {e}")
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


@bp.route("/private/statement", methods=("GET", "POST"))
def private_statement():
    if request.method == "POST":
        session["company_code"] = request.form["company_code"]
        upload_file = request.files["my_file"]

        file_path = "flaskr/data/dcf/temp"
        os.makedirs(file_path, exist_ok=True)

        filename = secure_filename(f"{session['user_id']}{session['company_code']}.xlsx")
        file_path = os.path.join(file_path, filename)

        upload_file.save(file_path)
        session["company_statement"] = file_path

        try:
            private.engine.import_data(session["company_statement"], session["company_code"], session["user_id"])
            return render_template("dcf/private/statement.html", company_code=None, my_file=session["company_statement"])
        except Exception as e:
            print(f"Error importing data: {e}")
            return render_template("dcf/private/statement.html", company_code=None, my_file=None)

    return render_template("dcf/private/statement.html", company_code=None, my_file=None)


@bp.route("/private/download")
def private_download():
    file_path = "flaskr/data/dcf/upload_template.xlsx"
    response = make_response(open(file_path, 'rb').read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=upload_template.xlsx'
    response.headers['Content-Length'] = os.path.getsize(file_path)

    return response


@bp.route("/private/income-statement")
def private_income_statement():
    html_template_path = f"dcf/temp/IS_private_{session['company_code']}{session['user_id']}.html"
    return render_template("dcf/private/income_statement.html", html_template_path=html_template_path)


@bp.route("/private/cash-flow")
def private_cash_flow():
    html_template_path = f"dcf/temp/CF_private_{session['company_code']}{session['user_id']}.html"
    return render_template("dcf/private/cash_flow.html", html_template_path=html_template_path)


@bp.route("/private/fcf", methods=("GET", "POST"))
def private_fcf():
    if request.method == "POST":
        session["fcf"] = private.engine.project_fcf(session["company_statement"], session["revenue_g"], session["company_code"],
                                                    session["user_id"]).to_json()
        return render_template("dcf/private/fcf.html", revenue_g="{:.2%}".format(session["revenue_g"]), fcf=True)

    session["revenue_g"] = float(private.engine.project_revenue(session["company_statement"]))
    return render_template("dcf/private/fcf.html", revenue_g="{:.2%}".format(session["revenue_g"]), fcf=False)


@bp.route("/private/fcf-statement")
def private_fcf_statement():
    html_template_path = f"dcf/temp/FCF_private_{session['company_code']}{session['user_id']}.html"
    return render_template("dcf/private/fcf_statement.html", html_template_path=html_template_path)


@bp.route("/private/wacc", methods=("GET", "POST"))
def private_wacc():
    if request.method == "POST":
        beta_type = request.form["type"]
        if beta_type == "non_beta":
            risk_free = request.form.get("risk_free")
            if risk_free is None:
                return render_template("/dcf/private/wacc.html", type=beta_type, industry=None, cap=None,
                                       benchmark=None, revenue_g=None, wacc=None, risk_free=None, credit_spread=None,
                                       market_return=None, beta=None, tax_rate=None, equity_ratio=None)
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
                return render_template("/dcf/private/wacc.html", type=beta_type, industry=None, cap=None,
                                       benchmark=None, revenue_g="{:.2%}".format(session["revenue_g"]),
                                       wacc="{:.2%}".format(session["wacc"]), risk_free=risk_free, credit_spread=credit_spread,
                                       market_return=market_return, beta=beta, tax_rate=tax_rate, equity_ratio=equity_ratio)

        elif beta_type == "beta":
            risk_free = request.form.get("risk_free")
            industry = request.form.get("industry")
            benchmark = request.form.get("benchmark")
            beta = request.form.get("beta")
            cap = request.form.get("cap")
            tax_rate = request.form.get("tax_rate")
            equity_ratio = request.form.get("equity_ratio")
            credit_spread = request.form.get("credit_spread")
            market_return = request.form.get("market_return")
            if industry is None and benchmark is None and beta is None:
                return render_template("/dcf/private/wacc.html", type=beta_type, industry=None, cap=None,
                                       benchmark=None, revenue_g=None, wacc=None, risk_free=None, credit_spread=None,
                                       market_return=None, beta=None, tax_rate=None, equity_ratio=None)
            else:
                if benchmark is None and beta is None:
                    list_check = wacc.engine.estimate_beta(industry, cap, session["company_code"], session["user_id"])
                    if list_check.empty:
                        return render_template("/dcf/private/wacc.html", type=beta_type, industry=None,
                                               cap=cap, benchmark=None, revenue_g=None, wacc=None, risk_free=None,
                                               credit_spread=None, market_return=None, beta=None, tax_rate=None, equity_ratio=None)
                    else:
                        return render_template("/dcf/private/wacc.html", type=beta_type, industry=industry,
                                               cap=None, benchmark=None, revenue_g=None, wacc=None, risk_free=None, credit_spread=None,
                                               market_return=None, beta=None, tax_rate=None, equity_ratio=None)
                else:
                    if beta is None:
                        company_beta = wacc.engine.calculate_beta(benchmark, float(tax_rate), float(equity_ratio))
                        if company_beta == "na":
                            return render_template("/dcf/private/wacc.html", type=beta_type, industry="VALUE", cap="VALUE",
                                                   benchmark=None, revenue_g=None, wacc=None, risk_free=None, credit_spread=None,
                                                   market_return=None, beta=None, tax_rate=None, equity_ratio=None)
                        else:
                            beta = float(company_beta[0])
                            risk_free = float(company_beta[1])
                            market_return = float(company_beta[2])
                            return render_template("/dcf/private/wacc.html", type=beta_type, industry="VALUE", cap=None,
                                                   benchmark=None, revenue_g=None, wacc=None, risk_free="{:.4f}".format(risk_free),
                                                   credit_spread=None, market_return="{:.4f}".format(market_return),
                                                   beta="{:.2f}".format(beta), tax_rate="{:.4f}".format(float(tax_rate)),
                                                   equity_ratio="{:.4f}".format(float(equity_ratio)))
                    else:
                        risk_free = float(risk_free)
                        credit_spread = float(credit_spread)
                        market_return = float(market_return)
                        beta = float(beta)
                        tax_rate = float(tax_rate)
                        equity_ratio = float(equity_ratio)
                        cost_debt = risk_free + credit_spread
                        cost_equity = risk_free + (beta * (market_return - risk_free))
                        session["wacc"] = (cost_debt * (1 - tax_rate) * (1 - equity_ratio)) + (cost_equity * equity_ratio)
                        return render_template("/dcf/private/wacc.html", type=beta_type, industry=None, cap=None,
                                               benchmark=None, revenue_g="{:.2%}".format(session["revenue_g"]),
                                               wacc="{:.2%}".format(session["wacc"]), risk_free=risk_free, credit_spread=credit_spread,
                                               market_return=market_return, beta=beta, tax_rate=tax_rate, equity_ratio=equity_ratio)

    return render_template("/dcf/private/wacc.html", type=None, industry=None, cap=None, benchmark=None, revenue_g=None,
                           wacc=None, risk_free=None, credit_spread=None, market_return=None, beta=None, tax_rate=None, equity_ratio=None)


@bp.route("/private/beta")
def private_beta():
    html_template_path = f"dcf/temp/Beta_private_{session['company_code']}{session['user_id']}.html"
    return render_template("dcf/private/beta.html", html_template_path=html_template_path)


@bp.route("/private/terminal", methods=("GET", "POST"))
def private_terminal():
    if request.method == "POST":
        session["growth"] = float(request.form["growth"])
        try:
            session["tv_discounted"] = private.engine.calc_tv(session["growth"], session["wacc"], session["fcf"])
            assert session["growth"] < session["wacc"]
        except AssertionError or OverflowError:
            return render_template("dcf/private/terminal.html", revenue_g="{:.2%}".format(session["revenue_g"]),
                                   wacc="{:.2%}".format(session["wacc"]), growth="ERROR", tv=None, debt=None)

        else:
            return render_template("dcf/private/terminal.html", revenue_g="{:.2%}".format(session["revenue_g"]),
                                   wacc="{:.2%}".format(session["wacc"]), growth="{:.2%}".format(session["growth"]),
                                   tv="{:,.0f}".format(session["tv_discounted"]), debt=None)

    return render_template("dcf/private/terminal.html", revenue_g="{:.2%}".format(session["revenue_g"]),
                           wacc="{:.2%}".format(session["wacc"]), growth=None, tv=None, debt=None)


@bp.route("/private/value", methods=("GET", "POST"))
def private_value():
    debt = float(request.args.get("debt", 0))
    dcf_value = private.engine.calc_dcf(session["wacc"], session["fcf"], session["tv_discounted"], debt)
    firm_value = dcf_value[0]
    total_debt = dcf_value[1]
    equity_value = dcf_value[2]

    folder_path = "flaskr/templates/dcf/temp"
    files = os.listdir(folder_path)
    for file in files:
        if session["user_id"] in file:
            file_path = os.path.join(folder_path, file)
            os.remove(file_path)

    return render_template("dcf/private/value.html", wacc="{:.2%}".format(session["wacc"]),
                           g="{:.2%}".format(session["growth"]), tv="{:,.0f}".format(session["tv_discounted"]),
                           firm_value="{:,.0f}".format(firm_value), total_debt="{:,.0f}".format(total_debt),
                           equity_value="{:,.0f}".format(equity_value))