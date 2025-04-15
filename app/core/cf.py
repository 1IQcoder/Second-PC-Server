import json, os, requests
from .utils import JsonEditor, DB_DIR, BaseJsonFile
from typing import TypedDict

class CloudflareAPIException(Exception):
    def __init__(self, errors: list):
        self.errors = errors
        self.message = self.format_errors(errors)
        super().__init__(self.message)

    def format_errors(self, errors: list) -> str:
        error_messages = []
        for error in errors:
            error_message = f"Code: {error['code']}, Message: {error['message']}"
            if 'error_chain' in error and error['error_chain']:
                error_message += f", Error Chain: {self.format_errors(error['error_chain'])}"
            error_messages.append(error_message)
        return "\n".join(error_messages)


class CloudFlareAPI:
    def __init__(self, api_token: str):
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        self.account_id = self.get_account()['id']

    def get_account(self, account_name: str = None):
        url = 'https://api.cloudflare.com/client/v4/accounts'
        accounts = self.request('GET', url)
        if len(accounts) < 1: raise ValueError("No accounts linked to this api_token")
        if account_name:
            for account in accounts:
                if account['name'] == account_name:
                    return account
            raise ValueError(f"Account not found for such api_token")
        return accounts[0]

    def request(self, method: str, url: str, json: dict = None) -> dict:
        try:
            res = requests.request(method, url, headers=self.headers, json=json)
            res_data = res.json()
            res.raise_for_status()
            return res_data["result"]
        except Exception as e:
            if not res_data.get("success"):
                raise CloudflareAPIException(res_data.get('errors'))


class Config(BaseJsonFile):
    FILE_PATH = os.path.join(DB_DIR, 'cloudflare.json')

    @staticmethod
    def is_data() -> bool:
        """
        Checks for the existence of the created tunnel and account
        """
        config = JsonEditor.read(Config.FILE_PATH)
        if not config.get('tunnel') or not config.get('account'): return False
        return True


class CFClient:
    config: "Config"
    api: "CloudFlareAPI"
    tunnel: "Tunnel"
    route: "Route"
    dns: "Dns"

    _initialized = False
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _init_subclasses(self, api: "CloudFlareAPI", config: "Config"):
        self.api = api
        self.dns = self.Dns(api=api, config=config)
        self.tunnel = self.Tunnel(api=api, config=config)
        self.route = self.Route(api=api, config=config)

    def __init__(self):
        self.config = Config()
        if self.config.is_data():
            self._initialized = True
            api_token = self.config('account', 'api_token')
            api = CloudFlareAPI(api_token)
            self._init_subclasses(api=api, config=self.config)

    def __getattr__(self, name):
        print('method:', name)
        print(self._initialized)
        if name != "init" and not self._initialized:
            raise Exception("доступ запрещен")
        return super().__getattr__(name)

    def init(self, api_token: str, zone_name: str, tunnel_name: str = 'spcs-tunnel'):
        def _check_zone():
            url = 'https://api.cloudflare.com/client/v4/zones'
            zones = self.api.request('GET', url)
            if len(zones) < 1: raise Exception("This cloudflare account have not any zones")
            for zone in zones:
                if zone_name == zone['name']: return zone
            raise Exception(f'Zone {zone_name} does not belong to this account')

        self._initialized = True
        api = CloudFlareAPI(api_token)
        self._init_subclasses(api=api, config=self.config)

        account = self.api.get_account()
        zone = _check_zone()
        new_tunnel = self.tunnel.create(tunnel_name)

        dns_record: "CFClient.Dns.DNSRecord" = {
            'type': 'CNAME',
            'proxied': True,
            "name": f"{new_tunnel['name']}.{zone_name}",
            "content": f"{new_tunnel['id']}.cfargotunnel.com"
        }
        self.dns.zone_id = zone['id']
        self.dns.create_record(dns_record)

        configObj = {
            'account': {
                'id': account['id'],
                'name': account['name'],
                'api_token': api_token
            },
            'tunnel': {
                'name': new_tunnel['name'],
                'id': new_tunnel['id'],
                'zone': {
                    'name': zone['name'],
                    'id': zone['id']
                }
            }
        }
        self.config.save(configObj)
        print(self.config.data)
        return {'tunnel_id': new_tunnel['id'], 'account_id': account['id'], 'zone_id': zone['id']}


    class Dns:
        class DNSRecord(TypedDict):
            type: str
            proxied: str
            name: str
            content: str

        def __init__(self, api: "CloudFlareAPI", config: "Config"):
            self.api = api
            self.config = config
            self.zone_id = config('tunnel', 'zone', 'id')

        def get_records(self) -> tuple[DNSRecord]:
            url = f'https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records'
            records = self.api.request(method='GET', url=url)
            self.config = records
            return records

        def check_record(self, record_name: str) -> DNSRecord:
            records = self.get_records()
            if len(records) < 1: return None
            for record in records:
                if record['name'] == record_name: return record
            return None

        def create_record(self, data: DNSRecord) -> DNSRecord:
            exists_zone = self.check_record(data['name'])
            if exists_zone: return exists_zone
            
            url = f'https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records'
            return self.api.request(method='POST', url=url, json=data)


    class Tunnel:
        class TunnelObj(TypedDict):
            id: str
            name: str
            status: str

        def __init__(self, api: "CloudFlareAPI", config: "Config"):
            self.api = api
            self.config = config

        def _check(self, tunnel_name) -> None | TunnelObj:
            url = f'https://api.cloudflare.com/client/v4/accounts/{self.config('tunnel', 'id')}/cfd_tunnel'
            tunnels = self.api.request('GET', url)

            for tunnel in tunnels:
                if tunnel['name'] == tunnel_name:
                    return tunnel
            return None

        def create(self, tunnel_name = None) -> TunnelObj:
            if not tunnel_name: tunnel_name = 'spcs-tunnel'

            tunnel: "CFClient.Tunnel.TunnelObj" = self._check(tunnel_name)
            if not tunnel:
                data = {
                    "name": tunnel_name,
                    "config_src": "cloudflare"
                }
                url = f'https://api.cloudflare.com/client/v4/accounts/{self.api.account_id}/cfd_tunnel'
                tunnel = self.api.request('POST', url, json=data)

            self.tunnel_name = tunnel_name
            self.tunnel_id = tunnel['id']
            return tunnel

        def delete(self) -> str:
            url = f'https://api.cloudflare.com/client/v4/accounts/{self.api.account_id}/cfd_tunnel/{self.config('tunnel', 'id')}'
            res: "CFClient.Tunnel.TunnelObj" = self.api.request('DELETE', url)
            self.config.set('tunnel', value={})
            print('deleted')
            print(self.config.data)
            self.config.save()
            return res['id']

        def status(self) -> str:
            url = f'https://api.cloudflare.com/client/v4/accounts/{self.api.account_id}/cfd_tunnel/{self.config('tunnel', 'id')}'
            res: "CFClient.Tunnel.TunnelObj" = self.api.request('GET', url)
            return res['status']


    class Route:
        class IngressRoute(TypedDict):
            hostname: str
            service: str

        def __init__(self, api: "CloudFlareAPI", config: "Config"):
            self.api = api
            self.config = config
            self.account_id = config('account', 'id')
            self.tunnel_id = config('tunnel', 'id')
        
        def add(self, route: "IngressRoute") -> None:
            url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/cfd_tunnel/{self.tunnel_id}/configurations'
            res = self.api.request(method='GET', url=url)

            ingress: list = res['ingress']
            ingress.insert(0, route)
            ingress.append({ "service": "http_status:404" })

            data = {
                "config": {
                    "ingress": ingress
                }
            }

            url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/cfd_tunnel/{self.tunnel_id}/configurations'
            self.api.request(method='PUT', url=url, json=data)
 
        def delete(self, hostname: str):
            url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/cfd_tunnel/{self.tunnel_id}/configurations'
            res = self.api.request(method='GET', url=url)

            ingress: list = res['ingress']
            if len(ingress) > 0:
                ingress = [route for route in ingress if route['hostname'] != hostname]
            ingress.append({ "service": "http_status:404" })

            data = {
                "config": {
                    "ingress": ingress
                }
            }

            url = f'https://api.cloudflare.com/client/v4/accounts/{self.account_id}/cfd_tunnel/{self.tunnel_id}/configurations'
            self.api.request(method='PUT', url=url, json=data)


