CREATE TABLE IF NOT EXISTS sector_etfs (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL REFERENCES sector_etfs(symbol) ON DELETE CASCADE,
    date DATE NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT,
    PRIMARY KEY (ticker, date)
);

CREATE INDEX IF NOT EXISTS prices_date_idx ON prices(date);

CREATE TABLE IF NOT EXISTS technical_indicators (
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    sma50 DOUBLE PRECISION,
    sma200 DOUBLE PRECISION,
    ema21 DOUBLE PRECISION,
    boll_up DOUBLE PRECISION,
    boll_dn DOUBLE PRECISION,
    PRIMARY KEY (ticker, date),
    FOREIGN KEY (ticker, date)
        REFERENCES prices(ticker, date)
        ON DELETE CASCADE
);
