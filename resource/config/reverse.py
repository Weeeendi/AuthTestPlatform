import configparser
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
import sys


class IniFileDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Ini File Dialog')
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()

        self.ini_parser = configparser.ConfigParser()
        self.ini_parser.read('config.ini')

        for section in self.ini_parser.sections():
            section_layout = QVBoxLayout()
            label = QLabel(section)
            section_layout.addWidget(label)

            for key, value in self.ini_parser.items(section):
                label = QLabel(f'{key}: {value}')
                section_layout.addWidget(label)

            layout.addLayout(section_layout)

        button = QPushButton('Load Ini File')
        button.clicked.connect(self.load_ini_file)
        layout.addWidget(button)

        self.setLayout(layout)

    def load_ini_file(self):
        file_path, _ = QFileDialog.getOpenFileName(None, 'Load Ini File', '.', 'INI files (*.ini)')
        if file_path:
            self.ini_parser = configparser.ConfigParser()
            self.ini_parser.read(file_path)
            for section in self.ini_parser.sections():
                section_layout = QVBoxLayout()
                label = QLabel(section)
                section_layout.addWidget(label)

                for key, value in self.ini_parser.items(section):
                    label = QLabel(f'{key}: {value}')
                    section_layout.addWidget(label)

                self.layout.removeItem(self.layout.itemAt(0))  # remove previous section layout
                self.layout.addLayout(section_layout)  # add new section layout at the beginning of the window


if __name__ == '__main__':
    app = QApplication(sys.argv)

    w = IniFileDialog()
    # setTheme(Theme.DARK)

    w.show()
    app.exec()
