import requests, json

class Request:
    def request(self, method: str):
        json_type_header = { "Content-Type": "application/json" }
        method = method.lower()

        if method != 'get':
            self.headers.update(json_type_header)

        if method == 'get':
            res = requests.get(self.url, headers=self.headers)
        elif method == 'post':
            res = requests.post(self.url, headers=self.headers, data=self.json_data)
        elif method == 'put':
            res = requests.put(self.url, headers=self.headers, data=self.json_data)
        elif method == 'delete':
            res = requests.delete(self.url, headers=self.headers, data=self.json_data)
        return res

    def res(self):
        return self.res_data

    def __init__(self, method: str, url: str, headers: dict = None, data: dict = None):
        self.url = url
        self.headers = headers
        self.json_data = json.dumps(data)
        print(f'\n(\n    Request {method}: {url}\n    headers: {self.headers}\n    data: {self.json_data}\n)')

        try:
            res = self.request(method)
        except Exception as e: print(e)
        res_data = res.json()
        print(f'(\n    Responce: ({res.status_code})\n    Result data: {res_data}\n)')
        self.res_data = res_data
        

account_id = "0edfa044863951378df23b4e63d73d95"
api_token = "PF19RM-La5RcSe4GpdsenHDYPds4E-wT5xRwQjxW"
zone_name = "spc-server.xyz"
zone_id = "cfa8f14c6a77d25454f00fc3715a6847"
tunnel_name = "api-test3"

headers = {
    "Authorization": f"Bearer {api_token}"
}


print('Creating a tunnel')
req = Request(
    method = 'post',
    url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel',
    headers = headers,
    data = {
        "name": tunnel_name,
        "config_src": "cloudflare"
    }
)
tunnel_id = req.res()['result']['id']


print('Connecting an application')
req = Request(
    method = 'put',
    url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations',
    headers = headers,
    data = {
        "config": {
            "ingress": [
            {
                "hostname": f"{tunnel_name}.{zone_name}",
                "service": "http://172.24.240.192:3001",
                "originRequest": {}
            },
            {
                "service": "http_status:404"
            }
            ]
        }
    }
)


print('Creating a DNS record')
req = Request(
    method = 'post',
    url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records',
    headers = headers,
    data = {
        "type": "CNAME",
        "proxied": True,
        "name": f"{tunnel_name}.{zone_name}",
        "content": f"{tunnel_id}.cfargotunnel.com"
    }
)


print('Verifying tunnel status')
req = Request(
    method = 'get',
    url = f'https://api.cloudflare.com/client/v4/accounts/{account_id}/cfd_tunnel/{tunnel_id}',
    headers = headers
)


# e84dabc8-70e7-417a-b6a0-b58996c2689b











