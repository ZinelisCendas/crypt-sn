import sys
import types

# Stub flipside module
flipside_mod = types.ModuleType("flipside")


class Dummy:
    def getWalletInfo(self, *a, **k):
        return {"data": {"address": "x", "totalRealizedProfit": 0}}

    def getTrendingWallets(self):
        return {"data": []}


flipside_mod.flipside = lambda: Dummy()
sys.modules.setdefault("flipside", flipside_mod)

# Stub aiohttp
aiohttp_mod = types.ModuleType("aiohttp")


class Resp:
    status = 200

    async def json(self):
        return {}

    def raise_for_status(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class Session:
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get(self, *a, **k):
        return Resp()

    async def post(self, *a, **k):
        return Resp()


aiohttp_mod.ClientSession = Session
aiohttp_mod.ClientTimeout = lambda *a, **k: None
sys.modules.setdefault("aiohttp", aiohttp_mod)

# Stub websockets
websockets_mod = types.ModuleType("websockets")


class WS:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def __aiter__(self):
        async def gen():
            if False:
                yield None

        return gen()


websockets_mod.connect = lambda *a, **k: WS()
sys.modules.setdefault("websockets", websockets_mod)

# Stub pandas
pd_mod = types.ModuleType("pandas")


class Series(list):
    def mean(self):
        return sum(self) / len(self) if self else 0.0

    def std(self):
        return 1.0

    def astype(self, t):
        return Series([t(x) for x in self])

    def to_numpy(self):
        return self


pd_mod.Series = Series


class DataFrame(dict):
    def __init__(self, data):
        super().__init__(data)

    def __getitem__(self, k):
        return Series(self.get(k, []))

    def to_numpy(self):
        return list(self.values())


pd_mod.DataFrame = DataFrame
sys.modules.setdefault("pandas", pd_mod)

# Stub dotenv
dotenv_mod = types.ModuleType("dotenv")
dotenv_mod.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", dotenv_mod)

# Stub prometheus_client
prom_mod = types.ModuleType("prometheus_client")


class Gauge:
    def __init__(self, *a, **k):
        pass

    def set(self, *a, **k):
        pass


prom_mod.Gauge = Gauge
prom_mod.Histogram = Gauge
prom_mod.start_http_server = lambda *a, **k: None
sys.modules.setdefault("prometheus_client", prom_mod)

# Stub base58
base58_mod = types.ModuleType("base58")
base58_mod.b58decode = lambda b: b""
sys.modules.setdefault("base58", base58_mod)

# Stub solana modules
sol_rpc_api = types.ModuleType("solana.rpc.api")


class Client:
    def __init__(self, *a, **k):
        pass

    def send_raw_transaction(self, *a, **k):
        return {}


sol_rpc_api.Client = Client
sys.modules.setdefault("solana.rpc.api", sol_rpc_api)

sol_tx = types.ModuleType("solana.transaction")


class Transaction:
    @classmethod
    def deserialize(cls, *a, **k):
        return cls()

    def sign(self, *a, **k):
        pass

    def serialize(self):
        return b""


sol_tx.Transaction = Transaction
sys.modules.setdefault("solana.transaction", sol_tx)

sol_kp = types.ModuleType("solana.keypair")
sol_kp.Keypair = type(
    "Keypair", (), {"from_secret_key": staticmethod(lambda b: object())}
)
sys.modules.setdefault("solana.keypair", sol_kp)

sys.modules.setdefault("solana", types.ModuleType("solana"))
sys.modules.setdefault("solana.rpc", types.ModuleType("solana.rpc"))

# Stub numpy
np_mod = types.ModuleType("numpy")
np_mod.arange = lambda n: list(range(n))
np_mod.array = lambda x: x
np_mod.reshape = lambda arr, shape: [[i] for i in arr]
np_mod.isscalar = lambda x: isinstance(x, (int, float))
sys.modules.setdefault("numpy", np_mod)

# Stub sklearn
sk_mod = types.ModuleType("sklearn")
lin_mod = types.ModuleType("linear_model")


class LR:
    def fit(self, X, y):
        return self

    @property
    def coef_(self):
        return [1.0]

    def score(self, X, y):
        return 1.0


LinearRegression = LR
lin_mod.LinearRegression = LinearRegression
sk_mod.linear_model = lin_mod
sys.modules.setdefault("sklearn", sk_mod)
sys.modules.setdefault("sklearn.linear_model", lin_mod)

# Stub pythonjsonlogger
pj_mod = types.ModuleType("pythonjsonlogger")


class JF:
    def __init__(self, *a, **k):
        pass


pj_mod.jsonlogger = types.SimpleNamespace(JsonFormatter=JF)
sys.modules.setdefault("pythonjsonlogger", pj_mod)
