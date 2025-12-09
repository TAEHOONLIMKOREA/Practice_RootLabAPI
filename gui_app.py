import sys
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QSpinBox, QComboBox,
    QFileDialog, QListWidget, QListWidgetItem
)
from Modules import DataFetcher, DataUploader


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.token = None
        self.user_id = None
        self.upload_file = None
        self.file_list_data = []  # 파일 목록 데이터 저장
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RootLab API 테스트 도구")
        self.setGeometry(100, 100, 700, 850)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 로그인
        login_group = QGroupBox("로그인")
        login_layout = QVBoxLayout()

        row = QHBoxLayout()
        row.addWidget(QLabel("ID:"))
        self.id_input = QLineEdit("corp04")
        row.addWidget(self.id_input)
        login_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("PW:"))
        self.pw_input = QLineEdit("*corp12#")
        self.pw_input.setEchoMode(QLineEdit.Password)
        row.addWidget(self.pw_input)
        login_layout.addLayout(row)

        login_btn = QPushButton("로그인")
        login_btn.clicked.connect(self.on_login)
        login_layout.addWidget(login_btn)

        self.token_label = QLabel("토큰: 로그인하지 않음")
        self.token_label.setStyleSheet("color: red;")
        login_layout.addWidget(self.token_label)

        self.token_display = QLineEdit()
        self.token_display.setReadOnly(True)
        self.token_display.setPlaceholderText("로그인 후 토큰이 여기에 표시됩니다 (복사 가능)")
        login_layout.addWidget(self.token_display)

        login_group.setLayout(login_layout)
        layout.addWidget(login_group)

        # 다운로드 설정
        dl_group = QGroupBox("다운로드 설정")
        dl_layout = QVBoxLayout()

        row = QHBoxLayout()
        row.addWidget(QLabel("Build ID:"))
        self.build_input = QSpinBox()
        self.build_input.setRange(1, 100000)
        self.build_input.setValue(308)
        row.addWidget(self.build_input)
        dl_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Layer:"))
        self.layer_input = QSpinBox()
        self.layer_input.setRange(1, 1000)
        self.layer_input.setValue(1)
        row.addWidget(self.layer_input)
        dl_layout.addLayout(row)

        dl_group.setLayout(dl_layout)
        layout.addWidget(dl_group)

        # 다운로드 버튼
        btn_group = QGroupBox("데이터 다운로드")
        btn_layout = QHBoxLayout()
        log_btn = QPushButton("로그 다운로드")
        log_btn.clicked.connect(lambda: self.on_download("log"))
        btn_layout.addWidget(log_btn)
        vision_btn = QPushButton("비전 다운로드")
        vision_btn.clicked.connect(lambda: self.on_download("vision"))
        btn_layout.addWidget(vision_btn)
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)

        # 업로드
        upload_group = QGroupBox("파일 업로드")
        upload_layout = QVBoxLayout()

        row = QHBoxLayout()
        self.file_label = QLabel("파일: 선택되지 않음")
        row.addWidget(self.file_label)
        file_btn = QPushButton("파일 선택")
        file_btn.clicked.connect(self.on_select_file)
        row.addWidget(file_btn)
        upload_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("파일 타입:"))
        self.file_type_input = QComboBox()
        self.file_type_input.addItems(["STTLG", "PSTTLGF", "PSTTLGS", "RTISN", "RTIDP", "MEPIG", "MEPBR"])
        row.addWidget(self.file_type_input)
        upload_layout.addLayout(row)

        upload_btn = QPushButton("업로드")
        upload_btn.clicked.connect(self.on_upload)
        upload_layout.addWidget(upload_btn)

        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)

        # 파일 다운로드
        file_dl_group = QGroupBox("파일 다운로드")
        file_dl_layout = QVBoxLayout()

        row = QHBoxLayout()
        row.addWidget(QLabel("Table Name:"))
        self.dl_table_name = QLineEdit("build_process")
        row.addWidget(self.dl_table_name)
        file_dl_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Table SN:"))
        self.dl_table_sn = QSpinBox()
        self.dl_table_sn.setRange(1, 100000)
        self.dl_table_sn.setValue(308)
        row.addWidget(self.dl_table_sn)
        file_dl_layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("File Type:"))
        self.dl_file_type = QComboBox()
        self.dl_file_type.addItems(["PSTTLGF", "PSTTLGS", "RTISN", "RTIDP", "STTLG", "MEPIG", "MEPBR", "AINDVI", "ADSTTLG"])
        row.addWidget(self.dl_file_type)
        file_dl_layout.addLayout(row)

        search_btn = QPushButton("파일 검색")
        search_btn.clicked.connect(self.on_search_files)
        file_dl_layout.addWidget(search_btn)

        self.file_list_widget = QListWidget()
        self.file_list_widget.setMaximumHeight(100)
        file_dl_layout.addWidget(self.file_list_widget)

        download_btn = QPushButton("선택 파일 다운로드")
        download_btn.clicked.connect(self.on_download_file)
        file_dl_layout.addWidget(download_btn)

        file_dl_group.setLayout(file_dl_layout)
        layout.addWidget(file_dl_group)

        # API 테스트
        api_group = QGroupBox("API 테스트")
        api_layout = QVBoxLayout()

        row = QHBoxLayout()
        row.addWidget(QLabel("API:"))
        self.api_type_input = QComboBox()
        self.api_type_input.addItems(["machines", "retentions", "bp", "bs", "designs", "materials", "files"])
        self.api_type_input.currentTextChanged.connect(self.on_api_type_changed)
        row.addWidget(self.api_type_input)
        api_layout.addLayout(row)

        # BP용 Retention SN
        self.retention_row = QHBoxLayout()
        self.retention_row.addWidget(QLabel("Retention SN:"))
        self.retention_sn_input = QSpinBox()
        self.retention_sn_input.setRange(1, 100000)
        self.retention_sn_input.setValue(1219)
        self.retention_row.addWidget(self.retention_sn_input)
        api_layout.addLayout(self.retention_row)

        # Files용 파라미터
        self.file_params = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("Table Name:"))
        self.api_table_name = QLineEdit("design")
        row.addWidget(self.api_table_name)
        self.file_params.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Table SN:"))
        self.api_table_sn = QSpinBox()
        self.api_table_sn.setRange(1, 100000)
        self.api_table_sn.setValue(1274)
        row.addWidget(self.api_table_sn)
        self.file_params.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("File Type:"))
        self.api_file_type = QLineEdit("WSTSL")
        row.addWidget(self.api_file_type)
        self.file_params.addLayout(row)
        api_layout.addLayout(self.file_params)

        api_btn = QPushButton("API 조회")
        api_btn.clicked.connect(self.on_api_test)
        api_layout.addWidget(api_btn)

        api_group.setLayout(api_layout)
        layout.addWidget(api_group)

        self.on_api_type_changed("machines")

        # 결과
        result_group = QGroupBox("결과")
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

    def log(self, msg):
        self.result_text.append(msg)

    def on_login(self):
        user_id = self.id_input.text().strip()
        user_pw = self.pw_input.text().strip()
        if not user_id or not user_pw:
            self.log("❌ ID와 PW를 입력하세요\n")
            return

        self.log(f"🔄 로그인 시도: {user_id}\n")
        token = DataFetcher.login(user_id, user_pw)

        if token:
            self.token = token
            self.user_id = user_id
            self.token_label.setText("토큰: 로그인 성공")
            self.token_label.setStyleSheet("color: green;")
            self.token_display.setText(token)
            self.log("✅ 로그인 성공!\n")
        else:
            self.token_label.setText("토큰: 로그인 실패")
            self.token_label.setStyleSheet("color: red;")
            self.token_display.clear()
            self.log("❌ 로그인 실패\n")

    def on_download(self, dl_type):
        if not self.token:
            self.log("❌ 먼저 로그인하세요\n")
            return

        self.log(f"🔄 {dl_type} 다운로드 시작...\n")
        fetcher = DataFetcher(self.token, str(self.build_input.value()), self.user_id)

        if dl_type == "log":
            data = fetcher.fetch_log()
            if data:
                with open("log_data.csv", "wb") as f:
                    f.write(data)
                self.log(f"✅ 로그 다운로드 완료 ({len(data)} bytes)\n")
            else:
                self.log("❌ 로그 다운로드 실패\n")
        else:
            scanning, deposition = fetcher.fetch_vision(self.layer_input.value())
            if scanning:
                with open("scanning_image.jpg", "wb") as f:
                    f.write(scanning)
                self.log(f"✓ 스캐닝: {len(scanning)} bytes\n")
            else:
                self.log("✗ 스캐닝 실패\n")
            if deposition:
                with open("deposition_image.jpg", "wb") as f:
                    f.write(deposition)
                self.log(f"✓ 디포지션: {len(deposition)} bytes\n")
            else:
                self.log("✗ 디포지션 실패\n")

        self.log("=" * 50 + "\n")

    def on_select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택")
        if path:
            self.upload_file = path
            self.file_label.setText(f"파일: {os.path.basename(path)}")

    def on_upload(self):
        if not self.token:
            self.log("❌ 먼저 로그인하세요\n")
            return
        if not self.upload_file:
            self.log("❌ 파일을 선택하세요\n")
            return

        file_type = self.file_type_input.currentText()
        self.log(f"🔄 업로드 시작: {file_type}\n")

        success = DataUploader.upload_file(
            self.upload_file, self.token, str(self.build_input.value()), "build_process", file_type
        )
        self.log("✅ 업로드 성공\n" if success else "❌ 업로드 실패\n")
        self.log("=" * 50 + "\n")

    def on_api_type_changed(self, api_type):
        show_retention = api_type == "bp"
        for i in range(self.retention_row.count()):
            w = self.retention_row.itemAt(i).widget()
            if w:
                w.setVisible(show_retention)

        show_files = api_type == "files"
        for i in range(self.file_params.count()):
            item = self.file_params.itemAt(i).layout()
            if item:
                for j in range(item.count()):
                    w = item.itemAt(j).widget()
                    if w:
                        w.setVisible(show_files)

    def on_api_test(self):
        if not self.token:
            self.log("❌ 먼저 로그인하세요\n")
            return

        api_type = self.api_type_input.currentText()
        self.log(f"🔄 API 조회: {api_type}\n")

        fetcher = DataFetcher(self.token)
        if api_type == "machines":
            data = fetcher.get_machines()
        elif api_type == "retentions":
            data = fetcher.get_machine_retentions()
        elif api_type == "bp":
            data = fetcher.get_build_processes(self.retention_sn_input.value())
        elif api_type == "bs":
            data = fetcher.get_build_strategies()
        elif api_type == "designs":
            data = fetcher.get_designs()
        elif api_type == "materials":
            data = fetcher.get_materials()
        elif api_type == "files":
            data = fetcher.get_files(self.api_table_name.text(), self.api_table_sn.value(), self.api_file_type.text())
        else:
            data = None

        if data:
            self.log(f"조회 성공 ({len(data)}건)\n{json.dumps(data, indent=2, ensure_ascii=False)}\n")
        else:
            self.log("데이터 없음\n")
        self.log("=" * 50 + "\n")

    def on_search_files(self):
        if not self.token:
            self.log("❌ 먼저 로그인하세요\n")
            return

        table_name = self.dl_table_name.text().strip()
        table_sn = self.dl_table_sn.value()
        file_type = self.dl_file_type.currentText()

        self.log(f"🔄 파일 검색: {table_name}, {table_sn}, {file_type}\n")

        fetcher = DataFetcher(self.token)
        data = fetcher.get_files(table_name, table_sn, file_type)

        self.file_list_widget.clear()
        self.file_list_data = []

        if data and isinstance(data, list):
            self.file_list_data = data
            for item in data:
                file_name = item.get("orgnl_file_nm", "알 수 없음")
                file_sn = item.get("file_sn", "")
                list_item = QListWidgetItem(f"{file_name} (SN: {file_sn})")
                self.file_list_widget.addItem(list_item)
            self.log(f"✅ {len(data)}개 파일 발견\n")
        else:
            self.log("❌ 파일 없음\n")

        self.log("=" * 50 + "\n")

    def on_download_file(self):
        if not self.token:
            self.log("❌ 먼저 로그인하세요\n")
            return

        selected = self.file_list_widget.currentRow()
        if selected < 0 or selected >= len(self.file_list_data):
            self.log("❌ 다운로드할 파일을 선택하세요\n")
            return

        file_info = self.file_list_data[selected]
        file_sn = file_info.get("file_sn")
        file_name = file_info.get("orgnl_file_nm", "downloaded_file")

        self.log(f"🔄 다운로드 시작: {file_name}\n")

        fetcher = DataFetcher(self.token)
        data = fetcher._download(file_sn)

        if data:
            save_path, _ = QFileDialog.getSaveFileName(self, "파일 저장", file_name)
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(data)
                self.log(f"✅ 다운로드 완료: {save_path} ({len(data)} bytes)\n")
            else:
                self.log("❌ 저장 취소됨\n")
        else:
            self.log("❌ 다운로드 실패\n")

        self.log("=" * 50 + "\n")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
