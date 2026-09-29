import time
import bs4
from curl_cffi import requests as curl_requests
from threading import Event
from .. import settings
from x_client_transaction.utils import get_ondemand_file_url
from x_client_transaction import ClientTransaction
from .xpff import XPFFHeaderGenerator
from .constants import BEARER_TOKEN, XPFF_BASE_KEY, USER_AGENT, BASE_UA_HEADERS


class XSession:
    def __init__(self, auth_token: str, proxy: str = "", stop_event=None):
        self.auth_token = auth_token
        self.stop_event = stop_event if stop_event is not None else Event()
        self._s = curl_requests.Session(
            impersonate="chrome124",  # supported by the pinned curl_cffi 0.7.4
            proxies={"http": proxy, "https": proxy} if proxy else {},
            timeout=settings.X_REQUEST_TIMEOUT,
        )
        self._ct0 = ""
        self._gt = ""
        self._xpff = ""
        self._ct = None
        self._cookie_base: dict = {}
        # True quand la dernière erreur vient du transport (proxy injoignable,
        # timeout, DNS) plutôt que d'un refus de X — les callers ne doivent
        # pas le compter comme un échec d'auth du compte.
        self.last_net_error = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._s.close()

    def _request(self, method, url, **kwargs):
        if self.stop_event.is_set():
            raise RuntimeError("Job stopped")
        try:
            return self._s.request(method, url, **kwargs)
        except RuntimeError:
            raise
        except Exception:
            # curl_cffi transport failures: proxy down, connexion refusée,
            # timeout, DNS… — pas un signal sur la validité du compte.
            self.last_net_error = True
            raise

    def authenticate(self) -> bool:
        self.last_net_error = False
        if not self._load_home():
            return False
        if not self._fetch_ct0():
            return False
        if not self._fetch_guest_token():
            return False
        if not self._generate_xpff():
            return False
        return True

    # ── Auth steps ────────────────────────────────────────────────────────────

    def _load_home(self) -> bool:
        try:
            home = self._request("GET", "https://x.com/home", headers={
                **BASE_UA_HEADERS,
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-encoding": "gzip, deflate, br, zstd",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
                "cookie": f"auth_token={self.auth_token}",
            })
        except Exception:
            return False

        sc = dict(self._s.cookies)
        self._cookie_base = {
            "auth_token": self.auth_token,
            "personalization_id": sc.get("personalization_id", ""),
            "guest_id": sc.get("guest_id", ""),
        }

        try:
            soup = bs4.BeautifulSoup(home.content, "html.parser")
            od_url = get_ondemand_file_url(response=soup)
            od_text = self._request("GET", url=od_url).text
            self._ct = ClientTransaction(home_page_response=soup, ondemand_file_response=od_text)
        except Exception:
            return False

        return True

    def _fetch_ct0(self) -> bool:
        for attempt in range(3):
            try:
                r = self._request("POST", 
                    "https://x.com/i/api/1.1/account/update_profile.json",
                    headers={
                        **BASE_UA_HEADERS,
                        "accept": "*/*",
                        "accept-encoding": "gzip, deflate, br, zstd",
                        "content-type": "application/x-www-form-urlencoded",
                        "origin": "https://x.com",
                        "priority": "u=1, i",
                        "referer": "https://x.com/settings/profile",
                        "sec-fetch-dest": "empty",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-site": "same-origin",
                        "x-twitter-active-user": "yes",
                        "x-twitter-auth-type": "OAuth2Session",
                        "x-twitter-client-language": "en",
                        "cookie": self._build_cookie(),
                    },
                )
                self._ct0 = r.cookies["ct0"]
                return True
            except Exception:
                if attempt == 2:
                    return False
                self.stop_event.wait(1)
        return False

    def _fetch_guest_token(self) -> bool:
        for attempt in range(3):
            try:
                r = self._request("POST", 
                    "https://api.x.com/1.1/guest/activate.json",
                    headers={
                        **BASE_UA_HEADERS,
                        "accept": "*/*",
                        "accept-encoding": "gzip, deflate, br, zstd",
                        "authorization": f"Bearer {BEARER_TOKEN}",
                        "content-type": "application/json",
                        "cookie": self._build_cookie(),
                        "origin": "https://x.com",
                        "referer": "https://x.com/",
                        "sec-fetch-dest": "empty",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-site": "same-site",
                        "x-csrf-token": self._ct0,
                        "x-twitter-active-user": "yes",
                        "x-twitter-client-language": "en",
                        "x-client-transaction-id": self._ct.generate_transaction_id(
                            method="POST", path="/1.1/guest/activate.json"
                        ),
                    },
                )
                self._gt = r.json().get("guest_token", "")
                return bool(self._gt)
            except Exception:
                if attempt == 2:
                    return False
                self.stop_event.wait(1)
        return False

    def _generate_xpff(self) -> bool:
        try:
            gen = XPFFHeaderGenerator(XPFF_BASE_KEY)
            self._xpff, _ = gen.generate(USER_AGENT, self._gt, True)
            return True
        except Exception:
            return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_cookie(self) -> str:
        parts = dict(self._cookie_base)
        if self._ct0:
            parts["ct0"] = self._ct0
        if self._gt:
            parts["gt"] = self._gt
        return "; ".join(f"{k}={v}" for k, v in parts.items() if v)

    def graphql_headers(self, method: str, path: str, referer: str) -> dict:
        return {
            **BASE_UA_HEADERS,
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "authorization": f"Bearer {BEARER_TOKEN}",
            "content-type": "application/json",
            "cookie": self._build_cookie(),
            "origin": "https://x.com",
            "priority": "u=1, i",
            "referer": referer,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-client-transaction-id": self._ct.generate_transaction_id(method=method, path=path),
            "x-csrf-token": self._ct0,
            "x-guest-token": self._gt,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
            "x-xp-forwarded-for": self._xpff,
        }

    def post(self, url: str, payload: dict, referer: str):
        path = url.split("x.com", 1)[-1]
        return self._request("POST", url, headers=self.graphql_headers("POST", path, referer), json=payload)

    def post_form(self, url: str, data: dict, referer: str):
        path = url.split("x.com", 1)[-1]
        headers = self.graphql_headers("POST", path, referer)
        headers["content-type"] = "application/x-www-form-urlencoded"
        return self._request("POST", url, headers=headers, data=data)

    def get(self, url: str, params: dict, referer: str):
        path = url.split("x.com", 1)[-1]
        return self._request("GET", url, headers=self.graphql_headers("GET", path, referer), params=params)
