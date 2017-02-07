import httplib2
import os
import ntpath
import os.path

from apiclient import discovery
from googleapiclient.http import MediaIoBaseDownload
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'shinobooru-desktop'
shinobooruDir = "/home/firenox/T/shinobooru"

# TODO check for expired credentials
def get_credentials():
    """Gets valid user credentials from storage.
    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """

    if not os.path.isfile(CLIENT_SECRET_FILE):
        raise Exception('client_secret.json is missing. Check: https://developers.google.com/drive/v3/web/quickstart/python' )
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def get_directories():
    dirs = os.listdir(shinobooruDir)
    return map(lambda d: os.path.join(shinobooruDir, d), dirs)


def get_service():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    return discovery.build('drive', 'v3', http=http)


def get_root_dir_id(service):
    shinobooru_root_query = "name = 'Shinobooru'"
    results = service.files().list(spaces="drive", fields="files(id, name)", q=shinobooru_root_query).execute()
    items = results.get('files', [])
    if len(items) != 1:
        raise Exception("TODO handle this case")
    root_dir_id = items[0]['id']
    print('{0} ({1})'.format(items[0]['name'], items[0]['id']))
    return root_dir_id


def get_board_dirs(service, root_dir):
    board_dirs_query = "'" + root_dir + "' in parents"

    results = service.files().list(spaces="drive", fields="nextPageToken, files(id, name)", q=board_dirs_query).execute()
    items = results.get('files', [])
    boards = []
    if not items:
        raise Exception('No files found.')
    else:
        for item in items:
            boards.append([item['name'], item['id']])

    return boards


def handle_next_token(service, nextToken):
    raise Exception("TODO handle this case")

    while nextToken is not None:
        results = service.files().list(spaces="drive", pageToken=nextToken,
                                       fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        nextToken = results.get('nextPageToken')
        if not items:
            print('No files found.')
        else:
            print('Files:')
            for item in items:
                print('{0} ({1})'.format(item['name'].encode('utf-8'), item['id']))


def get_wallpaper_list():
    wallpapers = []

    for path in [shinobooruDir + "/" + board for board in os.listdir(shinobooruDir)]:
        files = os.listdir(path)
        wallpapers += [path+"/"+wallpaper for wallpaper in files]

    return wallpapers


def list_drive(service):
    posts = []

    root_dir_id = get_root_dir_id(service)
    boards = get_board_dirs(service, root_dir_id)
    for board in boards:
        board_dir_query = "'" + board[1] + "' in parents"

        results = service.files().list(spaces="drive",
                                       fields="nextPageToken, files(id, name)",
                                       q=board_dir_query,
                                       pageSize=1000).execute()
        items = results.get('files', [])

        nextToken = results.get('nextPageToken')

        if nextToken is not None:
            handle_next_token(service, nextToken)

        if not items:
            print('No files found.')
        else:
            for item in items:
                posts.append([item['name'], item['id']])

    return posts


def main():
    locallist = get_wallpaper_list()
    locallistfilenames = [ntpath.basename(path) for path in locallist]

    service = get_service()
    drivelist = list_drive(service)

    for e in drivelist:
        if not e[0] in locallistfilenames:
            print(e[0])
            subdir = e[0].split(" ")[0]
            path = shinobooruDir + "/" + subdir + "/" + e[0]
            request = service.files().get_media(fileId=e[1])
            fh = open(path, "wb")
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print("Download %d%%." % int(status.progress() * 100))


if __name__ == '__main__':
    main()
