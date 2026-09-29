import asyncio
import aiohttp
import json
import time
import os
from typing import List, Dict, Optional

# count=200 = tarif optimal : 1 crédit/follower (vs 3 crédits à count<100)
PAGE_SIZE = 200


class TokenBucketRateLimiter:
    def __init__(self, rate: float):
        self.rate = rate
        self.tokens = rate
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            self.tokens = min(self.rate, self.tokens + (now - self.last_refill) * self.rate)
            self.last_refill = now
            if self.tokens < 1:
                await asyncio.sleep((1 - self.tokens) / self.rate)
                self.tokens = 0
            else:
                self.tokens -= 1


class TwitterFollowerScraper:
    def __init__(self, api_key: str, qps: int = 20):
        self.api_key = api_key
        self.base_url = "https://api.twitterapi.io"
        self.headers = {"X-API-Key": api_key}
        self.rate_limiter = TokenBucketRateLimiter(qps)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers=self.headers,
            connector=aiohttp.TCPConnector(limit=100, ttl_dns_cache=300, keepalive_timeout=30),
            timeout=aiohttp.ClientTimeout(total=30, connect=5),
        )
        return self

    async def __aexit__(self, *_):
        if self._session:
            await self._session.close()

    async def _get(self, path: str, params: Dict, retries: int = 4) -> Optional[Dict]:
        url = f"{self.base_url}{path}"
        for attempt in range(retries):
            await self.rate_limiter.acquire()
            try:
                async with self._session.get(url, params=params) as resp:
                    if resp.status == 429:
                        wait = 5 * 2 ** attempt
                        print(f"⚠️  Rate limit — attente {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                    if resp.status in (401, 403, 404):
                        return {"_http": resp.status}
                    if resp.status != 200:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return await resp.json()
            except asyncio.TimeoutError:
                await asyncio.sleep(2 ** attempt)
            except aiohttp.ClientError:
                await asyncio.sleep(2 ** attempt)
        return None

    async def get_follower_usernames(self, username: str, max_followers: int) -> List[str]:
        username = username.lstrip("@")
        pages_needed = -(-max_followers // PAGE_SIZE)
        print(f"\n🔍 @{username} — {max_followers} followers (~{pages_needed} pages)")

        usernames: List[str] = []
        cursor: Optional[str] = None
        page = 0

        while len(usernames) < max_followers:
            page += 1
            params: Dict = {
                "userName": username,
                "count": min(PAGE_SIZE, max_followers - len(usernames)),
            }
            if cursor:
                params["cursor"] = cursor

            print(f"   📡 page {page}/{pages_needed} | {len(usernames)}/{max_followers}")
            data = await self._get("/twitter/user/followers", params)

            if data is None:
                print("   ⚠️  Abandon après échecs répétés")
                break

            code = data.get("_http")
            if code == 401:
                print("   ❌ Clé API invalide")
                break
            elif code == 403:
                print("   ❌ Accès refusé ou compte privé")
                break
            elif code == 404:
                print(f"   ❌ @{username} introuvable")
                break

            if data.get("status") != "success":
                print(f"   ❌ API: {data.get('msg', 'erreur inconnue')}")
                break

            batch = data.get("followers", [])
            if not batch:
                print("   ℹ️  Plus de followers")
                break

            for f in batch:
                uname = f.get("userName") or f.get("screen_name")
                if uname:
                    usernames.append(uname)

            if not data.get("has_next_page") or not data.get("next_cursor"):
                break
            cursor = data["next_cursor"]

        print(f"   ✅ {len(usernames[:max_followers])} usernames récupérés")
        return usernames[:max_followers]

    async def check_credits(self) -> Optional[Dict]:
        data = await self._get("/credits", {})
        return data if data and "_http" not in data else None


async def async_main():
    print("=" * 60)
    print("🐦  TWITTER FOLLOWER SCRAPER — twitterapi.io")
    print("=" * 60)

    api_key = input("\n🔑 Clé API: ").strip()
    if not api_key:
        print("❌ Clé API requise!")
        return

    raw = input("👤 Compte(s) Twitter (séparés par virgule): ").strip()
    if not raw:
        print("❌ Nom d'utilisateur requis!")
        return
    usernames = [u.strip() for u in raw.split(",") if u.strip()]

    try:
        n = input("📊 Nombre de followers (défaut 1000): ").strip()
        max_followers = int(n) if n else 1000
        if max_followers <= 0:
            raise ValueError
    except ValueError:
        print("❌ Nombre invalide!")
        return

    pages = -(-max_followers // PAGE_SIZE) * len(usernames)
    cost = max_followers * len(usernames)
    print(f"\n📋 ~{pages} requêtes | ~{cost:,} crédits | ~${cost/100000:.4f}")

    start = time.perf_counter()

    async with TwitterFollowerScraper(api_key) as scraper:
        credits_info = await scraper.check_credits()
        if credits_info:
            bal = credits_info.get("balance", credits_info.get("credits", "?"))
            print(f"💳 Crédits disponibles: {bal}")

        tasks = [scraper.get_follower_usernames(u, max_followers) for u in usernames]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        os.makedirs("outputs", exist_ok=True)
        for u, result in zip(usernames, results):
            uname = u.lstrip("@")
            if not isinstance(result, list) or not result:
                print(f"❌ Aucun résultat pour @{uname}")
                continue
            filepath = os.path.join("outputs", f"{uname}.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(result) + "\n")
            print(f"✅ {len(result)} usernames → {filepath}")

    elapsed = time.perf_counter() - start
    print(f"\n🎉 Terminé en {elapsed:.1f}s")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
