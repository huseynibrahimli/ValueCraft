import datetime
import pandas as pd
import pandas_datareader.data as web
import requests


pd.options.display.float_format = "{:,.4f}".format
pd.set_option("mode.chained_assignment", None)
pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 999)

api_key = "24cb7ed8e2f85f03a04132535646cc5f"

# https://pages.stern.nyu.edu/~adamodar/
equity_risk_premium = 0.0457


class WACC:

    def __init__(self, key, risk_premium):
        self.key = key
        self.risk_premium = risk_premium

    def calculate_wacc(self, company):
        company_profile = requests.get(
            f"https://financialmodelingprep.com/api/v3/profile/{company}?apikey={self.key}").json()
        financial_ratios = requests.get(
            f"https://financialmodelingprep.com/api/v3/ratios/{company}?apikey={self.key}").json()
        market_cap = requests.get(
            f"https://financialmodelingprep.com/api/v3/market-capitalization/{company}?apikey={self.key}").json()
        balance_sheet = requests.get(
            f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{company}?apikey={self.key}").json()

        beta = company_profile[0]["beta"]

        financial_ratios = pd.DataFrame(financial_ratios[0:5])
        interest_coverage_ratio = financial_ratios["interestCoverage"].mean()
        tax_rate = financial_ratios["effectiveTaxRate"].mean()
        if tax_rate < 0:
            tax_rate = 0

        equity_value = market_cap[0]["marketCap"]
        debt_value = balance_sheet[0]["totalDebt"]
        equity_weight = equity_value / (equity_value + debt_value)
        debt_weight = 1 - equity_weight

        start = (datetime.datetime.today() - datetime.timedelta(days=10))
        end = datetime.datetime.now()
        treasury_10Y = web.DataReader("DGS10", "fred", start, end)
        risk_free = treasury_10Y.iloc[-1, 0] / 100

        credit_ratings = pd.read_json("flaskr/data/dcf/credit_ratings.json")
        credit_ratings.set_index("Symbol", inplace=True)
        credit_ratings.index.name = None
        credit_ratings.rename_axis("Ticker", axis="columns", inplace=True)
        credit_spread = credit_ratings.loc[company, "Spread"]

        if credit_spread is None:
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

        cost_debt = risk_free + credit_spread
        cost_equity = risk_free + (beta * self.risk_premium)
        wacc = (cost_debt * (1 - tax_rate) * debt_weight) + (cost_equity * equity_weight)

        return wacc, cost_debt, risk_free, credit_spread, cost_equity, self.risk_premium, beta, tax_rate, equity_weight

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

    def calculate_beta(self, reference_company, tax_rate, equity_weight):
        try:
            beta = requests.get(
                f"https://financialmodelingprep.com/api/v3/profile/{reference_company}?apikey={self.key}").json()
            financial_ratios = requests.get(
                f"https://financialmodelingprep.com/api/v3/ratios/{reference_company}?apikey={self.key}").json()

            start = (datetime.datetime.today() - datetime.timedelta(days=10))
            end = datetime.datetime.now()
            treasury_10Y = web.DataReader("DGS10", "fred", start, end)
            risk_free = treasury_10Y.iloc[-1, 0] / 100

            reference_levered_beta = beta[0]["beta"]

            reference_tax_rate = financial_ratios[0]["effectiveTaxRate"]
            if reference_tax_rate < 0:
                reference_tax_rate = 0

            reference_debt_to_equity = financial_ratios[0]["debtEquityRatio"]
            actual_debt_to_equity = (1 - equity_weight) / equity_weight

            unlevered_beta = reference_levered_beta / (1 + (1 - reference_tax_rate) * reference_debt_to_equity)
            actual_levered_beta = unlevered_beta * (1 + (1 - tax_rate) * actual_debt_to_equity)

            if actual_levered_beta > 0:
                return actual_levered_beta, risk_free, self.risk_premium
            else:
                return "na"
        except Exception as e:
            print(f"Sufficient information doesn't exist: {e}")
            return "na"


engine = WACC(api_key, equity_risk_premium)