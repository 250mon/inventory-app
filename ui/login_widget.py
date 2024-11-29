import sys
from time import sleep
import bcrypt
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QLineEdit,
    QMessageBox, QFormLayout, QVBoxLayout, QApplication
)
from PySide6.QtCore import Qt, QByteArray, Signal
from PySide6.QtGui import QFont
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from db.db_utils import ConfigReader
from common.d_logger import Logs


logger = Logs().get_logger("main")


class LoginWidget(QWidget):
    start_main = Signal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.initializeUI()

    def initializeUI(self):
        """Initialize the Login GUI window."""
        self.createConnection()
        self.setFixedSize(300, 300)
        self.setWindowTitle("로그인")
        self.setupWindow()

    def createConnection(self):
        """Set up the connection to the database.
        Check for the tables needed."""
        config = ConfigReader()
        database = QSqlDatabase.addDatabase("QPSQL")
        database.setHostName(config.get_options("Host"))
        database.setPort(int(config.get_options("Port")))
        database.setUserName(config.get_options("User"))
        database.setPassword(config.get_options("Password"))
        database.setDatabaseName(config.get_options("Database"))
        if not database.open():
            logger.error("Unable to Connect.")
            logger.error(database.lastError())
            sys.exit(1)  # Error code 1 - signifies error
        else:
            logger.debug("Connected")

        # Check if the tables we need exist in the database
        # tables_needed = {"users"}
        # tables_not_found = tables_needed - set(database.tables())
        # if tables_not_found:
        tables = database.tables()
        if "users" not in tables:
            QMessageBox.critical(None,
                                 "Error",
                                 f"""<p>The following tables are missing
                                  from the database: {tables}</p>""")
            sys.exit(1)  # Error code 1 - signifies error

    def setupWindow(self):
        """Set up the widgets for the login GUI."""
        header_label = QLabel("다나을 재고 관리")
        header_label.setFont(QFont('Arial', 20))
        header_label.setAlignment(Qt.AlignCenter)

        self.user_entry = QLineEdit()
        self.user_entry.setMinimumWidth(150)

        self.password_entry = QLineEdit()
        self.password_entry.setMinimumWidth(150)
        self.password_entry.setEchoMode(QLineEdit.Password)

        # Arrange the QLineEdit widgets into a QFormLayout
        login_form = QFormLayout()
        login_form.setLabelAlignment(Qt.AlignLeft)
        login_form.addRow("Login Id:", self.user_entry)
        login_form.addRow("Password:", self.password_entry)

        connect_button = QPushButton("Connect")
        connect_button.clicked.connect(self.process_login)
        # respond to returnPressed
        connect_button.setAutoDefault(True)

        change_password_button = QPushButton("Change password")
        change_password_button.clicked.connect(lambda: self.process_login(change_pw=True))
        change_password_button.setAutoDefault(True)

        new_user_button = QPushButton("Sign up")
        new_user_button.clicked.connect(lambda: self.register_password_dialog(user_name=None))
        new_user_button.setAutoDefault(True)

        main_v_box = QVBoxLayout()
        main_v_box.setAlignment(Qt.AlignTop)
        main_v_box.addWidget(header_label)
        main_v_box.addSpacing(20)
        main_v_box.addLayout(login_form)
        main_v_box.addSpacing(20)
        main_v_box.addWidget(connect_button)
        main_v_box.addWidget(change_password_button)
        main_v_box.addSpacing(10)
        main_v_box.addWidget(connect_button)
        main_v_box.addWidget(new_user_button)

        self.setLayout(main_v_box)

    def query_user_password(self, user_name):
        query = QSqlQuery()
        query.prepare("SELECT user_password FROM users WHERE user_name = ?")
        query.addBindValue(user_name)
        query.exec()

        result = None
        if query.next():
            result = query.value(0)
            logger.debug("Got a password!")
        else:
            logger.debug("No password found")

        return result

    def insert_user_info(self, user_name, hashed_user_pw):
        query = QSqlQuery()
        pw = QByteArray(hashed_user_pw)
        logger.debug(f"{user_name}, password:{pw}")
        query.prepare("""INSERT INTO users (user_name, user_password) VALUES ($1, $2)
                            ON CONFLICT (user_name)
                            DO
                                UPDATE SET user_name = $1, user_password = $2""")
        query.addBindValue(user_name)
        # postgresql only accepts hexadecimal format
        query.addBindValue(pw)

        if query.exec():
            logger.debug("User info inserted!")
        else:
            QMessageBox.warning(self,
                                "Warning",
                                "User name or password is improper!!",
                                QMessageBox.Close)
            logger.debug("User info not inserted!")
            logger.debug(f"{query.lastError()}")

    def encrypt_password(self, password):
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password

    def verify_password(self, input_password, stored_password):
        # Hash the input password with the same salt used to hash the stored password
        hashed_input_password = bcrypt.hashpw(input_password.encode('utf-8'), stored_password)
        # Compare the hashed input password with the stored password
        return hashed_input_password == stored_password

    def verify_user(self, password, user_name):
        # The following code converts QByteArray to PyBtye(bytes) format
        # stored_pwd: type is QByteArray hex format
        stored_pw: QByteArray = self.query_user_password(user_name)
        if stored_pw is None:
            return False

        # convert QByteArray to bytes
        stored_pw_bytes: bytes = stored_pw.data()
        password_verified = self.verify_password(password, stored_pw_bytes)
        return password_verified

    def process_login(self, change_pw=False):
        """
        Check the user's information. Close the login window if a match
        is found, and open the inventory manager window.

        :return:
        """
        # Collect information that the user entered
        user_name = self.user_entry.text()
        password = self.password_entry.text()

        password_verified = self.verify_user(password, user_name)
        if password_verified:
            self.close()
            if change_pw:
                self.register_password_dialog(user_name)
            else:
                # Open the SQL management application
                sleep(0.5)  # Pause slightly before showing the parent window
                self.start_main.emit(user_name)
                logger.debug("Passed!!!")
        else:
            QMessageBox.warning(self,
                                "Information Incorrect",
                                "The user name or password is incorrect.",
                                QMessageBox.Close)

    def register_password_dialog(self, user_name=None):
        """Set up the dialog box for the user to create a new user account."""
        self.hide()  # Hide the login window
        self.user_input_dialog = QDialog(self)
        # create a new user account
        if user_name is None:
            self.user_input_dialog.setWindowTitle("Create New User")
            header_label = QLabel("Create New User Account")
            self.user_name = QLineEdit()
        # change password
        else:
            self.user_input_dialog.setWindowTitle("Change Password")
            header_label = QLabel("Change Password")
            self.user_name = QLabel(user_name)

        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)

        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)

        # Arrange QLineEdit widgets in a QFormLayout
        dialog_form = QFormLayout()
        if user_name is None:
            dialog_form.addRow("User Name:", self.user_name)
        dialog_form.addRow("New Password", self.new_password)
        dialog_form.addRow("Confirm Password", self.confirm_password)

        # Create sign up button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept_user_info)

        dialog_v_box = QVBoxLayout()
        dialog_v_box.setAlignment(Qt.AlignTop)
        dialog_v_box.addWidget(header_label)
        dialog_v_box.addSpacing(10)
        dialog_v_box.addLayout(dialog_form, 1)
        dialog_v_box.addWidget(ok_button)

        self.user_input_dialog.setLayout(dialog_v_box)
        self.user_input_dialog.show()

    def accept_user_info(self):
        """Verify that the user's passwords match. If so, save them user's
        info to DB and display the login window."""
        user_name_text = self.user_name.text()
        pw_text = self.new_password.text()
        confirm_text = self.confirm_password.text()
        if pw_text != confirm_text:
            QMessageBox.warning(self,
                                "Error Message",
                                "The passwords you entered do not match. Please try again.",
                                QMessageBox.Close)
        else:
            # If the passwords match, encrypt and save it to the db
            hashed_pw = self.encrypt_password(pw_text)
            self.insert_user_info(user_name_text, hashed_pw)
        self.user_input_dialog.close()
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    login_window = LoginWidget()
    login_window.show()
    sys.exit(app.exec())