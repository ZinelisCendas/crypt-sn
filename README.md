# flipside_wallet_bot

Open-source Solana copy trading bot with safety checks and adaptive sizing.

The engine now uses the **Flipside Cooperation‑API** to fetch swap routes and submit transactions via HTTP rather than the WebSocket interface.

## Installation

```bash
pip install -r requirements.txt
```

This project now relies on the official `flipside` SDK.

## Environment Setup

```bash
cp .env.template .env
# edit .env and provide PRIVATE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
# and FLIPSIDE_API_KEY (optionally FLIPSIDE_API_URL)
```

## Quick Start

```bash
python main.py
pytest tests/smoke.py
```

### Running the checks

This project uses `ruff`, `black`, `mypy` and `pytest` for linting and tests. Run them locally before opening a pull request:

```bash
ruff check .
black --check .
mypy .
pytest -q
```



### Flipside **Python SDK** (“`flipside`” package) – *one-page cheat-sheet*

---

#### 1  Install & import

```bash
pip install flipside        # Python ≥3.7
```

```python
from flipside import Flipside
```

#### 2  Create a client

```python
flipside = Flipside("<API_KEY>", "https://api-v2.flipsidecrypto.xyz")
```

---

### 3  Run a query (all optional kwargs shown)

```python
sql = "SELECT …"
result = flipside.query(
    sql,                      # required

    # execution / cache control
    max_age_minutes=30,       # 0-1440 min cache allowance (0 ⇒ always rerun)
    cached=True,              # False overrides max_age_minutes

    timeout_minutes=15,       # cancel if runtime >x min

    # paging for the *first* fetch
    page_number=1,
    page_size=100000,         # default 100 k rows; ≤30 MB payload

    # snowflake options (seldom needed)
    data_provider="flipside",
    data_source="snowflake-default",
)
```

---

### 4  `QueryResultSet` object (returned by **`query()`** & **`get_query_results()`**)

| attr                      | type / meaning                       |
| ------------------------- | ------------------------------------ |
| `query_id`                | str                                  |
| `status`                  | `'PENDING' \| 'FINISHED' \| 'ERROR'` |
| `columns`, `column_types` | list\[str]                           |
| `rows`                    | list\[list\[Any]]                    |
| `records`                 | list\[dict] (1 row = dict)           |
| `run_stats`               | `QueryRunStats` (☑ billing)          |
| `page`                    | `PageStats` (☑ pagination)           |
| `error`                   | one of the Error classes             |

##### `run_stats` keys

`started_at, ended_at, elapsed_seconds, query_exec_seconds (billable), queued_seconds, streaming_seconds, record_count, bytes`

##### `page` keys

`currentPageNumber, currentPageSize, totalRows, totalPages`

---

### 5  Paginate, sort, filter (no re-execution)

```python
all_rows = []
page_num = 1
while True:
    r = flipside.get_query_results(
            result.query_id,
            page_number=page_num,
            page_size=10000,
            sort_by=[{'column':'price_usd','direction':'desc'}],
            filters=[
                {'eq':'moonbirds','column':'project_name'},
                {'gte':5000,'column':'price_usd'},
                {'in':['opensea','blur'],'column':'platform_name'}
            ])
    all_rows += r.records or []
    if page_num >= r.page.totalPages:
        break
    page_num += 1
```

*`sort_by` accepts `{column:str, direction:'asc'|'desc'}`*
*`filters` operators: `eq, neq, gt, gte, lt, lte, like, in, notIn`*

---

### 6  Caching with `max_age_minutes`

* If a *byte-for-byte identical* query last succeeded ≤ `max_age_minutes` ago, cached results are returned instantly & **not billed**.
* Set `max_age_minutes=0` **or** `cached=False` to force re-execution.

---

### 7  Billing – Query Seconds

You are charged only for `run_stats.query_exec_seconds` (compute on the warehouse). Queued, streaming or cached queries cost **0**.

---

### 8  Limits

| limit                | value           |
| -------------------- | --------------- |
| Concurrent QueryRuns | **15**          |
| Result-set size      | **1 GB** total  |
| Single page payload  | **30 MB**       |
| `max_age_minutes`    | 0 – 1440 (24 h) |

---

### 9  Error classes you can `except`

```python
from flipside.errors import (
    QueryRunRateLimitError,   # >15 concurrent or burst
    QueryRunTimeoutError,     # runtime exceeded timeout_minutes
    QueryRunExecutionError,   # bad SQL
    ServerError,              # Flipside server issue
    ApiError,                 # bad request / invalid API key
    SDKError                  # generic client-side
)
```

---

### 10  Minimal snippets

*Quick run & loop every row*

```python
rs = flipside.query("SELECT * FROM ... LIMIT 1000")
for r in rs.records or []:
    print(r['col1'], r['col2'])
```

*Only download fresh data*

```python
rs = flipside.query(sql, max_age_minutes=0)   # always rerun
```

*Lightweight head request*

```python
head = flipside.query(sql, page_size=1)       # preview columns
```

---

