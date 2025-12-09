import socket
import os
import time


class DataUploader:
    """TCP 소켓 기반 파일 업로드 클라이언트"""

    DEFAULT_HOST = "114.108.139.100"
    DEFAULT_PORT = 8501
    CHUNK_SIZE = 64 * 1024
    READ_TIMEOUT = 300

    def __init__(self, host: str = None, port: int = None):
        self.host = host or self.DEFAULT_HOST
        self.port = port or self.DEFAULT_PORT
        self.sock = None

    def connect(self):
        """서버 연결"""
        print(f"[DEBUG] 서버 연결 시도: {self.host}:{self.port}")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.READ_TIMEOUT)
        self.sock.connect((self.host, self.port))
        print("[DEBUG] 서버 연결 성공")

    def close(self):
        """연결 종료"""
        if self.sock:
            self.sock.close()
            self.sock = None

    def _send(self, msg: str):
        """메시지 전송"""
        self.sock.sendall(msg.encode())
        time.sleep(0.1)

    def _send_file(self, file_path: str, on_progress=None):
        """파일 데이터 전송"""
        filesize = os.path.getsize(file_path)
        sent = 0
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                self.sock.sendall(chunk)
                sent += len(chunk)
                if on_progress:
                    on_progress(sent, filesize)

    def _read_loop(self, file_path: str, token: str, table_sn: str,
                   table_name: str, file_type: str, on_progress=None):
        """서버 요청에 응답"""
        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)
        print(f"[DEBUG] 업로드 시작: {filename} ({filesize} bytes)")
        print(f"[DEBUG] table_name={table_name}, table_sn={table_sn}, file_type={file_type}")

        while True:
            try:
                data = self.sock.recv(1024)
            except socket.timeout:
                raise ConnectionError(f"서버 응답 타임아웃 ({self.READ_TIMEOUT}s)")

            if not data:
                raise ConnectionError("서버 연결 종료")

            msg = data.decode().strip()
            print(f"[DEBUG] 서버 요청: {msg}")

            if msg == "CLOSE":
                print("[DEBUG] 업로드 완료 - CLOSE 수신")
                break
            elif msg == "UID":
                print("[DEBUG] -> PASS 전송")
                self._send("PASS")
            elif msg == "FILESIZE":
                print(f"[DEBUG] -> 파일크기 전송: {filesize}")
                self._send(str(filesize))
            elif msg == "TOKEN":
                print(f"[DEBUG] -> 토큰 전송: {token[:20]}...")
                self._send(token)
            elif msg == "TABLENAME":
                print(f"[DEBUG] -> 테이블명 전송: {table_name}")
                self._send(table_name)
            elif msg == "TABLENSN":
                print(f"[DEBUG] -> 테이블SN 전송: {table_sn}")
                self._send(str(table_sn))
            elif msg == "FILETYPE":
                print(f"[DEBUG] -> 파일타입 전송: {file_type}")
                self._send(file_type)
            elif msg == "FILENAME":
                print(f"[DEBUG] -> 파일명 전송: {filename}")
                self._send(filename)
            elif msg == "FILEDATA":
                print("[DEBUG] -> 파일 데이터 전송 시작...")
                self._send_file(file_path, on_progress)
                print("[DEBUG] -> 파일 데이터 전송 완료")
            else:
                print(f"[DEBUG] 알 수 없는 요청: {msg}")

    def upload(self, file_path: str, token: str, table_sn: str,
               table_name: str = "build_process", file_type: str = "STTLG",
               on_progress=None) -> bool:
        """
        파일 업로드

        Args:
            file_path: 업로드할 파일 경로
            token: 인증 토큰
            table_sn: 테이블 SN (build_id)
            table_name: 테이블 이름 (기본: build_process)
            file_type: 파일 타입
                - RTISN: 스캐닝 이미지
                - RTIDP: 디포지션 이미지
                - PSTTLGF: 로그 파일 V1
                - PSTTLGS: 로그 파일 V2
                - STTLG: 기타 로그
                - MEPIG: 멜트풀 이미지
                - MEPBR: 멜트풀 브라이트
            on_progress: 진행률 콜백 (sent, total)

        Returns:
            성공 여부
        """
        if not os.path.exists(file_path):
            return False

        try:
            self.connect()
            self._send("START")
            self._read_loop(file_path, token, table_sn, table_name, file_type, on_progress)
            return True
        except Exception as e:
            print(f"업로드 에러: {e}")
            return False
        finally:
            self.close()

    @classmethod
    def upload_file(cls, file_path: str, token: str, table_sn: str,
                    table_name: str = "build_process", file_type: str = "STTLG",
                    on_progress=None) -> bool:
        """편의 메서드: 단일 파일 업로드"""
        uploader = cls()
        return uploader.upload(file_path, token, table_sn, table_name, file_type, on_progress)
