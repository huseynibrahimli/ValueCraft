import numpy_financial as npf
import pandas as pd

pd.options.display.float_format = "{:,.0f}".format
pd.set_option("mode.chained_assignment", None)
pd.set_option("display.width", 320)
pd.set_option("display.max_columns", 999)


class Private:

    def import_data(self, company_statement, company_code, session_id):

        statements = pd.ExcelFile(company_statement)
        df_is = pd.read_excel(statements, "income_statement", index_col="Income Statement")
        df_cf = pd.read_excel(statements, "cashflow_statement", index_col="Cash Flow Statement")

        df_is.index.name = None
        df_is = df_is.rename_axis("Income Statement", axis="columns")
        df_is = df_is.astype(float)
        num_columns = len(df_is.columns) + 1
        df_is = df_is.iloc[:, 0:num_columns].applymap("{:,.0f}".format)
        df_is.to_html("flaskr/templates/dcf/temp/IS_private_" + company_code + session_id + ".html",
                      float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        df_cf.index.name = None
        df_cf = df_cf.rename_axis("Cash Flow Statement", axis="columns")
        df_cf = df_cf.astype(float)
        num_columns = len(df_cf.columns) + 1
        df_cf = df_cf.iloc[:, 0:num_columns].applymap("{:,.0f}".format)
        df_cf.to_html("flaskr/templates/dcf/temp/CF_private_" + company_code + session_id + ".html",
                      float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        return df_is, df_cf

    def project_revenue(self, company_statement):
        statements = pd.ExcelFile(company_statement)
        df_is = pd.read_excel(statements, "income_statement", index_col="Income Statement")
        df_is.index.name = None
        df_is = df_is.rename_axis("Income Statement", axis="columns")
        df_is = df_is.astype(float)
        num_columns = len(df_is.columns) - 1

        revenue_g = (df_is.loc["revenue", df_is.columns[0]] / df_is.loc["revenue", df_is.columns[-1]]) ** (1 / num_columns) - 1

        return revenue_g

    def project_fcf(self, company_statement, company_code, session_id, revenue_g, tax_rate, wacc, projection_period, convergence_year, perpetuity_growth, perpetuity_wacc):
        statements = pd.ExcelFile(company_statement)
        df_is = pd.read_excel(statements, "income_statement", index_col="Income Statement")
        df_cf = pd.read_excel(statements, "cashflow_statement", index_col="Cash Flow Statement")

        revenue_g_delta = (revenue_g - perpetuity_growth) / (projection_period - convergence_year + 1)
        wacc_delta = (wacc - perpetuity_wacc) / (projection_period - convergence_year + 1)

        df_is["T-Average"] = df_is.mean(axis=1)
        df_is["%_revenue"] = df_is["T-Average"] / df_is["T-Average"].iloc[0]
        df_is = df_is.astype(float)

        df_cf = df_cf.astype(float)
        df_cf["T-Average"] = df_cf.mean(axis=1)
        df_cf["%_revenue"] = df_cf["T-Average"] / df_is["T-Average"].iloc[0]
        df_cf = df_cf.astype(float)

        i = 1
        while i <= projection_period:
            if i == 1:
                df_is[f"T+{i}"] = (df_is["T"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
                df_is.loc["revenue_g", f"T+{i}"] = revenue_g
                df_is.loc["wacc", f"T+{i}"] = wacc
                df_is.loc["discount_factor", f"T+{i}"] = (1 / (1 + wacc))
            elif 1 < i < convergence_year:
                df_is[f"T+{i}"] = (df_is[f"T+{i - 1}"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
                df_is.loc["revenue_g", f"T+{i}"] = revenue_g
                df_is.loc["wacc", f"T+{i}"] = wacc
                df_is.loc["discount_factor", f"T+{i}"] = (1 / (1 + wacc)) * df_is.loc["discount_factor", f"T+{i-1}"]
            else:
                revenue_g = revenue_g - revenue_g_delta
                wacc = wacc - wacc_delta
                df_is[f"T+{i}"] = (df_is[f"T+{i - 1}"]["revenue"] * (1 + revenue_g)) * df_is["%_revenue"]
                df_is.loc["revenue_g", f"T+{i}"] = revenue_g
                df_is.loc["wacc", f"T+{i}"] = wacc
                df_is.loc["discount_factor", f"T+{i}"] = (1 / (1 + wacc)) * df_is.loc["discount_factor", f"T+{i - 1}"]
            i += 1

        i = 1
        while i <= projection_period:
            df_cf[f"T+{i}"] = df_is[f"T+{i}"]["revenue"] * df_cf["%_revenue"]
            i += 1

        cf_forecast = {}
        i = 1
        while i <= projection_period:
            t = f"T+{i}"
            cf_forecast[t] = {}
            cf_forecast[t]["Revenue growth rate"] = df_is[t]["revenue_g"]
            cf_forecast[t]["Cost of capital"] = df_is[t]["wacc"]
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
        cf_forecast.to_html("flaskr/templates/dcf/temp/FCF_private_" + company_code + session_id + ".html",
                            float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        return cf_forecast

    def calc_tv(self, perpetuity_growth, perpetuity_wacc, fcf, projection_period):
        fcf = pd.read_json(fcf)
        projection_period = int(projection_period)
        discount_factor = float(fcf[f"T+{projection_period}"]["Discount factor"])
        fcf_terminal = float(fcf[f"T+{projection_period}"]["FCFF"])
        if fcf_terminal > 0:
            terminal_value = (fcf_terminal * (1 + perpetuity_growth)) / (perpetuity_wacc - perpetuity_growth)
            terminal_value_pv = max(round(terminal_value * discount_factor), 0)
        else:
            terminal_value = 0
            terminal_value_pv = 0

        return fcf_terminal, terminal_value, terminal_value_pv

    def calc_dcf(self, fcf, terminal_value_pv, net_debt):
        fcf = pd.read_json(fcf)
        pv_fcff = fcf.iloc[-1].sum()
        firm_value = pv_fcff + terminal_value_pv

        if firm_value > 0:
            equity_value = max(firm_value - net_debt, 0)
        else:
            equity_value = 0

        firm_value = equity_value + net_debt

        return firm_value, equity_value


engine = Private()