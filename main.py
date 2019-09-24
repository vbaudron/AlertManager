import sys
from os import listdir
from os.path import join, isfile

from model import alert

scripts_folder_name = "scripts"


def get_script_files():
    try:
        file_names = [
            join(scripts_folder_name, f) for f in listdir(scripts_folder_name) if isfile(join(scripts_folder_name, f))
        ]
        return file_names
    except Exception as e:
        print(e)
        return None


def launch_script(globals=None):
    scripts = get_script_files()
    for param in sys.argv:
        if param in scripts:
            print("==>  |", param, "FOUND |  <==")
            file_name = param.split("/")[1]
            print(file_name)
            if globals is None:
                globals = {}
            globals.update({
                "__file__": param,
                "__name__": "__main__",
            })
            with open(param, "rb") as file:
                exec(compile(file.read(), file_name , 'exec'), globals)



if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) > 1:
        launch_script()
    else:
        alert.startAlertScript()