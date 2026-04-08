import os.path
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import DOWNLOAD_PATH

# 파일 경로 설정을 위한 라이브러리 추가
import os

# 프로젝트 루트 경로 계산
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'token.json')

# 구글 드라이브 접근 권한 범위
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly']

class GoogleDriveManager:
    def __init__(self):
        self.creds = self._authenticate()
        self.service = build('drive', 'v3', credentials=self.creds)

    def _authenticate(self):
        """OAuth2 인증을 수행하고 token.json을 생성/로드합니다."""
        creds = None
        # 기존에 저장된 인증 토큰이 있는지 확인 (절대 경로 사용)
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
        # 유효한 인증 정보가 없으면 새로 로그인 수행
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_PATH):
                    raise FileNotFoundError(f"'{CREDENTIALS_PATH}' 파일을 찾을 수 없습니다. 구글 클라우드 콘솔에서 다운로드하여 프로젝트 루트에 저장해 주세요.")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES)
                # 로컬 서버(윈도우)에서 브라우저를 띄워 인증받음
                creds = flow.run_local_server(port=0)
            
            # 다음 실행을 위해 인증 정보를 token.json에 저장 (절대 경로 사용)
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        
        return creds

    def upload_file(self, file_path, folder_id=None):
        """파일을 구글 드라이브로 업로드하고 File ID를 반환합니다."""
        file_name = os.path.basename(file_path)
        
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, resumable=True)
        
        print(f"Uploading {file_name} to Google Drive...")
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            print(f"Upload complete. File ID: {file_id}")
            return file_id
        except Exception as e:
            print(f"An error occurred during upload: {e}")
            return None

    def get_folder_id(self, folder_name, parent_id=None):
        """특정 이름의 폴더 ID를 검색하여 반환합니다."""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        else:
            query += " and 'root' in parents"
            
        try:
            results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            items = results.get('files', [])
            if not items:
                return None
            return items[0]['id']
        except Exception as e:
            print(f"Error searching for folder {folder_name}: {e}")
            return None

    def create_folder(self, folder_name, parent_id=None):
        """특정 이름의 폴더를 생성하고 폴더 ID를 반환합니다."""
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        try:
            file = self.service.files().create(body=file_metadata, fields='id').execute()
            return file.get('id')
        except Exception as e:
            print(f"Error creating folder: {e}")
            return None

    def get_or_create_folder(self, folder_name, parent_id=None):
        """폴더가 있으면 ID를, 없으면 생성 후 ID를 반환합니다."""
        folder_id = self.get_folder_id(folder_name, parent_id)
        if folder_id:
            return folder_id
        return self.create_folder(folder_name, parent_id)

    def ensure_path(self, path_string):
        """
        'blackboard/과목명/유형' 과 같은 경로를 받아 구글 드라이브에 폴더들을
        순차적으로 찾거나 만들어 최종 대상 폴더의 ID를 반환합니다.
        """
        parts = [p for p in path_string.split('/') if p.strip()]
        current_parent = None
        for part in parts:
            current_parent = self.get_or_create_folder(part, current_parent)
            if not current_parent:
                print(f"Failed to create or find folder: {part}")
                return None
        return current_parent

if __name__ == '__main__':
    # 테스트 실행
    drive = GoogleDriveManager()
    drive.upload_file("test.txt") # 실제 파일이 있을 때 테스트 가능
