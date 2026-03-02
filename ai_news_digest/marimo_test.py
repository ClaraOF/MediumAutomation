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

    return mo, pd


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        select * from df
        """
    )
    return


@app.cell
def _(mo):
    name = mo.ui.text(placeholder="Your name here")
    mo.md(
      f"""
      Hi! What's your name?

      {name}
      """
    )
    return (name,)


@app.cell
def _(mo, name):
    mo.md(
      f"""
      Hello, {name.value}!
      """
    )
    return


@app.cell
def _(mo):
    # mo.status.progress_bar is similar to TQDM
    for i in mo.status.progress_bar(range(10)):
      print(i)
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd 

    df2 = pd.read_json(
        "https://raw.githubusercontent.com/vega/vega-datasets/master/data/cars.json"
    )
    mo.plain(df2)
    return mo, pd


@app.cell
def _(mo, pd):
    df3 = pd.DataFrame({"person": ["Alice", "Bob", "Charlie"], "age": [20, 30, 40]})
    transformed_df = mo.ui.dataframe(df3)
    transformed_df
    return (df3,)


@app.cell
def _(mo):
    # Cell 2 - create a filter
    age_filter = mo.ui.slider(start=0, stop=100, value=50, label="Max age")
    age_filter
    return (age_filter,)


@app.cell
def _(age_filter, df3, mo):
    # Cell 3 - display the transformed dataframe
    filtered_df = df3[df3["age"] < age_filter.value]
    mo.ui.table(filtered_df)
    return


if __name__ == "__main__":
    app.run()
