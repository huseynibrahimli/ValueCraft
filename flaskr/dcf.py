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
        ticker = request.form.get("ticker")
        cagr_years = request.form.get("cagr_years")
        next_page = request.form.get("next_page")
        if ticker is not None:
            try:
                session["ticker"] = request.form.get("ticker")
                session["company_type"] = request.form.get("company_type")
                public.engine.import_data(session["ticker"], session["user_id"])
            except Exception as e:
                print(f"Error in data import: {e}")
                return render_template("dcf/public/statement.html", ticker="ERROR", cagr_years=None)
            else:
                return render_template("dcf/public/statement.html", ticker=session["ticker"], cagr_years=None)
        elif cagr_years is not None:
            cagr_years = float(request.form.get("cagr_years"))
            session["revenue_g"] = float(public.engine.project_revenue(session["ticker"], cagr_years))
            return render_template("dcf/public/statement.html", ticker=session["ticker"], cagr_years=cagr_years)
        elif next_page is not None:
            return redirect(url_for("dcf.public_wacc"))

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


@bp.route("/public/wacc", methods=("GET", "POST"))
def public_wacc():
    if request.method == "POST":
        wacc_type = request.form.get("type")
        next_page = request.form.get("next_page")
        if wacc_type == "auto":
            wacc_calc = wacc.engine.calculate_wacc(session["ticker"])
            session["wacc"] = float(wacc_calc[0])
            cost_debt = "{:.2%}".format(wacc_calc[1])
            session["risk_free"] = float(wacc_calc[2])
            credit_spread = "{:.2%}".format(wacc_calc[3])
            cost_equity = "{:.2%}".format(wacc_calc[4])
            session["equity_risk_premium"] = float(wacc_calc[5])
            beta = "{:.2f}".format(wacc_calc[6])
            session["tax_rate"] = float(wacc_calc[7])
            equity_weight = "{:.2%}".format(wacc_calc[8])
            return render_template("dcf/public/wacc.html", wacc="{:.2%}".format(session["wacc"]),
                                   type=wacc_type, cost_debt=cost_debt, risk_free="{:.2%}".format(session["risk_free"]), credit_spread=credit_spread,
                                   cost_equity=cost_equity, equity_risk_premium="{:.2%}".format(session["equity_risk_premium"]),
                                   beta=beta, tax_rate="{:.2%}".format(session["tax_rate"]), equity_weight=equity_weight)

        elif wacc_type == "manual":
            risk_free = request.form.get("risk_free")
            if risk_free is None:
                return render_template("dcf/public/wacc.html", wacc=None, type=wacc_type)
            else:
                session["risk_free"] = float(request.form["risk_free"])
                credit_spread = float(request.form["credit_spread"])
                session["equity_risk_premium"] = float(request.form["equity_risk_premium"])
                beta = float(request.form["beta"])
                session["tax_rate"] = float(request.form["tax_rate"])
                equity_weight = float(request.form["equity_weight"])
                cost_debt = session["risk_free"] + credit_spread
                cost_equity = session["risk_free"] + (beta * session["equity_risk_premium"])
                session["wacc"] = (cost_debt * (1 - session["tax_rate"]) * (1 - equity_weight)) + (cost_equity * equity_weight)
                return render_template("dcf/public/wacc.html", wacc="{:.2%}".format(session["wacc"]),
                                       type=wacc_type, cost_debt="{:.2%}".format(cost_debt), risk_free="{:.2%}".format(session["risk_free"]),
                                       credit_spread="{:.2%}".format(credit_spread), cost_equity="{:.2%}".format(cost_equity),
                                       equity_risk_premium="{:.2%}".format(session["equity_risk_premium"]), beta="{:.2f}".format(beta),
                                       tax_rate="{:.2%}".format(session["tax_rate"]), equity_weight="{:.2%}".format(equity_weight))
        elif next_page is not None:
            return redirect(url_for("dcf.public_fcf"))

    return render_template("dcf/public/wacc.html", wacc=None, type=None)


@bp.route("/public/fcf", methods=("GET", "POST"))
def public_fcf():
    if request.method == "POST":
        next_page = request.form.get("next_page")
        if next_page is None:
            session["projection_period"] = float(request.form["projection_period"])
            session["convergence_year"] = float(request.form["convergence_year"])
            session["perpetuity_growth"] = float(request.form["perpetuity_growth"])
            session["perpetuity_wacc"] = float(request.form["perpetuity_wacc"])
            session["fcf"] = public.engine.project_fcf(session["ticker"], session["user_id"], session["company_type"], session["revenue_g"], session["tax_rate"],
                                                       session["wacc"], session["projection_period"], session["convergence_year"],
                                                       session["perpetuity_growth"], session["perpetuity_wacc"]).to_json()

            return render_template("dcf/public/fcf.html", fcf=True)
        elif next_page is not None:
            return redirect(url_for("dcf.public_terminal"))

    return render_template("dcf/public/fcf.html", ticker=session["ticker"], revenue_g="{:.2%}".format(session["revenue_g"]),
                           perp_g="{:.4f}".format(session["risk_free"]), perp_wacc="{:.4f}".format(session["risk_free"] + session["equity_risk_premium"]),
                           wacc="{:.2%}".format(session["wacc"]), risk_free="{:.2%}".format(session["risk_free"]),
                           erp="{:.2%}".format(session["equity_risk_premium"]), fcf=False)


@bp.route("/public/fcf-statement")
def fcf_statement():
    html_template_path = f"dcf/temp/FCF_{session['ticker']}{session['user_id']}.html"
    return render_template("dcf/public/fcf_statement.html", html_template_path=html_template_path)


@bp.route("/public/terminal", methods=("GET", "POST"))
def public_terminal():
    if request.method == "POST":
        next_page = request.form.get("next_page")
        if next_page is not None:
            return redirect(url_for("dcf.public_value"))
    terminal_value_calc = public.engine.calc_tv(session["perpetuity_growth"], session["perpetuity_wacc"], session["fcf"], session["projection_period"])
    session["fcff_terminal"] = float(terminal_value_calc[0])
    session["terminal_value"] = float(terminal_value_calc[1])
    session["terminal_value_pv"] = float(terminal_value_calc[2])

    return render_template("dcf/public/terminal.html", ticker=session["ticker"],
                           perpetuity_growth="{:.2%}".format(session["perpetuity_growth"]), perpetuity_wacc="{:.2%}".format(session["perpetuity_wacc"]),
                           fcff_terminal="{:,.0f}".format(session["fcff_terminal"]), terminal_value="{:,.0f}".format(session["terminal_value"]))


@bp.route("/public/value", methods=("GET", "POST"))
def public_value():
    dcf_value = public.engine.calc_dcf(session["ticker"], session["fcf"], session["terminal_value_pv"], session["company_type"])
    target_price = "{:,.2f}".format(dcf_value[0])
    market_price = "{:,.2f}".format(dcf_value[1])
    firm_value = "{:,.0f}".format(dcf_value[2])
    net_debt = "{:,.0f}".format(dcf_value[3])
    equity_value = "{:,.0f}".format(dcf_value[4])
    n_shares = "{:,.0f}".format(dcf_value[5])

    folder_path = "flaskr/templates/dcf/temp"
    files = os.listdir(folder_path)
    for file in files:
        if session["user_id"] in file:
            file_path = os.path.join(folder_path, file)
            os.remove(file_path)

    return render_template("dcf/public/value.html", ticker=session["ticker"], target_price=target_price, market_price=market_price,
                           wacc="{:.2%}".format(session["wacc"]), perpetuity_growth="{:.2%}".format(session["perpetuity_growth"]),
                           terminal_value="{:,.0f}".format(session["terminal_value"]),  equity_value=equity_value, net_debt=net_debt,  firm_value=firm_value,
                           n_shares=n_shares)


@bp.route("/private/statement", methods=("GET", "POST"))
def private_statement():
    if request.method == "POST":
        ticker = request.form.get("company_code")
        next_page = request.form.get("next_page")
        if ticker is not None:
            session["company_code"] = ticker
            upload_file = request.files["my_file"]
            file_path = "flaskr/data/dcf/temp"
            os.makedirs(file_path, exist_ok=True)
            filename = secure_filename(f"{session['user_id']}{session['company_code']}.xlsx")
            file_path = os.path.join(file_path, filename)
            upload_file.save(file_path)
            session["company_statement"] = file_path
            try:
                private.engine.import_data(session["company_statement"], session["company_code"], session["user_id"])
                session["revenue_g"] = float(private.engine.project_revenue(session["company_statement"]))
                return render_template("dcf/private/statement.html", my_file=session["company_statement"])
            except Exception as e:
                print(f"Error importing data: {e}")
                return render_template("dcf/private/statement.html", my_file=None, company_code="ERROR")

        elif next_page is not None:
            return redirect(url_for("dcf.private_wacc"))

    return render_template("dcf/private/statement.html", my_file=None)


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


@bp.route("/private/wacc", methods=("GET", "POST"))
def private_wacc():
    if request.method == "POST":
        beta_type = request.form.get("type")
        next_page = request.form.get("next_page")
        if beta_type == "non_beta":
            risk_free = request.form.get("risk_free")
            if risk_free is None:
                return render_template("/dcf/private/wacc.html", wacc=None, type=beta_type)
            else:
                session["risk_free"] = float(risk_free)
                credit_spread = float(request.form["credit_spread"])
                session["equity_risk_premium"] = float(request.form["equity_risk_premium"])
                beta = float(request.form["beta"])
                session["tax_rate"] = float(request.form["tax_rate"])
                equity_weight = float(request.form["equity_weight"])
                cost_debt = session["risk_free"] + credit_spread
                cost_equity = session["risk_free"] + (beta * session["equity_risk_premium"])
                session["wacc"] = (cost_debt * (1 - session["tax_rate"]) * (1 - equity_weight)) + (cost_equity * equity_weight)
                return render_template("/dcf/private/wacc.html", wacc="{:.2%}".format(session["wacc"]), type=beta_type,
                                       cost_debt="{:.2%}".format(cost_debt), cost_equity="{:.2%}".format(cost_equity), beta="{:.2f}".format(beta))
        elif beta_type == "beta":
            industry = request.form.get("industry")
            benchmark = request.form.get("benchmark")
            beta = request.form.get("beta")
            cap = request.form.get("cap")
            if industry is None and benchmark is None and beta is None:
                return render_template("/dcf/private/wacc.html", wacc=None, type=beta_type, industry=None, cap=cap)
            elif industry is not None and benchmark is None and beta is None:
                list_check = wacc.engine.beta_reference_list(industry, cap, session["company_code"], session["user_id"])
                if list_check.empty:
                    return render_template("/dcf/private/wacc.html", wacc=None, type=beta_type, industry=None, cap=cap)
                else:
                    return render_template("/dcf/private/wacc.html",  wacc=None, type=beta_type, industry=industry, cap=None, beta=None)
            elif industry is None and benchmark is not None and beta is None:
                session["tax_rate"] = float(request.form["tax_rate"])
                session["equity_weight"] = float(request.form["equity_weight"])
                company_beta = wacc.engine.calculate_beta(benchmark, session["tax_rate"],  session["equity_weight"])
                if company_beta == "na":
                    return render_template("/dcf/private/wacc.html", wacc=None, type=beta_type, industry="checked", cap="checked", beta=None)
                else:
                    session["beta"] = float(company_beta[0])
                    session["risk_free"] = float(company_beta[1])
                    session["equity_risk_premium"] = float(company_beta[2])
                    return render_template("/dcf/private/wacc.html", wacc=None, type=beta_type, industry="checked", cap=None,
                                           beta="{:.2f}".format(session["beta"]), risk_free="{:.4f}".format(session["risk_free"]),
                                           equity_risk_premium="{:.4f}".format(session["equity_risk_premium"]),
                                           tax_rate="{:.4f}".format(session["tax_rate"]),
                                           equity_weight="{:.4f}".format(session["equity_weight"]))
            else:
                credit_spread = float(request.form["credit_spread"])
                cost_debt = session["risk_free"] + credit_spread
                cost_equity = session["risk_free"] + (session["beta"] * session["equity_risk_premium"])
                session["wacc"] = (cost_debt * (1 - session["tax_rate"]) * (1 - session["equity_weight"])) + (cost_equity * session["equity_weight"])
                return render_template("/dcf/private/wacc.html", wacc="{:.2%}".format(session["wacc"]), type=beta_type,
                                       cost_debt="{:.2%}".format(cost_debt), cost_equity="{:.2%}".format(cost_equity), beta="{:.2f}".format(session["beta"]))

        elif next_page is not None:
            return redirect(url_for("dcf.private_fcf"))

    return render_template("/dcf/private/wacc.html", wacc=None, type=None)


@bp.route("/private/beta")
def private_beta():
    html_template_path = f"dcf/temp/Beta_private_{session['company_code']}{session['user_id']}.html"
    return render_template("dcf/private/beta.html", html_template_path=html_template_path)


@bp.route("/private/fcf", methods=("GET", "POST"))
def private_fcf():
    if request.method == "POST":
        next_page = request.form.get("next_page")
        if next_page is None:
            session["projection_period"] = float(request.form["projection_period"])
            session["convergence_year"] = float(request.form["convergence_year"])
            session["perpetuity_growth"] = float(request.form["perpetuity_growth"])
            session["perpetuity_wacc"] = float(request.form["perpetuity_wacc"])
            session["fcf"] = private.engine.project_fcf(session["company_statement"], session["company_code"], session["user_id"], session["revenue_g"],
                                                        session["tax_rate"], session["wacc"], session["projection_period"], session["convergence_year"],
                                                        session["perpetuity_growth"], session["perpetuity_wacc"]).to_json()

            return render_template("dcf/private/fcf.html", fcf=True)
        elif next_page is not None:
            return redirect(url_for("dcf.private_terminal"))

    return render_template("dcf/private/fcf.html", revenue_g="{:.2%}".format(session["revenue_g"]),
                           perp_g="{:.4f}".format(session["risk_free"]), perp_wacc="{:.4f}".format(session["risk_free"] + session["equity_risk_premium"]),
                           wacc="{:.2%}".format(session["wacc"]), risk_free="{:.2%}".format(session["risk_free"]),
                           erp="{:.2%}".format(session["equity_risk_premium"]), fcf=False)


@bp.route("/private/fcf-statement")
def private_fcf_statement():
    html_template_path = f"dcf/temp/FCF_private_{session['company_code']}{session['user_id']}.html"
    return render_template("dcf/private/fcf_statement.html", html_template_path=html_template_path)


@bp.route("/private/terminal", methods=("GET", "POST"))
def private_terminal():
    if request.method == "POST":
        next_page = request.form.get("next_page")
        net_debt = request.form.get("net_debt")

        if net_debt is not None:
            session["net_debt"] = float(request.form["net_debt"])
            terminal_value_calc = private.engine.calc_tv(session["perpetuity_growth"], session["perpetuity_wacc"], session["fcf"], session["projection_period"])
            session["fcff_terminal"] = float(terminal_value_calc[0])
            session["terminal_value"] = float(terminal_value_calc[1])
            session["terminal_value_pv"] = float(terminal_value_calc[2])

            return render_template("dcf/private/terminal.html", perpetuity_growth="{:.2%}".format(session["perpetuity_growth"]),
                                   perpetuity_wacc="{:.2%}".format(session["perpetuity_wacc"]), fcff_terminal="{:,.0f}".format(session["fcff_terminal"]),
                                   terminal_value="{:,.0f}".format(session["terminal_value"]))
        if next_page is not None:
            return redirect(url_for("dcf.private_value"))

    return render_template("dcf/private/terminal.html", net_debt=None)


@bp.route("/private/value", methods=("GET", "POST"))
def private_value():
    dcf_value = private.engine.calc_dcf(session["fcf"], session["terminal_value_pv"], session["net_debt"])
    firm_value = "{:,.0f}".format(dcf_value[0])
    equity_value = "{:,.0f}".format(dcf_value[1])

    folder_path = "flaskr/templates/dcf/temp"
    files = os.listdir(folder_path)
    for file in files:
        if session["user_id"] in file:
            file_path = os.path.join(folder_path, file)
            os.remove(file_path)

    return render_template("dcf/private/value.html", wacc="{:.2%}".format(session["wacc"]),
                           perpetuity_growth="{:.2%}".format(session["perpetuity_growth"]),
                           terminal_value="{:,.0f}".format(session["terminal_value"]),
                           equity_value=equity_value, net_debt="{:,.0f}".format(session["net_debt"]),  firm_value=firm_value)
