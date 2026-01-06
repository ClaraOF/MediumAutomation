# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "duckdb>=1.4.3",
#     "marimo>=0.17.0",
#     "pandas>=2.3.3",
#     "pyzmq>=27.1.0",
#     "sqlglot>=28.5.0",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import pandas as pd 

    df=pd.DataFrame({
        "A": [1, 2, 3, 4], "B": [5,6,7,8]})

    return (mo,)


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        select * from df
        """
    )
    return


if __name__ == "__main__":
    app.run()
