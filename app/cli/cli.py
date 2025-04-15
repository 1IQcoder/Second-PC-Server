"""
Build guide:
    cd app/cli
    pyinstaller --add-data "../core;core" --distpath ../../build/ --workpath ../../build/trash/ --hidden-import=requests --clean -y cli.py

Debug command:
    cd app
    python -m cli.cli
"""

"""
commands:
    init <cloudflare_api_token> name=<name: optional> zone=<zone: optional>

    tunnel delete
    tunnel status

    route all
    route app <name> <port>
    route remove <name>

    server status
    server launch
    server stop
"""

import sys, argparse
from core import CFClient

cf_client = CFClient()

print("CF_CLIENT:", cf_client)
print("CF_CLIENT INIT:", getattr(cf_client, "_initialized", "NO ATTRIBUTE"))


import sys
from core import CFClient

cf_client = CFClient()

def main():
    args = sys.argv

    if not args:
        print("Ошибка: команда не указана")
        return

    command = args[0]

    match command:
        case "init":
            if len(args) < 2:
                print("Ошибка: не указан API-токен")
                return
            api_token = args[1]
            name = None
            zone = None
            for arg in args[2:]:
                if arg.startswith("name="):
                    name = arg.split("=", 1)[1]
                elif arg.startswith("zone="):
                    zone = arg.split("=", 1)[1]
            cf_client.init(api_token=api_token, zone_name=zone)

        case "tunnel":
            if len(args) < 2:
                print("Ошибка: подкоманда не указана (delete/status)")
                return
            match args[1]:
                case "delete":
                    cf_client.tunnel.delete()
                case "status":
                    cf_client.tunnel.status()
                case _:
                    print(f"Ошибка: неизвестная подкоманда {args[1]}")

        case "route":
            if len(args) < 2:
                print("Ошибка: подкоманда не указана (all/app/remove)")
                return
            match args[1]:
                case "all":
                    cf_client.route.all()
                case "app":
                    if len(args) < 4:
                        print("Ошибка: недостаточно аргументов для route app")
                        return
                    name = args[2]
                    port = int(args[3])
                    cf_client.route.app(name, port)
                case "remove":
                    if len(args) < 3:
                        print("Ошибка: не указано имя маршрута")
                        return
                    name = args[2]
                    cf_client.route.remove(name)
                case _:
                    print(f"Ошибка: неизвестная подкоманда {args[1]}")

        case "server":
            if len(args) < 2:
                print("Ошибка: подкоманда не указана (status/launch/stop)")
                return
            match args[1]:
                case "status":
                    cf_client.server.status()
                case "launch":
                    cf_client.server.launch()
                case "stop":
                    cf_client.server.stop()
                case _:
                    print(f"Ошибка: неизвестная подкоманда {args[1]}")

        case _:
            print(f"Ошибка: неизвестная команда {command}")

if __name__ == "__main__":
    sys.argv = ["init", "PF19RM-La5RcSe4GpdsenHDYPds4E-wT5xRwQjxW", "zone=spc-server.xyz"]
    main()

