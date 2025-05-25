try:
    from flipside import flipside as real_flipside  # type: ignore
except ModuleNotFoundError:

    class Dummy:
        def getWalletInfo(self, *a, **k):
            return {"data": {"address": "", "totalRealizedProfit": 0}}

        def getTrendingWallets(self):
            return {"data": []}

    def real_flipside():
        return Dummy()


flipside = real_flipside
