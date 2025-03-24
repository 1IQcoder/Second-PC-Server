import os

app_dir = os.path.join(os.getcwd(), 'app')
bin_folder = os.path.join(app_dir, 'bin')
exe_path = os.path.join(app_dir, )
if not os.path.isdir(bin_folder): os.mkdir(bin_folder)
bats = ['cf', 'tunnel', 'route', 'server']

def create_bat_file(filename):
    filepath = os.path.join(bin_folder, filename+'.bat')

    bat_content = """@echo off\ncli/cli.exe %*"""

    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(bat_content)

for bat in bats:
    create_bat_file(bat)