import datetime
import numpy_financial as npf
import pandas as pd
import pandas_datareader.data as web
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
            df_is.index.str.contains("Ratio", case=False)].map("{:.2%}".format)
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

        return revenue_g

    def project_fcf(self, company, session_id, revenue_g, company_type, projection_period, revenue_g_year):
        income_statement = requests.get(
            f"https://financialmodelingprep.com/api/v3/income-statement/{company}?apikey={self.key}").json()
        cash_flow = requests.get(
            f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{company}?apikey={self.key}").json()
        financial_ratios = requests.get(
            f"https://financialmodelingprep.com/api/v3/ratios/{company}?apikey={self.key}").json()

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

        start = (datetime.datetime.today() - datetime.timedelta(days=10))
        end = datetime.datetime.now()
        treasury_10Y = web.DataReader("DGS10", "fred", start, end)
        risk_free = treasury_10Y.iloc[-1, 0] / 100

        tax_rate = financial_ratios[0]["effectiveTaxRate"]
        if tax_rate < 0:
            tax_rate = 0

        revenue_g_delta = (revenue_g - risk_free) / (projection_period - revenue_g_year + 1)

        i = 1
        while i <= projection_period:
            if i == 1:
                df_is[f"T+{i}"] = (df_is["T"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
                df_is.loc["revenue_g", f"T+{i}"] = revenue_g
            elif 1 < i < revenue_g_year:
                df_is[f"T+{i}"] = (df_is[f"T+{i - 1}"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
                df_is.loc["revenue_g", f"T+{i}"] = revenue_g
            else:
                revenue_g = revenue_g - revenue_g_delta
                df_is[f"T+{i}"] = (df_is[f"T+{i - 1}"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
                df_is.loc["revenue_g", f"T+{i}"] = revenue_g
            i += 1

        i = 1
        while i <= projection_period:
            df_cf[f"T+{i}"] = df_is[f"T+{i}"]["revenue"] * df_cf["%_revenue"]
            i += 1

        if company_type == "bank":
            cf_forecast = {}
            i = 1
            while i <= projection_period:
                t = f"T+{i}"
                cf_forecast[t] = {}
                cf_forecast[t]["Revenue CAGR"] = df_is[t]["revenue_g"]
                cf_forecast[t]["EBITDA(1-Tax rate)"] = df_is[t]["ebitda"] * (1 - tax_rate)
                cf_forecast[t]["Dep(Tax rate)"] = df_cf[t]["depreciationAndAmortization"] * tax_rate
                cf_forecast[t]["WCInv"] = df_cf[t]["changeInWorkingCapital"]
                cf_forecast[t]["FCInv"] = df_cf[t]["capitalExpenditure"]
                cf_forecast[t]["FCF"] = (cf_forecast[t]["EBITDA(1-Tax rate)"] + cf_forecast[t]["Dep(Tax rate)"] +
                                         cf_forecast[t]["WCInv"] + cf_forecast[t]["FCInv"])
                i += 1

            cf_forecast = pd.DataFrame(cf_forecast)
            cf_forecast = cf_forecast.astype(float)
            cf_forecast.loc["Revenue CAGR"] = cf_forecast.loc["Revenue CAGR"].apply("{:,.2%}".format)
            cf_forecast.to_html("flaskr/templates/dcf/temp/FCF_" + company + session_id + ".html",
                                float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

            return cf_forecast

        else:
            cf_forecast = {}
            i = 1
            while i <= projection_period:
                t = f"T+{i}"
                cf_forecast[t] = {}
                cf_forecast[t]["Revenue CAGR"] = df_is[t]["revenue_g"]
                cf_forecast[t]["EBITDA(1-Tax rate)"] = df_is[t]["ebitda"] * (1 - tax_rate)
                cf_forecast[t]["Dep(Tax rate)"] = df_cf[t]["depreciationAndAmortization"] * tax_rate
                cf_forecast[t]["WCInv"] = df_cf[t]["changeInWorkingCapital"]
                cf_forecast[t]["FCInv"] = df_cf[t]["capitalExpenditure"]
                cf_forecast[t]["FCF"] = (cf_forecast[t]["EBITDA(1-Tax rate)"] + cf_forecast[t]["Dep(Tax rate)"] +
                                         cf_forecast[t]["WCInv"] + cf_forecast[t]["FCInv"])
                i += 1

            cf_forecast = pd.DataFrame(cf_forecast)
            cf_forecast = cf_forecast.astype(float)
            cf_forecast.loc["Revenue CAGR"] = cf_forecast.loc["Revenue CAGR"].apply("{:,.2%}".format)
            cf_forecast.to_html("flaskr/templates/dcf/temp/FCF_" + company + session_id + ".html",
                                float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

            return cf_forecast

    def calc_tv(self, g, wacc, fcf, projection_period):
        fcf = pd.read_json(fcf)
        projection_period = int(projection_period)
        if fcf[f"T+{projection_period}"]["FCF"] > 0:
            terminal_value = (fcf[f"T+{projection_period}"]["FCF"] * (1 + g)) / (wacc - g)
            terminal_value_discounted = max(round(terminal_value / (1 + wacc) ** projection_period), 0)
        else:
            terminal_value_discounted = 0

        return terminal_value_discounted

    def calc_dcf(self, company, wacc, fcf, tv, company_type):
        balance_sheet = requests.get(
            f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{company}?apikey={self.key}").json()
        market_info = requests.get(
            f"https://financialmodelingprep.com/api/v3/quote/{company}?apikey={self.key}").json()

        fcf = pd.read_json(fcf)
        fcf_list = fcf.iloc[-1].tolist()
        fcf_list.insert(0, 0)
        npv = npf.npv(wacc, fcf_list)
        firm_value = tv + npv
        net_debt = balance_sheet[0]["netDebt"]

        if company_type == "bank":
            if firm_value > 0:
                equity_value = firm_value
            else:
                firm_value = net_debt
                equity_value = firm_value
        else:
            if firm_value > 0:
                equity_value = max(firm_value - net_debt, 0)
            else:
                equity_value = 0
            firm_value = equity_value + net_debt

        number_of_shares = market_info[0]["sharesOutstanding"]
        actual_price_per_share = market_info[0]["price"]
        target_price_per_share = equity_value / number_of_shares

        return target_price_per_share, actual_price_per_share, firm_value, net_debt, equity_value, number_of_shares


engine = Public(api_key)