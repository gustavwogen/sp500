import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import pytz

SP500_URL = "https://www.slickcharts.com/sp500"


def upload_df_to_sql(df, table):
    conn_string = f"mysql+mysqldb://{os.getenv('USERNAME')}:{os.getenv('PASSWORD')}@{os.getenv('HOST')}/{os.getenv('DATABASE')}"
    engine = create_engine(conn_string)
    with engine.connect() as connection:
        utc_now = pytz.utc.localize(datetime.utcnow())
        est_yesterday = utc_now.astimezone(
            pytz.timezone("America/New_York")
        ) - timedelta(1)

        with connection.begin():
            query = text("select max(Date) from Stocks")
            res = connection.execute(query)
            for line in res:
                if line[0] is None:
                    continue
                elif est_yesterday.date() == line[0]:
                    return

        date_col = [est_yesterday.date()] * df.shape[0]
        df["Date"] = date_col
        df = df[["Date", "Company", "Symbol", "Weight", "Price"]]
        df["Date"] = df["Date"].astype("datetime64[ns]")

        df.to_sql(table, con=connection, if_exists="append", index=False)
