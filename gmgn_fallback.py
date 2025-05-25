try:
    from gmgn import gmgn as real_gmgn  # type: ignore
except ModuleNotFoundError:

    class Dummy:
        def getWalletInfo(self, *a, **k):
            return {"data": {"address": "", "totalRealizedProfit": 0}}

        def getTrendingWallets(self):
            return {"data": []}

    def real_gmgn():
        return Dummy()


gmgn = real_gmgn
