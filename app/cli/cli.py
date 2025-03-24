"""
Build guide:
    pyinstaller --add-data "../core;core" --distpath ../../build/ --workpath ../../build/trash/ --hidden-import=requests --clean -y cli.py
"""

"""
commands:
    cf login <cloudflare_api_token>

    tunnel create name=<name: optional> zone=<zone: optional>
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
from core import GitHubRepo

def cf_check(func):
    """
    Cloudflare account and tunnel check
    """
    def wrapper():
        
        func()
    return wrapper

class TunnelCommands:
    @staticmethod
    def create():
        print('create')

    @staticmethod
    def delete():
        print('delete')

    @staticmethod
    def status():
        print('status')


# class RouteCommands:


def main():
    if len(sys.argv) < 2:
        print("No command provided")
        sys.exit(1)

    command = sys.argv[1]
    args_list = sys.argv[2:]

    parser = argparse.ArgumentParser(prog=command, description="SPCS CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    if command == "cf":
        login_parser = subparsers.add_parser("login", help="Authenticate using Cloudflare API token")
        login_parser.add_argument("cloudflare_api_token", type=str, help="Cloudflare API token")
        login_parser.set_defaults(func=login)

    elif command == "tunnel":
        tunnel_parser = argparse.ArgumentParser(prog="tunnel", description="Manage tunnels")
        tunnel_subparsers = tunnel_parser.add_subparsers(dest="tunnel_command", required=True)

        create_parser = tunnel_subparsers.add_parser("create", help="Create a new tunnel")
        create_parser.add_argument("--name", type=str, default="default_tunnel", help="Tunnel name (optional)")
        create_parser.add_argument("--zone", type=str, default="default_zone", help="Cloudflare zone (optional)")
        create_parser.set_defaults(func=tunnel_create)

        delete_parser = tunnel_subparsers.add_parser("delete", help="Delete an existing tunnel")
        delete_parser.set_defaults(func=tunnel_delete)

        status_parser = tunnel_subparsers.add_parser("status", help="Check tunnel status")
        status_parser.set_defaults(func=tunnel_status)

        args = tunnel_parser.parse_args(args_list)
        args.func(args)
        return

    elif command == "route":
        route_parser = argparse.ArgumentParser(prog="route", description="Manage routing")
        route_subparsers = route_parser.add_subparsers(dest="route_command", required=True)

        all_parser = route_subparsers.add_parser("all", help="Show all routes")
        all_parser.set_defaults(func=route_all)

        app_parser = route_subparsers.add_parser("app", help="Create an app route")
        app_parser.add_argument("name", type=str, help="App name")
        app_parser.add_argument("port", type=int, help="App port")
        app_parser.set_defaults(func=route_app)

        remove_parser = route_subparsers.add_parser("remove", help="Remove a route")
        remove_parser.add_argument("name", type=str, help="Route name to remove")
        remove_parser.set_defaults(func=route_remove)

        args = route_parser.parse_args(args_list)
        args.func(args)
        return

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    args = parser.parse_args(args_list)
    args.func(args)

if __name__ == "__main__":
    main()

