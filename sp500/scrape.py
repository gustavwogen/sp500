import os
from re import sub
from typing import Optional
import requests
from bs4 import BeautifulSoup
import pandas as pd
import boto3
import io
from datetime import datetime, timedelta
import pytz
from sqlalchemy import create_engine, text


SP500_URL = "https://www.slickcharts.com/sp500"
S3_BUCKET = "gurrastav"


def scrape_sp500(url: str) -> Optional[BeautifulSoup]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return BeautifulSoup(res.text, "html.parser")


def create_sp500_df(soup: BeautifulSoup) -> pd.DataFrame:
    table = soup.find("table", class_="table table-hover table-borderless table-sm")
    cols = [col.text.strip() for col in table.thead.tr.find_all("th")]

    rows = []
    for tr in table.tbody.find_all("tr"):
        row = [data.text.strip() for data in tr.find_all("td")]
        rows.append(row)

    df = pd.DataFrame(rows, columns=cols)
    df["Price"] = df["Price"].apply(lambda x: sub(r"[^\d.]", "", x))
    df = df.astype({"Weight": "float", "Price": "float", "Chg": "float"})
    return df[["Company", "Symbol", "Weight", "Price", "Chg", "% Chg"]]


def upload_df_to_s3(df: pd.DataFrame, bucket: str, dest_key: str) -> None:
    client = boto3.client("s3")
    with io.BytesIO() as csv_buffer:
        df.to_csv(csv_buffer)
        csv_buffer.seek(0)
        client.upload_fileobj(csv_buffer, bucket, dest_key)


def upload_df_to_sql(df, user, password, host, database, table):
    conn_string = f"mysql+mysqlconnector://{user}:{password}@{host}/{database}"
    engine = create_engine(conn_string)
    with engine.connect() as connection:
        utc_now = pytz.utc.localize(datetime.utcnow())
        est_yesterday = utc_now.astimezone(
            pytz.timezone("America/New_York")
        ) - timedelta(1)

        with connection.begin():
            query = text(f"select max(Date) from {table}")
            res = connection.execute(query)
            for line in res:
                if line[0] is None:
                    continue
                elif est_yesterday.date() == line[0]:
                    return

        date_col = [est_yesterday.date()] * df.shape[0]
        df["Date"] = date_col
        df = df[["Date", "Company", "Symbol", "Weight", "Price"]].copy()
        df["Date"] = df["Date"].astype("datetime64[ns]")

        df.to_sql(table, con=connection, if_exists="append", index=False)


def main() -> None:
    soup_obj = scrape_sp500(SP500_URL)
    df = create_sp500_df(soup_obj)
    print(df)
    # utc_now = pytz.utc.localize(datetime.utcnow())
    # est_yesterday = utc_now.astimezone(pytz.timezone("America/New_York")) - timedelta(1)
    # upload_df_to_s3(df, S3_BUCKET, f"sp500/{est_yesterday.strftime('%Y_%m_%d')}.csv")
    # upload_df_to_sql(df, "Stocks")


if __name__ == "__main__":
    main()
