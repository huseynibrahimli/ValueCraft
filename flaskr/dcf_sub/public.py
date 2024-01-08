import numpy_financial as npf
import pandas as pd
import requests

pd.options.display.float_format = "{:,.0f}".format
pd.set_option("mode.chained_assignment", None)
pd.set_option("display.width", 320)
pd.set_option('display.max_columns', 999)

api_key = "24cb7ed8e2f85f03a04132535646cc5f"


def sp500_list(session_id):
    total_list = requests.get(
        f"https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan=200000000000&apikey={api_key}").json()

    company_list = pd.DataFrame(total_list[0:50])
    company_list = company_list[["symbol", "companyName", "exchangeShortName", "industry", "marketCap", "price"]]
    company_list.set_index("symbol", inplace=True)
    company_list.index.name = None
    company_list.columns = ["Company Name", "Exchange", "Industry", "Market Cap", "Price"]
    company_list.rename_axis("Ticker", axis="columns", inplace=True)
    exchanges = ["NASDAQ", "NYSE", "AMEX"]
    company_list = company_list[company_list["Exchange"].isin(exchanges)]
    company_list["Market Cap"] = company_list["Market Cap"].apply("{:,.0f}".format)
    company_list["Price"] = company_list["Price"].apply("{:.2f}".format)
    company_list.drop(company_list.index[20:], inplace=True)
    company_list.to_html("flaskr/templates/dcf/temp/SP_" + session_id + ".html", classes='dataframe_sp500')

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

    def project_revenue(self, company):
        income_statement = requests.get(
            f"https://financialmodelingprep.com/api/v3/income-statement/{company}?apikey={self.key}").json()
        count = 0
        revenue_g = []
        for item in income_statement:
            if count < 5:
                revenue_g.append(item["revenue"])
                count = count + 1
        revenue_g = (revenue_g[0] / revenue_g[4]) ** 0.25 - 1

        return revenue_g

    def project_fcf(self, company, session_id, revenue_g):
        income_statement = requests.get(
            f"https://financialmodelingprep.com/api/v3/income-statement/{company}?apikey={self.key}").json()
        cash_flow = requests.get(
            f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{company}?apikey={self.key}").json()
        financial_ratios = requests.get(
            f"https://financialmodelingprep.com/api/v3/ratios/{company}?apikey={self.key}").json()

        tax_rate = financial_ratios[0]["effectiveTaxRate"]

        df_is = pd.DataFrame(income_statement[0:5])
        df_is = df_is.transpose()
        df_is = df_is[8:32]
        df_is.columns = ["T", "T-1", "T-2", "T-3", "T-4"]
        df_is["T-Average"] = df_is.mean(axis=1)
        df_is["%_revenue"] = df_is["T-Average"] / df_is["T-Average"].iloc[0]
        df_is = df_is.astype(float)
        i = 1
        while i < 6:
            if i == 1:
                df_is[f"T+{i}"] = (df_is["T"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
            else:
                df_is[f"T+{i}"] = (df_is[f"T+{i - 1}"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
            i += 1

        df_cf = pd.DataFrame(cash_flow[0:5])
        df_cf = df_cf.transpose()
        df_cf = df_cf[8:-2]
        df_cf.columns = ["T", "T-1", "T-2", "T-3", "T-4"]
        df_cf["T-Average"] = df_cf.mean(axis=1)
        df_cf["%_revenue"] = df_cf["T-Average"] / df_is["T-Average"].iloc[0]
        df_cf = df_cf.astype(float)
        i = 1
        while i < 6:
            df_cf[f"T+{i}"] = df_is[f"T+{i}"]["revenue"] * df_cf["%_revenue"]
            i += 1

        cf_forecast = {}
        i = 1
        while i < 6:
            t = f"T+{i}"
            cf_forecast[t] = {}
            cf_forecast[t]["EBITDA(1-Tax rate)"] = df_is[t]["ebitda"] * (1 - tax_rate)
            cf_forecast[t]["Dep(Tax rate)"] = df_cf[t]["depreciationAndAmortization"] * tax_rate
            cf_forecast[t]["WCInv"] = df_cf[t]["changeInWorkingCapital"]
            cf_forecast[t]["FCInv"] = df_cf[t]["capitalExpenditure"]
            cf_forecast[t]["FCF"] = (cf_forecast[t]["EBITDA(1-Tax rate)"] + cf_forecast[t]["Dep(Tax rate)"] +
                                     cf_forecast[t]["WCInv"] + cf_forecast[t]["FCInv"])
            i += 1

        cf_forecast = pd.DataFrame(cf_forecast)
        cf_forecast = cf_forecast.astype(float)
        cf_forecast.to_html("flaskr/templates/dcf/temp/FCF_" + company + session_id + ".html",
                            float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        return cf_forecast

    def calc_tv(self, g, wacc, fcf):
        terminal_value = (fcf["T+5"]["FCF"] * (1 + g)) / (wacc - g)
        terminal_value_discounted = max(round(terminal_value / (1 + wacc) ** 5), 0)

        return terminal_value_discounted

    def calc_dcf(self, company, wacc, fcf, tv):
        balance_sheet = requests.get(
            f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{company}?apikey={self.key}").json()
        market_info = requests.get(
            f"https://financialmodelingprep.com/api/v3/quote/{company}?apikey={self.key}").json()

        fcf_list = fcf.iloc[-1].tolist()
        fcf_list.insert(0, 0)
        npv = npf.npv(wacc, fcf_list)
        firm_value = tv + npv
        debt = balance_sheet[0]["totalDebt"]

        if firm_value > 0:
            equity_value = max(firm_value - debt, 0)
        else:
            equity_value = 0

        firm_value = equity_value + debt
        number_of_shares = market_info[0]["sharesOutstanding"]
        actual_price_per_share = market_info[0]["price"]
        target_price_per_share = equity_value / number_of_shares

        return target_price_per_share, actual_price_per_share, firm_value, debt, equity_value, number_of_shares


engine = Public(api_key)