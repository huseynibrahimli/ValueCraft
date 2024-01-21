import pandas as pd
import requests

pd.options.display.float_format = "{:,.0f}".format
pd.set_option("mode.chained_assignment", None)
pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 999)

api_key = "24cb7ed8e2f85f03a04132535646cc5f"


def sp500_list(session_id):
    total_list = requests.get(
        f"https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=100000000000&apikey={api_key}").json()

    sp_list = requests.get(f"https://financialmodelingprep.com/api/v3/dowjones_constituent?apikey={api_key}").json()

    included_companies = pd.DataFrame(sp_list)
    included_companies = included_companies["symbol"]
    included_companies = included_companies.to_list()

    company_list = pd.DataFrame(total_list[0:200])
    company_list = company_list[["symbol", "companyName", "exchangeShortName", "industry", "marketCap", "price"]]
    company_list.set_index("symbol", inplace=True)
    company_list.index.name = None
    company_list.columns = ["Company Name", "Exchange", "Industry", "Market Cap", "Price"]
    company_list.rename_axis("Ticker", axis="columns", inplace=True)
    company_list = company_list[company_list.index.isin(included_companies)]
    company_list["Market Cap"] = company_list["Market Cap"].apply("{:,.0f}".format)
    company_list["Price"] = company_list["Price"].apply("{:.2f}".format)
    company_list.to_html("flaskr/templates/dcf/temp/SP_" + session_id + ".html", classes="dataframe_sp500")

    return company_list


class Public:

    def __init__(self, key):
        self.key = key

    def import_data(self, company, session_id):
        income_statement = requests.get(
            f"https://financialmodelingprep.com/api/v3/income-statement/{company}?apikey={self.key}").json()
        cash_flow = requests.get(
            f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{company}?apikey={self.key}").json()
        balance_sheet = requests.get(
            f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{company}?apikey={self.key}").json()

        df_is = pd.DataFrame(income_statement[0:5])
        df_is = df_is.transpose()
        df_is = df_is[6:32]
        df_is.columns = ["T", "T-1", "T-2", "T-3", "T-4"]
        df_is.index.name = None
        df_is = df_is.rename_axis("Income Statement", axis="columns")
        df_is.iloc[2:, 0:5] = df_is.iloc[2:, 0:5].astype(float)
        df_is.loc[df_is.index.str.contains("Ratio", case=False)] = df_is.loc[
            df_is.index.str.contains("Ratio", case=False)].applymap("{:.2%}".format)
        df_is.to_html("flaskr/templates/dcf/temp/IS_" + company + session_id + ".html",
                      float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        df_cf = pd.DataFrame(cash_flow[0:5])
        df_cf = df_cf.transpose()
        df_cf = df_cf[6:-2]
        df_cf.columns = ["T", "T-1", "T-2", "T-3", "T-4"]
        df_cf.index.name = None
        df_cf = df_cf.rename_axis("Cash Flow Statement", axis="columns")
        df_cf.iloc[2:, 0:5] = df_cf.iloc[2:, 0:5].astype(float)
        df_cf.to_html("flaskr/templates/dcf/temp/CF_" + company + session_id + ".html",
                      float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        df_bs = pd.DataFrame(balance_sheet[0:5])
        df_bs = df_bs.transpose()
        df_bs = df_bs[6:-2]
        df_bs.columns = ["T", "T-1", "T-2", "T-3", "T-4"]
        df_bs.index.name = None
        df_bs = df_bs.rename_axis("Balance Sheet", axis="columns")
        df_bs.iloc[2:, 0:5] = df_bs.iloc[2:, 0:5].astype(float)
        df_bs.to_html("flaskr/templates/dcf/temp/BS_" + company + session_id + ".html",
                      float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        return df_is, df_cf, df_bs

    def project_revenue(self, company, cagr_years):
        income_statement = requests.get(
            f"https://financialmodelingprep.com/api/v3/income-statement/{company}?apikey={self.key}").json()

        default_years = 5

        try:
            count = 0
            revenue_g = []
            actual_period = cagr_years
            for item in income_statement:
                if count <= actual_period:
                    revenue_g.append(item["revenue"])
                    count = count + 1
            revenue_g = (revenue_g[0] / revenue_g[-1]) ** (1 / actual_period) - 1
        except Exception as e:
            print(f"Sufficient information doesn't exist: {e}")
            count = 0
            revenue_g = []
            actual_period = default_years
            for item in income_statement:
                if count <= actual_period:
                    revenue_g.append(item["revenue"])
                    count = count + 1
            revenue_g = (revenue_g[0] / revenue_g[-1]) ** (1 / actual_period) - 1
        
        if revenue_g < 0:
            revenue_g = 0

        return revenue_g

    def project_fcf(self, company, session_id, company_type, revenue_g, tax_rate, wacc, cost_equity, projection_period, convergence_year, perpetuity_growth, perpetuity_wacc):
        income_statement = requests.get(
            f"https://financialmodelingprep.com/api/v3/income-statement/{company}?apikey={self.key}").json()
        cash_flow = requests.get(
            f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{company}?apikey={self.key}").json()

        balance_sheet = requests.get(
            f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{company}?apikey={self.key}").json()

        if convergence_year > projection_period:
            convergence_year = projection_period

        revenue_g_delta = (revenue_g - perpetuity_growth) / (projection_period - convergence_year + 1)
        wacc_delta = (wacc - perpetuity_wacc) / (projection_period - convergence_year + 1)
        cost_equity_delta = (cost_equity - perpetuity_wacc) / (projection_period - convergence_year + 1)

        if company_type == "bank":
            cost_capital = cost_equity
            cost_capital_delta = cost_equity_delta
        else:
            cost_capital = wacc
            cost_capital_delta = wacc_delta

        try:
            df_is = pd.DataFrame(income_statement[0:11])
            df_is = df_is.transpose()
            df_is = df_is[8:32]
            df_is.columns = ["T", "T-1", "T-2", "T-3", "T-4", "T-5", "T-6", "T-7", "T-8", "T-9", "T-10"]
            df_is["T-Average"] = df_is.mean(axis=1)
            df_is["%_revenue"] = df_is["T-Average"] / df_is["T-Average"].iloc[0]
            df_is = df_is.astype(float)

            df_cf = pd.DataFrame(cash_flow[0:11])
            df_cf = df_cf.transpose()
            df_cf = df_cf[8:-2]
            df_cf.columns = ["T", "T-1", "T-2", "T-3", "T-4", "T-5", "T-6", "T-7", "T-8", "T-9", "T-10"]
            df_cf["T-Average"] = df_cf.mean(axis=1)
            df_cf["%_revenue"] = df_cf["T-Average"] / df_is["T-Average"].iloc[0]
            df_cf = df_cf.astype(float)

            df_bs = pd.DataFrame(balance_sheet[0:11])
            df_bs = df_bs.transpose()
            df_bs = df_bs[8:-2]
            df_bs.columns = ["T", "T-1", "T-2", "T-3", "T-4", "T-5", "T-6", "T-7", "T-8", "T-9", "T-10"]
            tangible_common_equity = df_bs.loc["totalStockholdersEquity", :] - df_bs.loc["preferredStock", :] - df_bs.loc["goodwillAndIntangibleAssets", :]
            df_bs.loc["tangible_common_equity", :] = tangible_common_equity
            df_bs["T-Average"] = df_bs.mean(axis=1)
            df_bs = df_bs.astype(float)

        except Exception as e:
            print(f"Sufficient information doesn't exist: {e}")
            df_is = pd.DataFrame(income_statement[0:6])
            df_is = df_is.transpose()
            df_is = df_is[8:32]
            df_is.columns = ["T", "T-1", "T-2", "T-3", "T-4", "T-5"]
            df_is["T-Average"] = df_is.mean(axis=1)
            df_is["%_revenue"] = df_is["T-Average"] / df_is["T-Average"].iloc[0]
            df_is = df_is.astype(float)

            df_cf = pd.DataFrame(cash_flow[0:6])
            df_cf = df_cf.transpose()
            df_cf = df_cf[8:-2]
            df_cf.columns = ["T", "T-1", "T-2", "T-3", "T-4", "T-5"]
            df_cf["T-Average"] = df_cf.mean(axis=1)
            df_cf["%_revenue"] = df_cf["T-Average"] / df_is["T-Average"].iloc[0]
            df_cf = df_cf.astype(float)

            df_bs = pd.DataFrame(balance_sheet[0:6])
            df_bs = df_bs.transpose()
            df_bs = df_bs[8:-2]
            df_bs.columns = ["T", "T-1", "T-2", "T-3", "T-4", "T-5"]
            tangible_common_equity = df_bs.loc["totalStockholdersEquity", :] - df_bs.loc["preferredStock", :] - df_bs.loc["goodwillAndIntangibleAssets", :]
            df_bs.loc["tangible_common_equity", :] = tangible_common_equity
            df_bs["T-Average"] = df_bs.mean(axis=1)
            df_bs = df_bs.astype(float)

        i = 1
        while i <= projection_period:
            if i == 1:
                df_is[f"T+{i}"] = (df_is["T"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
                df_is.loc["revenue_g", f"T+{i}"] = revenue_g
                df_is.loc["cost_capital", f"T+{i}"] = cost_capital
                df_is.loc["discount_factor", f"T+{i}"] = (1 / (1 + cost_capital))
            elif 1 < i < convergence_year:
                df_is[f"T+{i}"] = (df_is[f"T+{i - 1}"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
                df_is.loc["revenue_g", f"T+{i}"] = revenue_g
                df_is.loc["cost_capital", f"T+{i}"] = cost_capital
                df_is.loc["discount_factor", f"T+{i}"] = (1 / (1 + cost_capital)) * df_is.loc["discount_factor", f"T+{i-1}"]
            else:
                revenue_g = revenue_g - revenue_g_delta
                cost_capital = cost_capital - cost_capital_delta
                df_is[f"T+{i}"] = (df_is[f"T+{i - 1}"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
                df_is.loc["revenue_g", f"T+{i}"] = revenue_g
                df_is.loc["cost_capital", f"T+{i}"] = cost_capital
                df_is.loc["discount_factor", f"T+{i}"] = (1 / (1 + cost_capital)) * df_is.loc["discount_factor", f"T+{i - 1}"]

            df_cf[f"T+{i}"] = df_is[f"T+{i}"]["revenue"] * df_cf["%_revenue"]
            i += 1

        if company_type == "bank":
            rotce_ratio = df_is.loc["netIncome", "T-Average"] / df_bs.loc["tangible_common_equity", "T-Average"]
            cf_forecast = {}
            i = 1
            while i <= projection_period:
                t = f"T+{i}"
                cf_forecast[t] = {}
                cf_forecast[t]["Revenue growth rate"] = df_is[t]["revenue_g"]
                cf_forecast[t]["ROTCE"] = rotce_ratio
                cf_forecast[t]["Cost of capital"] = df_is[t]["cost_capital"]
                cf_forecast[t]["Discount factor"] = df_is[t]["discount_factor"]
                cf_forecast[t]["Net income"] = df_is[t]["netIncome"]
                cf_forecast[t]["Tangible common equity"] = df_is[t]["netIncome"] / rotce_ratio
                cf_forecast[t]["Capital charge"] = cf_forecast[t]["Tangible common equity"] * cost_capital
                cf_forecast[t]["FCFE"] = cf_forecast[t]["Net income"] - cf_forecast[t]["Capital charge"]
                cf_forecast[t]["PV(FCFE)"] = cf_forecast[t]["FCFE"] * cf_forecast[t]["Discount factor"]
                i += 1

            cf_forecast = pd.DataFrame(cf_forecast)
            cf_forecast = cf_forecast.astype(float)
            cf_forecast.loc["Revenue growth rate"] = cf_forecast.loc["Revenue growth rate"].apply("{:,.2%}".format)
            cf_forecast.loc["ROTCE"] = cf_forecast.loc["ROTCE"].apply("{:,.2%}".format)
            cf_forecast.loc["Cost of capital"] = cf_forecast.loc["Cost of capital"].apply("{:,.2%}".format)
            cf_forecast.loc["Discount factor"] = cf_forecast.loc["Discount factor"].apply("{:,.4f}".format)
            cf_forecast.to_html("flaskr/templates/dcf/temp/FCF_" + company + session_id + ".html",
                                float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

            return cf_forecast

        else:
            cf_forecast = {}
            i = 1
            while i <= projection_period:
                t = f"T+{i}"
                cf_forecast[t] = {}
                cf_forecast[t]["Revenue growth rate"] = df_is[t]["revenue_g"]
                cf_forecast[t]["Cost of capital"] = df_is[t]["cost_capital"]
                cf_forecast[t]["Discount factor"] = df_is[t]["discount_factor"]
                cf_forecast[t]["EBITDA * (1-Tax rate)"] = df_is[t]["ebitda"] * (1 - tax_rate)
                cf_forecast[t]["Depreciation * Tax rate"] = df_cf[t]["depreciationAndAmortization"] * tax_rate
                cf_forecast[t]["Working capital change"] = df_cf[t]["changeInWorkingCapital"]
                cf_forecast[t]["Capital expenditure"] = df_cf[t]["capitalExpenditure"]
                cf_forecast[t]["FCFF"] = (cf_forecast[t]["EBITDA * (1-Tax rate)"] + cf_forecast[t]["Depreciation * Tax rate"] +
                                          cf_forecast[t]["Working capital change"] + cf_forecast[t]["Capital expenditure"])
                cf_forecast[t]["PV(FCFF)"] = cf_forecast[t]["FCFF"] * cf_forecast[t]["Discount factor"]
                i += 1

            cf_forecast = pd.DataFrame(cf_forecast)
            cf_forecast = cf_forecast.astype(float)
            cf_forecast.loc["Revenue growth rate"] = cf_forecast.loc["Revenue growth rate"].apply("{:,.2%}".format)
            cf_forecast.loc["Cost of capital"] = cf_forecast.loc["Cost of capital"].apply("{:,.2%}".format)
            cf_forecast.loc["Discount factor"] = cf_forecast.loc["Discount factor"].apply("{:,.4f}".format)
            cf_forecast.to_html("flaskr/templates/dcf/temp/FCF_" + company + session_id + ".html",
                                float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

            return cf_forecast

    def calc_tv(self, perpetuity_growth, perpetuity_wacc, fcf, projection_period, company_type):
        fcf = pd.read_json(fcf)
        projection_period = int(projection_period)
        discount_factor = float(fcf[f"T+{projection_period}"]["Discount factor"])

        if company_type == "bank":
            fcf_terminal = float(fcf[f"T+{projection_period}"]["FCFE"])
        else:
            fcf_terminal = float(fcf[f"T+{projection_period}"]["FCFF"])

        if fcf_terminal > 0:
            terminal_value = (fcf_terminal * (1 + perpetuity_growth)) / (perpetuity_wacc - perpetuity_growth)
            terminal_value_pv = max(round(terminal_value * discount_factor), 0)
        else:
            terminal_value = 0
            terminal_value_pv = 0

        return fcf_terminal, terminal_value, terminal_value_pv

    def calc_dcf(self, company, fcf, terminal_value_pv, company_type):
        balance_sheet = requests.get(
            f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{company}?apikey={self.key}").json()
        market_info = requests.get(
            f"https://financialmodelingprep.com/api/v3/quote/{company}?apikey={self.key}").json()

        fcf = pd.read_json(fcf)
        pv_fcff = fcf.iloc[-1].sum()
        firm_value = pv_fcff + terminal_value_pv
        net_debt = balance_sheet[0]["netDebt"]

        if company_type == "bank":
            if firm_value > 0:
                equity_value = firm_value
            else:
                equity_value = 0
        else:
            if firm_value > 0:
                equity_value = max(firm_value - net_debt, 0)
            else:
                equity_value = 0
                firm_value = net_debt

        number_of_shares = market_info[0]["sharesOutstanding"]
        actual_price_per_share = market_info[0]["price"]
        target_price_per_share = equity_value / number_of_shares

        return target_price_per_share, actual_price_per_share, firm_value, net_debt, equity_value, number_of_shares


engine = Public(api_key)
