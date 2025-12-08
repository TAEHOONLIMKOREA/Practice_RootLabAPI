import asyncio, os, struct, async_timeout
import asyncio
import os, sys
import struct
import async_timeout
import time
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding="utf-8")

def _emit_error(user_msg, debug_msg=None, exit_code=1):
    if debug_msg:
        print(debug_msg, flush=True)
    sys.stderr.write(user_msg + "\n")
    sys.stderr.flush()
    sys.exit(exit_code)

class Client:
    READ_TIMEOUT = 1000  # second
    def __init__(self, host: str = None, port: int = None):
        if host is None or port is None:
            # 지연 import로 순환 참조 방지
            from Modules.config_utils import file_host, file_port
            host = host or file_host
            port = port or file_port

            if not host or not port:
                _emit_error("config.json에서 file_host 또는 file_port를 찾을 수 없습니다.")
        
        self.host = host
        self.port = port
        self._chunk_size = 64 * 1024

    def reduce_chunk_size(self):
        self._chunk_size = max(self._chunk_size // 2, 1024)
        print(f"→ 신규 CHUNK_SIZE: {self._chunk_size} bytes")

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port, limit=256 * 1024
        )
        # 즉시 플러시되도록 워터마크 낮추기
        transport = self.writer.transport
        transport.set_write_buffer_limits(high=0)
    
    async def send_file(self, file_path, on_total_inc=None):
        filesize = os.path.getsize(file_path)

        total_sent = 0
        last_emit_ts    = 0.0
        last_logged_pct = -1
        EMIT_INTERVAL   = 0.2  # 필요에 따라

        self._log("[INFO]", "SEND_FILE_START")
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(self._chunk_size)
                if not chunk:
                    break

                self.writer.write(chunk)
                await self.writer.drain()

                inc = len(chunk)
                total_sent += inc

                # 파일 단위(옵션)
                pct_file = int(total_sent * 100 / filesize)
                now = time.monotonic()
                if pct_file != last_logged_pct and (now - last_emit_ts) >= EMIT_INTERVAL:
                    last_emit_ts    = now
                    last_logged_pct = pct_file
                    # print(f"FPROGRESS:{pct_file}", flush=True)  # 원하면 파일 퍼센트도

                # 🔸 전체 퍼센트 호출
                if on_total_inc:
                    on_total_inc(inc)
        self._log("[INFO]", "SEND_FILE_END")

    def _log(self, level: str, message: str):
        """통일된 로그 출력 함수"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}", flush=True)
    
    async def send_message(self, message: str):
        self.writer.write(message.encode())
        await self.writer.drain()
        await asyncio.sleep(0.1)
    
    def _print_summary(self, summary_data: dict):
        """SUMMARY 형식으로 모든 정보를 한 번에 출력"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{timestamp}] ======= PROTOCOL SUMMARY ======", flush=True)
        for key, value in summary_data.items():
            print(f"[{timestamp}] {key:12}: {value}", flush=True)
        print(f"[{timestamp}] ===================================\n", flush=True)
    
    async def _send_response(self, request_type: str, value: str):
        """SERVER RESPONSE SEND (로그 없이)"""
        await self.send_message(value)
    
    async def read_loop(self, file_path, token, tableSn, tableNm, fileType, on_total_inc):
        uid = "PASS"
        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)
        
        # SUMMARY 정보 수집
        summary_data = {
            "FILENAME": filename,
            "SERVER": f"{self.host}:{self.port}",
            "UID": uid,
            "FILESIZE": f"{filesize / 1024:.1f} KB",
            "TOKEN": f"{token[:10]}..." if len(token) > 10 else token,
            "TABLENAME": tableNm,
            "TABLENSN": str(tableSn),
            "FILETYPE": fileType
        }
        

        while True:
            try:
                async with async_timeout.timeout(self.READ_TIMEOUT):
                    data = await self.reader.read(1024)
            except asyncio.TimeoutError:
                raise ConnectionError(f"SERVER RESPONSE TIMEOUT(>{self.READ_TIMEOUT}s)")

            if not data:
                raise ConnectionError("SERVER CONNECTION CLOSED")

            msg = data.decode().strip()
            
            if msg == "CLOSE":
                self._log("[INFO]", "SERVER CLOSE REQUEST")
                self.writer.close()
                await self.writer.wait_closed()
                break
            elif msg == "UID":
                # 첫 번째 요청에서 SUMMARY 출력
                self._print_summary(summary_data)
                await self._send_response("UID", uid)
            elif msg == "FILESIZE":
                await self._send_response("FILESIZE", str(filesize))
            elif msg == "TOKEN":
                await self._send_response("TOKEN", token)
            elif msg == "TABLENAME":
                await self._send_response("TABLENAME", tableNm)
            elif msg == "TABLENSN":
                await self._send_response("TABLENSN", str(tableSn))
            elif msg == "FILETYPE":
                await self._send_response("FILETYPE", fileType)
            elif msg == "FILENAME":
                await self._send_response("FILENAME", filename)
            elif msg == "FILEDATA":
                self._log("[INFO]", f"FILE DATA [SEND START]: {filename}")
                await self.send_file(file_path, on_total_inc=on_total_inc)

    async def run(self, file_path, token, tableSn, tableNm, fileType, on_total_inc):
        await self.connect()
        # read_loop and START message send at the same time
        await asyncio.gather(
            self.read_loop(file_path, token, tableSn, tableNm, fileType, on_total_inc),
            self.send_message("START")
        )
