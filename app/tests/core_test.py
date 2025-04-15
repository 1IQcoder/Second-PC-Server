# run command: pytest

import pytest, os
from dotenv import load_dotenv
from core import CFClient

load_dotenv()

def test_init_tunnel():
    client = CFClient()
    if client.config.is_data():
        return

    with pytest.raises(Exception) as excinfo:
        client.tunnel.status()
    assert str(excinfo.value) == "доступ запрещен"

    with pytest.raises(Exception) as excinfo:
        client.api.get_account()
    assert str(excinfo.value) == "доступ запрещен"

    res1 = client.init(os.getenv('API_TOKEN'), os.getenv('ZONE_NAME'))
    assert isinstance(res1, dict)

def test_delete_tunnel():
    client = CFClient()
    print('sadgasdg')
    status = client.tunnel.status()
    print('Status:', status)
    assert isinstance(status, str)

    tun_id = client.tunnel.delete()
    print('Id:', tun_id)
    assert isinstance(tun_id, str)