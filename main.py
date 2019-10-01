import sys
from os import listdir
from os.path import join, isfile

from model import alert

scripts_folder_name = "scripts"
tests_folder_name = "test"


def get_folder_files(folder_name: str):
    try:
        file_names = [
            join(folder_name, f) for f in listdir(folder_name) if isfile(join(folder_name, f))
        ]
        return file_names
    except Exception as e:
        print(e)
        return None


def launch_script(folder_name, globals=None):
    files = get_folder_files(folder_name=folder_name)
    for param in sys.argv:
        if param in files:
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
        folder = sys.argv[1].split("/")[0]
        print("FOLDER found :", folder)
        launch_script(folder_name=folder)
    else:
        print("go alert")
        alert.startAlertScript()