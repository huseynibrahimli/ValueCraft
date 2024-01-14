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
        df_is = df_is.iloc[:, 0:6].applymap("{:,.0f}".format)
        df_is.to_html("flaskr/templates/dcf/temp/IS_private_" + company_code + session_id + ".html",
                      float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        df_cf.index.name = None
        df_cf = df_cf.rename_axis("Cash Flow Statement", axis="columns")
        df_cf = df_cf.astype(float)
        df_cf = df_cf.iloc[:, 0:6].applymap("{:,.0f}".format)
        df_cf.to_html("flaskr/templates/dcf/temp/CF_private_" + company_code + session_id + ".html",
                      float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        return df_is, df_cf

    def project_revenue(self, company_statement):
        statements = pd.ExcelFile(company_statement)
        df_is = pd.read_excel(statements, "income_statement", index_col="Income Statement")
        df_is = df_is.to_dict()
        revenue_now = df_is["T"]["revenue"]
        revenue_past = df_is["T-4"]["revenue"]
        revenue_g = (revenue_now / revenue_past) ** 0.25 - 1

        return revenue_g

    def project_fcf(self, company_statement, revenue_g, company_code, session_id):
        statements = pd.ExcelFile(company_statement)
        df_is = pd.read_excel(statements, "income_statement", index_col="Income Statement")
        df_cf = pd.read_excel(statements, "cashflow_statement", index_col="Cash Flow Statement")

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

        tax_rate = df_is["T-Average"]["incomeTaxExpense"] / df_is["T-Average"]["incomeBeforeTax"]
        if tax_rate < 0:
            tax_rate = 0

        df_cf = df_cf.astype(float)
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
            t = "T+%d" % i
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
        cf_forecast.to_html("flaskr/templates/dcf/temp/FCF_private_" + company_code + session_id + ".html",
                            float_format=lambda x: "{:,.0f}".format(x), classes="dataframe_statement")

        return cf_forecast

    def calc_tv(self, g, wacc, fcf):
        fcf = pd.read_json(fcf)
        if fcf["T+5"]["FCF"] > 0:
            terminal_value = (fcf["T+5"]["FCF"] * (1 + g)) / (wacc - g)
            terminal_value_discounted = max(round(terminal_value / (1 + wacc) ** 5), 0)
        else:
            terminal_value_discounted = 0

        return terminal_value_discounted

    def calc_dcf(self, wacc, fcf, tv, debt):
        fcf = pd.read_json(fcf)
        fcf_list = fcf.iloc[-1].tolist()
        fcf_list.insert(0, 0)
        npv = npf.npv(wacc, fcf_list)
        firm_value = tv + npv

        if firm_value > 0:
            equity_value = max(firm_value - debt, 0)
        else:
            equity_value = 0

        firm_value = equity_value + debt

        return firm_value, debt, equity_value


engine = Private()
