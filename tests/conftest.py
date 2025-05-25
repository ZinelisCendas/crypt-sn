import sys
import types

# Stub flipside module
flipside_mod = types.ModuleType("flipside")


class DummyClient:
    def query(self, *a, **k):
        return types.SimpleNamespace(
            records=[], query_id="1", page=types.SimpleNamespace(totalPages=1)
        )

    def get_query_results(self, *a, **k):
        return types.SimpleNamespace(
            records=[], page=types.SimpleNamespace(totalPages=1)
        )


class Dummy:
    def getWalletInfo(self, *a, **k):
        return {"data": {"address": "x", "totalRealizedProfit": 0}}

    def getTrendingWallets(self):
        return {"data": []}


flipside_mod.Flipside = lambda *a, **k: DummyClient()
flipside_mod.flipside = lambda: Dummy()
sys.modules.setdefault("flipside", flipside_mod)

# Stub flipside.errors for QueryRunExecutionError
flipside_err_mod = types.ModuleType("flipside.errors")


class QueryRunExecutionError(Exception):
    pass


flipside_err_mod.QueryRunExecutionError = QueryRunExecutionError
sys.modules.setdefault("flipside.errors", flipside_err_mod)

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

# Stub networkx
nx_mod = types.ModuleType("networkx")


class G:
    def __init__(self):
        self.nodes = set()
        self.edges = []

    def add_nodes_from(self, nodes):
        self.nodes.update(nodes)

    def add_edge(self, a, b):
        self.edges.append((a, b))


def _louvain(g, resolution=1.0):
    visited = set()
    comps = []
    adj = {n: set() for n in g.nodes}
    for a, b in g.edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    for n in g.nodes:
        if n in visited:
            continue
        stack = [n]
        comp = set()
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            comp.add(cur)
            stack.extend(adj.get(cur, []))
        comps.append(comp)
    return comps


nx_mod.Graph = G
nx_mod.algorithms = types.SimpleNamespace(
    community=types.SimpleNamespace(louvain_communities=_louvain)
)
sys.modules.setdefault("networkx", nx_mod)

# Stub solders
solders_mod = types.ModuleType("solders")
sig_mod = types.ModuleType("solders.signature")
sig_mod.Signature = type("Signature", (), {"default": staticmethod(lambda: object())})
keypair_mod = types.ModuleType("solders.keypair")


class Pubkey:
    @staticmethod
    def default():
        return Pubkey()


pubkey_mod = types.ModuleType("solders.pubkey")
pubkey_mod.Pubkey = Pubkey

hash_mod = types.ModuleType("solders.hash")


class Hash:
    @staticmethod
    def new_unique():
        return "hash"


hash_mod.Hash = Hash

keypair_mod.Keypair = type(
    "Keypair",
    (),
    {
        "from_bytes": staticmethod(lambda b: object()),
        "from_secret_key": staticmethod(lambda b: object()),
        "pubkey": lambda self=None: Pubkey(),
    },
)
instr_mod = types.ModuleType("solders.instruction")


class Instruction:
    def __init__(self, program_id, data, accounts):
        self.program_id = program_id
        self.data = data
        self.accounts = accounts


class CompiledInstruction:
    def __init__(self, program_id_index, data, accounts):
        self.program_id_index = program_id_index
        self.data = data
        self.accounts = accounts


instr_mod.Instruction = Instruction
instr_mod.CompiledInstruction = CompiledInstruction
msg_mod = types.ModuleType("solders.message")


class Message:
    def __init__(self, instructions, blockhash):
        self.instructions = instructions
        self.recent_blockhash = blockhash
        self.account_keys = []
        self.header = types.SimpleNamespace(
            num_required_signatures=1,
            num_readonly_signed_accounts=0,
            num_readonly_unsigned_accounts=0,
        )

    @classmethod
    def new_with_blockhash(cls, instructions, payer, blockhash):
        msg = cls(instructions, blockhash)
        msg.account_keys = [payer]
        return msg

    @classmethod
    def new_with_compiled_instructions(
        cls,
        n_req,
        n_readonly_sig,
        n_readonly_unsig,
        keys,
        blockhash,
        instructions,
    ):
        msg = cls(instructions, blockhash)
        msg.account_keys = keys
        msg.header = types.SimpleNamespace(
            num_required_signatures=n_req,
            num_readonly_signed_accounts=n_readonly_sig,
            num_readonly_unsigned_accounts=n_readonly_unsig,
        )
        return msg

    def program_id(self, idx):
        return "ComputeBudget111111111111111111111111111111"


msg_mod.Message = Message
tx_mod = types.ModuleType("solders.transaction")
_tx_store = {}


class VersionedTransaction:
    def __init__(self, message, signers):
        self.message = message
        self.signatures = signers

    def __bytes__(self):
        _tx_store["last"] = self
        return b"tx"

    @classmethod
    def from_bytes(cls, b):
        return _tx_store.get("last", VersionedTransaction(Message([], None), []))

    @staticmethod
    def populate(message, signatures):
        return VersionedTransaction(message, signatures)


tx_mod.VersionedTransaction = VersionedTransaction
cb_mod = types.ModuleType("solders.compute_budget")
cb_mod.ID = "ComputeBudget111111111111111111111111111111"
cb_mod.set_compute_unit_limit = lambda lim: types.SimpleNamespace(
    data=b"\x02" + int(lim).to_bytes(8, "little")
)
cb_mod.set_compute_unit_price = lambda fee: types.SimpleNamespace(
    data=b"\x03" + int(fee).to_bytes(8, "little")
)

sys.modules.setdefault("solders", solders_mod)
sys.modules.setdefault("solders.signature", sig_mod)
sys.modules.setdefault("solders.keypair", keypair_mod)
sys.modules.setdefault("solders.pubkey", pubkey_mod)
sys.modules.setdefault("solders.hash", hash_mod)
sys.modules.setdefault("solders.instruction", instr_mod)
sys.modules.setdefault("solders.message", msg_mod)
sys.modules.setdefault("solders.transaction", tx_mod)
sys.modules.setdefault("solders.compute_budget", cb_mod)

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
