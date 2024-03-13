import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload
from datetime import datetime
import pytz 
import json
def download_files_if_modified(service, folder_id, download_path):
    """
    Google Drive의 특정 폴더 내에 있는 파일들을 최근 수정 날짜가 저장된 파일보다 최근이면 다운로드합니다.
    :param service: Google Drive service 객체
    :param folder_id: Google Drive 폴더의 ID
    :param download_path: 파일을 다운로드할 로컬 경로
    :return: None
    """
    # 폴더 내의 파일 목록을 가져옵니다.
    results = service.files().list(q=f"'{folder_id}' in parents", pageSize=1000, fields="nextPageToken, files(id, name, mimeType, modifiedTime)").execute()
    items = results.get('files', [])

    if not items:
        print('폴더 내에 파일이 없습니다.')
    else:
        for item in items:
            # 폴더인 경우 재귀적으로 하위 폴더의 파일을 다운로드합니다.
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                folder_path = os.path.join(download_path, item['name'])
                os.makedirs(folder_path, exist_ok=True)
                download_files_if_modified(service, item['id'], folder_path)
                continue
            # 파일인 경우 다운로드합니다.
            # 파일 정보 추출
            file_id = item['id']
            file_name = item['name']
            file_path = os.path.join(download_path, file_name)

            # Google Drive 파일의 최종 수정 날짜 가져오기
            modified_time_str = item.get('modifiedTime')
            modified_time_utc = datetime.fromisoformat(modified_time_str.replace('Z', '+00:00'))
            
            # UTC 시간을 한국 시간으로 변환
            timezone_kr = pytz.timezone('Asia/Seoul')
            modified_time = modified_time_utc.astimezone(timezone_kr)

            # modified_time = datetime.strptime(str(modified_time), "%Y-%m-%d")
            # 로컬에 저장된 파일의 최종 수정 날짜 가져오기
            local_modified_time = None
            if os.path.exists(file_path):
                local_modified_time = datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone_kr)
                # local_modified_time = datetime.strptime(str(local_modified_time), "%Y-%m-%d")

            
            # 로컬 파일이 없거나 Google Drive 파일이 더 최근에 수정되었으면 다운로드
            results = service.files().list(q=f"'{folder_id}' in parents", pageSize=1, fields="nextPageToken, files(id, name, mimeType, modifiedTime)").execute()
            it = results.get('files', [])
            if not local_modified_time or modified_time > local_modified_time:
                print(f'{file_name}의 최종 수정 날짜: {modified_time}')
                print(modified_time, local_modified_time)
                print(f'{file_name}을 다운로드합니다...')
                download_single_file(service, file_id, file_path)
            else:
                print(f'{file_name}은(는) 최신 상태입니다. 다운로드하지 않습니다.')
                print(modified_time, local_modified_time)

def download_single_file(service, file_id, file_path):
    """
    :param service: Google Drive service 객체
    :param file_id: Google Drive 파일의 ID
    :param file_path: 파일을 다운로드할 로컬 경로
    :return: None
    """
    request = service.files().get_media(fileId=file_id)
    try:
        with open(file_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                try:
                    status, done = downloader.next_chunk()
                    print(f'다운로드 진행 상황: {int(status.progress() * 100)}%')
                except:
                    done=True
    except:
        pass
    print(f'{file_path} 다운로드 완료.')

SCOPES = ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/drive"]
creds = None
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except:
            flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

service = build('drive', 'v3', credentials=creds)

def loadJson(dir :str):
    """Json 파일에서 데이터 로드

    Args:
        dir (str): 파일 경로

    Returns:
        Any: Json 파일에 저장된 데이터
    """
    with open(dir, 'r') as file:
        ls = json.load(file)
    return ls

config = loadJson('./config.json')
fileIds = config["fileIds"]
download_path = config['fileSavePath']
for fileId in fileIds:
    download_files_if_modified(service, fileId, download_path)
input("종료하려면 엔터를 누르세요.")