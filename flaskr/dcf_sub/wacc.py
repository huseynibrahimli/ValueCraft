import datetime
import pandas as pd
import pandas_datareader.data as web
import requests

pd.options.display.float_format = "{:,.4f}".format
pd.set_option("mode.chained_assignment", None)
pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 999)

api_key = "24cb7ed8e2f85f03a04132535646cc5f"


class WACC:

    def __init__(self, key):
        self.key = key

    def calculate_wacc(self, company):
        income_statement = requests.get(
            f"https://financialmodelingprep.com/api/v3/income-statement/{company}?apikey={self.key}").json()
        company_profile = requests.get(
            f"https://financialmodelingprep.com/api/v3/profile/{company}?apikey={self.key}").json()
        financial_ratios = requests.get(
            f"https://financialmodelingprep.com/api/v3/ratios/{company}?apikey={self.key}").json()

        interest_coverage_ratio = ((income_statement[0]["ebitda"] - income_statement[0]["depreciationAndAmortization"])
                                   / income_statement[0]["interestExpense"])

        # https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ratings.html
        credit_bands = {8.5: 0.0059, 6.5: 0.007, 5.5: 0.0092, 4.25: 0.0107, 3: 0.0121, 2.5: 0.0147, 2.25: 0.0174,
                        2: 0.0221, 1.75: 0.0314, 1.5: 0.0361, 1.25: 0.0524, 0.8: 0.0851, 0.65: 0.1178, 0.2: 0.17,
                        0.19: 0.2}

        min_difference = float("inf")

        for key in credit_bands.keys():
            difference = abs(key - interest_coverage_ratio)
            if difference < min_difference:
                min_difference = difference
                closest_key = key

        credit_spread = credit_bands[closest_key]
        start = (datetime.datetime.today() - datetime.timedelta(days=10))
        end = datetime.datetime.now()
        sofr = web.DataReader("SOFR", "fred", start, end)
        risk_free = sofr.iloc[-1, 0] / 100
        cost_of_debt = risk_free + credit_spread

        beta = company_profile[0]["beta"]
        sp500_return = 0.1190
        cost_of_equity = risk_free + (beta * (sp500_return - risk_free))

        tax_rate = financial_ratios[0]["effectiveTaxRate"]
        debt_to_equity = financial_ratios[0]["debtEquityRatio"]
        debt_ratio = debt_to_equity / (debt_to_equity + 1)
        equity_ratio = max(1 - debt_ratio, 0)
        wacc = (cost_of_debt * (1 - tax_rate) * debt_ratio) + (cost_of_equity * equity_ratio)

        return wacc, risk_free, credit_spread, sp500_return, beta, tax_rate, equity_ratio

    def estimate_beta(self, industry, cap, company_code, session_id):
        if cap == "small":
            low, high = 10000000, 2000000000
        elif cap == "mid":
            low, high = 2000000000, 10000000000
        elif cap == "large":
            low, high = 10000000000, 10000000000000

        total_list = requests.get(f"https://financialmodelingprep.com/api/v3/stock-screener?marketCapMoreThan={low}"
                                  f"&marketCapLowerThan={high}&industry={industry}&limit=100&apikey={self.key}").json()

        company_list = pd.DataFrame(total_list)
        company_list = company_list[["companyName", "symbol", "exchangeShortName", "industry", "marketCap", "beta"]]
        company_list.set_index("companyName", inplace=True)
        company_list.index.name = None
        company_list.columns = ["Ticker", "Exchange", "Industry", "Market Cap", "Beta"]
        company_list.rename_axis("Company Name", axis="columns", inplace=True)
        exchanges = ["NASDAQ", "NYSE", "AMEX"]
        company_list = company_list[company_list["Exchange"].isin(exchanges)]
        company_list["Market Cap"] = company_list["Market Cap"].apply("{:,.0f}".format)
        company_list["Beta"] = company_list["Beta"].apply("{:.2f}".format)
        company_list.to_html("flaskr/templates/dcf/temp/Beta_private_" + company_code + session_id + ".html",
                             float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        return company_list

    def calculate_beta(self, reference_company, tax_rate, equity_ratio):
        beta = requests.get(
            f"https://financialmodelingprep.com/api/v3/profile/{reference_company}?apikey={self.key}").json()
        financial_ratios = requests.get(
            f"https://financialmodelingprep.com/api/v3/ratios/{reference_company}?apikey={self.key}").json()

        if not beta or not financial_ratios:
            return "na"
        else:
            start = (datetime.datetime.today() - datetime.timedelta(days=400)).strftime("%Y-%m-%d")
            end = datetime.datetime.today().strftime("%Y-%m-%d")
            treasury = web.DataReader("TB1YR", "fred", start, end)
            risk_free = treasury.iloc[-1, 0] / 100
            sp500 = web.DataReader(["sp500"], "fred", start, end)
            sp500.dropna(inplace=True)
            sp500_return = (sp500.iloc[-1, 0] / sp500.iloc[-252, 0]) - 1

            reference_levered_beta = beta[0]["beta"]
            reference_tax_rate = financial_ratios[0]["effectiveTaxRate"]
            reference_debt_to_equity = financial_ratios[0]["debtEquityRatio"]
            actual_debt_to_equity = (1 - equity_ratio) / equity_ratio
            unlevered_beta = reference_levered_beta / (1 + (1 - reference_tax_rate) * reference_debt_to_equity)
            actual_levered_beta = unlevered_beta * (1 + (1 - tax_rate) * actual_debt_to_equity)

            if actual_levered_beta > 0:
                return actual_levered_beta, risk_free, sp500_return
            else:
                return "na"


engine = WACC(api_key)