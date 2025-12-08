import asyncio
import os


class DataUploader:
    """TCP 소켓 기반 파일 업로드 클라이언트"""
    
    DEFAULT_HOST = "114.108.139.100"
    DEFAULT_PORT = 8600
    CHUNK_SIZE = 64 * 1024
    READ_TIMEOUT = 300

    def __init__(self, host: str = None, port: int = None):
        self.host = host or self.DEFAULT_HOST
        self.port = port or self.DEFAULT_PORT
        self.reader = None
        self.writer = None

    async def connect(self):
        """서버 연결"""
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port, limit=256 * 1024
        )
        self.writer.transport.set_write_buffer_limits(high=0)

    async def close(self):
        """연결 종료"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def _send(self, msg: str):
        """메시지 전송"""
        self.writer.write(msg.encode())
        await self.writer.drain()
        await asyncio.sleep(0.1)

    async def _send_file(self, file_path: str, on_progress=None):
        """파일 데이터 전송"""
        filesize = os.path.getsize(file_path)
        sent = 0
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                self.writer.write(chunk)
                await self.writer.drain()
                sent += len(chunk)
                if on_progress:
                    on_progress(sent, filesize)

    async def _read_loop(self, file_path: str, token: str, table_sn: str, 
                         table_name: str, file_type: str, on_progress=None):
        """서버 요청에 응답"""
        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)

        while True:
            try:
                data = await asyncio.wait_for(
                    self.reader.read(1024), 
                    timeout=self.READ_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise ConnectionError(f"서버 응답 타임아웃 ({self.READ_TIMEOUT}s)")

            if not data:
                raise ConnectionError("서버 연결 종료")

            msg = data.decode().strip()

            if msg == "CLOSE":
                break
            elif msg == "UID":
                await self._send("PASS")
            elif msg == "FILESIZE":
                await self._send(str(filesize))
            elif msg == "TOKEN":
                await self._send(token)
            elif msg == "TABLENAME":
                await self._send(table_name)
            elif msg == "TABLENSN":
                await self._send(str(table_sn))
            elif msg == "FILETYPE":
                await self._send(file_type)
            elif msg == "FILENAME":
                await self._send(filename)
            elif msg == "FILEDATA":
                await self._send_file(file_path, on_progress)

    async def upload(self, file_path: str, token: str, table_sn: str,
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
            await self.connect()
            await asyncio.gather(
                self._read_loop(file_path, token, table_sn, table_name, file_type, on_progress),
                self._send("START")
            )
            return True
        except Exception as e:
            print(f"업로드 에러: {e}")
            return False
        finally:
            await self.close()

    @classmethod
    async def upload_file(cls, file_path: str, token: str, table_sn: str,
                          table_name: str = "build_process", file_type: str = "STTLG",
                          on_progress=None) -> bool:
        """편의 메서드: 단일 파일 업로드"""
        uploader = cls()
        return await uploader.upload(file_path, token, table_sn, table_name, file_type, on_progress)
