import sys
import csv
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QMessageBox, QVBoxLayout,
    QLineEdit, QPushButton, QFormLayout, QTableWidget,
    QTableWidgetItem, QScrollArea, QDockWidget, QTextEdit, QFileDialog, QStatusBar
)
from PyQt5.QtCore import Qt
from styles import qss  


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Buku - Raizul Furkon (F1D022024)")
        self.setGeometry(100, 100, 800, 650)

        self.clipboard = QApplication.clipboard()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_container = QWidget()
        form_layout = QFormLayout(form_container)

        self.judul_input = QLineEdit()
        self.pengarang_input = QLineEdit()
        self.tahun_input = QLineEdit()

        form_layout.addRow("Judul", self.judul_input)
        form_layout.addRow("Pengarang", self.pengarang_input)
        form_layout.addRow("Tahun", self.tahun_input)

        self.paste_btn = QPushButton("Paste from Clipboard")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        form_layout.addRow(self.paste_btn)

        scroll.setWidget(form_container)
        main_layout.addWidget(scroll)

        self.save_btn = QPushButton("Simpan")
        self.save_btn.clicked.connect(self.simpan_data)
        self.export_btn = QPushButton("Ekspor ke CSV")
        self.export_btn.clicked.connect(self.ekspor_csv)
        main_layout.addWidget(self.save_btn)
        main_layout.addWidget(self.export_btn)

        self.cari_input = QLineEdit()
        self.cari_input.setPlaceholderText("Cari Judul...")
        self.cari_input.textChanged.connect(self.cari_judul)
        main_layout.addWidget(self.cari_input)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Judul", "Pengarang", "Tahun"])
        self.table.itemChanged.connect(self.perbarui_data_di_database)
        main_layout.addWidget(self.table)

        self.delete_btn = QPushButton("Hapus Data")
        self.delete_btn.clicked.connect(self.hapus_data)
        main_layout.addWidget(self.delete_btn)

        central_widget.setLayout(main_layout)

        statusbar = QStatusBar()
        statusbar.showMessage("Raizul Furkon | F1D022024")
        self.setStatusBar(statusbar)

        self.help_dock = QDockWidget("Petunjuk Penggunaan", self)
        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setText(
            "📘 Panduan:\n- Isi data buku di atas\n- Klik Simpan\n- Gunakan tombol 'Paste' untuk menempel dari clipboard\n"
            "- Pencarian otomatis berdasarkan judul\n- Klik dua kali sel untuk edit langsung\n"
        )
        self.help_dock.setWidget(self.help_text)
        self.addDockWidget(Qt.RightDockWidgetArea, self.help_dock)

        self.conn = sqlite3.connect("buku.db")
        self.db_cursor = self.conn.cursor()
        self.db_cursor.execute('''
            CREATE TABLE IF NOT EXISTS buku (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                judul TEXT, pengarang TEXT, tahun TEXT
            )
        ''')
        self.conn.commit()
        self.editing_id = None
        self.is_updating_table = False
        self.load_data()
        self.setStyleSheet(qss)  

    def paste_from_clipboard(self):
        text = QApplication.clipboard().text()
        self.judul_input.setText(text)

    def simpan_data(self):
        judul = self.judul_input.text().strip()
        pengarang = self.pengarang_input.text().strip()
        tahun = self.tahun_input.text().strip()

        if not (judul and pengarang and tahun):
            QMessageBox.warning(self, "Input Error", "Semua field harus diisi!")
            return

        if self.editing_id:
            self.db_cursor.execute(
                "UPDATE buku SET judul=?, pengarang=?, tahun=? WHERE id=?",
                (judul, pengarang, tahun, self.editing_id)
            )
            self.editing_id = None
        else:
            self.db_cursor.execute(
                "INSERT INTO buku (judul, pengarang, tahun) VALUES (?, ?, ?)",
                (judul, pengarang, tahun)
            )
        self.conn.commit()
        self.judul_input.clear()
        self.pengarang_input.clear()
        self.tahun_input.clear()
        self.load_data()

    def load_data(self):
        self.is_updating_table = True
        self.table.setRowCount(0)
        self.db_cursor.execute("SELECT * FROM buku")
        rows = self.db_cursor.fetchall()
        for row_data in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, data in enumerate(row_data):
                self.table.setItem(row, col, QTableWidgetItem(str(data)))
        self.is_updating_table = False



    def hapus_data(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Hapus", "Pilih baris terlebih dahulu.")
            return
        id_item = self.table.item(selected, 0)
        if id_item:
            id_value = int(id_item.text())
            confirm = QMessageBox.question(self, "Konfirmasi", "Hapus data ini?", QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                self.db_cursor.execute("DELETE FROM buku WHERE id=?", (id_value,))
                self.conn.commit()
                self.load_data()

    def ekspor_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Simpan File CSV", "", "CSV Files (*.csv)")
        if path:
            with open(path, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Judul", "Pengarang", "Tahun"])
                for row in range(self.table.rowCount()):
                    writer.writerow([
                        self.table.item(row, col).text() if self.table.item(row, col) else ''
                        for col in range(self.table.columnCount())
                    ])
            QMessageBox.information(self, "Sukses", "Data berhasil diekspor ke CSV.")

    def cari_judul(self):
        keyword = self.cari_input.text().lower()
        self.is_updating_table = True
        self.table.setRowCount(0)

        query = "SELECT * FROM buku WHERE LOWER(judul) LIKE ?"
        self.db_cursor.execute(query, ('%' + keyword + '%',))
        results = self.db_cursor.fetchall()  # Ambil semua hasil pencarian

        for row_data in results:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, data in enumerate(row_data):
                self.table.setItem(row, col, QTableWidgetItem(str(data)))

        self.is_updating_table = False


    def perbarui_data_di_database(self, item):
        if self.is_updating_table:
            return

        row = item.row()

        item_id = self.table.item(row, 0)
        item_judul = self.table.item(row, 1)
        item_pengarang = self.table.item(row, 2)
        item_tahun = self.table.item(row, 3)

        if not all([item_id, item_judul, item_pengarang, item_tahun]):
            return  #

        try:
            book_id = int(item_id.text())
            judul = item_judul.text()
            pengarang = item_pengarang.text()
            tahun = item_tahun.text()

            self.db_cursor.execute(
                "UPDATE buku SET judul=?, pengarang=?, tahun=? WHERE id=?",
                (judul, pengarang, tahun, book_id)
            )
            self.conn.commit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error memperbarui: {e}")

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())
