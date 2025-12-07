import sys
import asyncio
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QSpinBox, QComboBox
)
from PyQt5.QtCore import QThread, pyqtSignal
from Modules import DataFetcher, Company


class WorkerThread(QThread):
    """백그라운드 작업 스레드"""
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, task_type, **kwargs):
        super().__init__()
        self.task_type = task_type
        self.kwargs = kwargs

    def run(self):
        """비동기 작업 실행"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if self.task_type == "login":
                result = loop.run_until_complete(self.do_login())
            elif self.task_type == "test":
                result = loop.run_until_complete(self.do_test())
            else:
                result = "알 수 없는 작업"

            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(f"에러: {str(e)}")
        finally:
            loop.close()

    async def do_login(self):
        """로그인 수행"""
        user_id = self.kwargs.get("user_id")
        user_pw = self.kwargs.get("user_pw")

        self.progress.emit(f"로그인 중: {user_id}")
        token = await DataFetcher.login(user_id, user_pw)

        if token:
            return f"SUCCESS:{token}"
        else:
            return "FAIL:로그인 실패"

    async def do_test(self):
        """데이터 테스트 수행"""
        token = self.kwargs.get("token")
        build_id = self.kwargs.get("build_id")
        layer = self.kwargs.get("layer")
        company = self.kwargs.get("company")
        test_type = self.kwargs.get("test_type")

        fetcher = DataFetcher(token, build_id, company)

        if test_type == "log":
            self.progress.emit("로그 데이터 조회 중...")
            log_data = await fetcher.fetch_log()

            if log_data:
                filename = "log_data.csv"
                with open(filename, "wb") as f:
                    f.write(log_data)
                return f"로그 데이터 성공\n크기: {len(log_data)} bytes\n저장: {filename}"
            else:
                return "로그 데이터 조회 실패"

        elif test_type == "vision":
            self.progress.emit(f"비전 데이터 조회 중 (Layer {layer})...")
            scanning, deposition = await fetcher.fetch_vision(layer)

            results = []
            if scanning:
                filename = "scanning_image.jpg"
                with open(filename, "wb") as f:
                    f.write(scanning)
                results.append(f"✓ 스캐닝: {len(scanning)} bytes -> {filename}")
            else:
                results.append("✗ 스캐닝 실패")

            if deposition:
                filename = "deposition_image.jpg"
                with open(filename, "wb") as f:
                    f.write(deposition)
                results.append(f"✓ 디포지션: {len(deposition)} bytes -> {filename}")
            else:
                results.append("✗ 디포지션 실패")

            return "\n".join(results)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.token = None
        self.worker = None
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("RootLab API 테스트 도구")
        self.setGeometry(100, 100, 700, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 로그인 섹션
        login_group = QGroupBox("로그인")
        login_layout = QVBoxLayout()

        # ID 입력
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("ID:"))
        self.id_input = QLineEdit()
        self.id_input.setText("corp03")
        id_layout.addWidget(self.id_input)
        login_layout.addLayout(id_layout)

        # PW 입력
        pw_layout = QHBoxLayout()
        pw_layout.addWidget(QLabel("PW:"))
        self.pw_input = QLineEdit()
        self.pw_input.setEchoMode(QLineEdit.Password)
        self.pw_input.setText("*corp12#")
        pw_layout.addWidget(self.pw_input)
        login_layout.addLayout(pw_layout)

        # 로그인 버튼
        self.login_btn = QPushButton("로그인")
        self.login_btn.clicked.connect(self.on_login)
        login_layout.addWidget(self.login_btn)

        # 토큰 표시
        self.token_label = QLabel("토큰: 로그인하지 않음")
        self.token_label.setWordWrap(True)
        self.token_label.setStyleSheet("color: red; padding: 5px;")
        login_layout.addWidget(self.token_label)

        login_group.setLayout(login_layout)
        main_layout.addWidget(login_group)

        # 테스트 설정 섹션
        test_group = QGroupBox("테스트 설정")
        test_layout = QVBoxLayout()

        # Build ID
        build_layout = QHBoxLayout()
        build_layout.addWidget(QLabel("Build ID:"))
        self.build_input = QSpinBox()
        self.build_input.setRange(1, 100000)
        self.build_input.setValue(308)
        build_layout.addWidget(self.build_input)
        test_layout.addLayout(build_layout)

        # Layer
        layer_layout = QHBoxLayout()
        layer_layout.addWidget(QLabel("Layer:"))
        self.layer_input = QSpinBox()
        self.layer_input.setRange(1, 1000)
        self.layer_input.setValue(1)
        layer_layout.addWidget(self.layer_input)
        test_layout.addLayout(layer_layout)

        # Company
        company_layout = QHBoxLayout()
        company_layout.addWidget(QLabel("Company:"))
        self.company_input = QComboBox()
        self.company_input.addItems(["corp01", "corp02", "corp03"])
        self.company_input.setCurrentText("corp03")
        company_layout.addWidget(self.company_input)
        test_layout.addLayout(company_layout)

        test_group.setLayout(test_layout)
        main_layout.addWidget(test_group)

        # 테스트 버튼 섹션
        button_group = QGroupBox("테스트 실행")
        button_layout = QHBoxLayout()

        self.log_btn = QPushButton("로그 데이터 테스트")
        self.log_btn.clicked.connect(self.on_test_log)
        self.log_btn.setEnabled(False)
        button_layout.addWidget(self.log_btn)

        self.vision_btn = QPushButton("비전 데이터 테스트")
        self.vision_btn.clicked.connect(self.on_test_vision)
        self.vision_btn.setEnabled(False)
        button_layout.addWidget(self.vision_btn)

        button_group.setLayout(button_layout)
        main_layout.addWidget(button_group)

        # 결과 출력
        result_group = QGroupBox("결과")
        result_layout = QVBoxLayout()

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)

        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)

    def on_login(self):
        """로그인 버튼 클릭"""
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()

        if not user_id or not user_pw:
            self.result_text.append("❌ ID와 PW를 입력하세요\n")
            return

        self.login_btn.setEnabled(False)
        self.result_text.append(f"🔄 로그인 시도: {user_id}\n")

        self.worker = WorkerThread("login", user_id=user_id, user_pw=user_pw)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_login_finished)
        self.worker.start()

    def on_login_finished(self, result):
        """로그인 완료"""
        self.login_btn.setEnabled(True)

        if result.startswith("SUCCESS:"):
            self.token = result.split(":", 1)[1]
            self.token_label.setText(f"토큰: {self.token[:60]}...")
            self.token_label.setStyleSheet("color: green; padding: 5px;")
            self.result_text.append("✅ 로그인 성공!\n")

            # 테스트 버튼 활성화
            self.log_btn.setEnabled(True)
            self.vision_btn.setEnabled(True)
        else:
            self.token_label.setText("토큰: 로그인 실패")
            self.token_label.setStyleSheet("color: red; padding: 5px;")
            self.result_text.append(f"❌ {result.split(':', 1)[1]}\n")

    def on_test_log(self):
        """로그 테스트 버튼 클릭"""
        if not self.token:
            self.result_text.append("❌ 먼저 로그인하세요\n")
            return

        self.log_btn.setEnabled(False)
        self.result_text.append("🔄 로그 데이터 테스트 시작...\n")

        self.worker = WorkerThread(
            "test",
            token=self.token,
            build_id=str(self.build_input.value()),
            layer=self.layer_input.value(),
            company=self.company_input.currentText(),
            test_type="log"
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(lambda r: self.on_test_finished(r, "log"))
        self.worker.start()

    def on_test_vision(self):
        """비전 테스트 버튼 클릭"""
        if not self.token:
            self.result_text.append("❌ 먼저 로그인하세요\n")
            return

        self.vision_btn.setEnabled(False)
        self.result_text.append("🔄 비전 데이터 테스트 시작...\n")

        self.worker = WorkerThread(
            "test",
            token=self.token,
            build_id=str(self.build_input.value()),
            layer=self.layer_input.value(),
            company=self.company_input.currentText(),
            test_type="vision"
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(lambda r: self.on_test_finished(r, "vision"))
        self.worker.start()

    def on_test_finished(self, result, test_type):
        """테스트 완료"""
        if test_type == "log":
            self.log_btn.setEnabled(True)
        else:
            self.vision_btn.setEnabled(True)

        self.result_text.append(f"📊 결과:\n{result}\n")
        self.result_text.append("=" * 50 + "\n")

    def on_progress(self, message):
        """진행 상황 업데이트"""
        self.result_text.append(f"⏳ {message}\n")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
