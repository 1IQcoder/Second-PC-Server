import subprocess

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
