import os


def clean_up():
    folder_path = "flaskr/templates/dcf/temp"
    if os.path.exists(folder_path):
        files = os.listdir(folder_path)
        for file in files:
            if file.endswith(".html"):
                file_path = os.path.join(folder_path, file)
                os.remove(file_path)

    folder_path = "flaskr/data/dcf/temp"

    if os.path.exists(folder_path):
        files = os.listdir(folder_path)
        for file in files:
            if file.endswith(".xlsx"):
                file_path = os.path.join(folder_path, file)
                os.remove(file_path)


clean_up()
