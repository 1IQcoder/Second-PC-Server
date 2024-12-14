import subprocess, json

def run_command(command):
    print(f'run command: {command}')
    try:
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            shell=isinstance(command, str)
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, f"Error: {result.stderr.strip()}"
    except Exception as e:
        return False, f"Exception: {str(e)}"

# Пример использования
'''
success, output = run_command("ls -la" if subprocess.os.name != "nt" else "dir")
if success:
    print("Команда выполнена успешно:")
    print(output)
else:
    print("Произошла ошибка:")
    print(output)
'''


class JsonEditor():
    @staticmethod
    def overwrite(file_path, data):
        try:
            with open(file_path, 'w') as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
            print(f"Файл {file_path} успешно перезаписан.")
        except Exception as e:
            print(f"Ошибка при перезаписи файла: {e}")

    @staticmethod
    def read(file_path):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            return data
        except FileNotFoundError:
            print(f"Файл {file_path} не найден.")
            return None
        except json.JSONDecodeError:
            print(f"Файл {file_path} повреждён или не является JSON.")
            return None
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return None
        

# file_data = JsonEditor.read(r'D:\склад\txt\SecondPC-server\accounts.json')
# print(type(file_data))