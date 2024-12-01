import sys
import bcrypt
from PySide6.QtWidgets import (
    QWidget, QDialog, QLabel, QPushButton, QLineEdit,
    QMessageBox, QFormLayout, QVBoxLayout, QApplication
)
from PySide6.QtCore import Qt, QByteArray, Signal
from PySide6.QtGui import QFont
from sqlalchemy import select
from db.models import User
from db.db_utils import DbUtil
import asyncio
import qasync
from common.d_logger import Logs

logger = Logs().get_logger("main")


class LoginWidget(QWidget):
    start_main = Signal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.db_util = DbUtil()
        self.initializeUI()

        # states
        self.user_name = None
        self.password = None
        self.change_pw = False

    def initializeUI(self):
        """Initialize the Login GUI window."""
        self.setFixedSize(300, 300)
        self.setWindowTitle("로그인")
        self.setupWindow()
   
    async def check_connection(self):
        """Set up the connection to the database."""
        try:
            await self.test_connection()
        except Exception as e:
            logger.error("Unable to Connect.")
            QMessageBox.critical(None, "Error", "Unable to connect to database")
            sys.exit(1)

    async def test_connection(self):
        """Test database connection by querying users table"""
        async with self.db_util.session() as session:
            stmt = select(User)
            result = await session.execute(stmt)
            # Just checking if we can execute a query
            result.first()

    async def query_user_password(self, user_name):
        """Query user password using SQLAlchemy"""
        try:
            async with self.db_util.session() as session:
                stmt = select(User.user_password).where(User.user_name == user_name)
                result = await session.execute(stmt)
                row = result.first()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Query password failed: {e}")
            return None

    async def insert_user_info(self, user_name, hashed_user_pw):
        """Insert or update user info using SQLAlchemy"""
        try:
            async with self.db_util.session() as session:
                # Check if user exists
                stmt = select(User).where(User.user_name == user_name)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user:
                    # Update existing user
                    user.user_password = hashed_user_pw
                else:
                    # Create new user
                    user = User(
                        user_name=user_name,
                        user_password=hashed_user_pw
                    )
                    session.add(user)
                
                await session.commit()
                logger.debug("User info inserted!")
                return True
        except Exception as e:
            logger.debug(f"User info not inserted: {e}")
            QMessageBox.warning(
                self,
                "Warning",
                "User name or password is improper!!",
                QMessageBox.Close
            )
            return False

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
        connect_button.clicked.connect(lambda: asyncio.create_task(self.process_login()))
        connect_button.setAutoDefault(True)

        change_password_button = QPushButton("Change password")
        change_password_button.clicked.connect(self.login_with_change_pw)
        change_password_button.setAutoDefault(True)

        new_user_button = QPushButton("Sign up")
        new_user_button.clicked.connect(self.register_password_dialog)
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

    def encrypt_password(self, password):
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password

    def compare_passwords(self, input_password, stored_password):
        # Hash the input password with the same salt used to hash the stored password
        hashed_input_password = bcrypt.hashpw(input_password.encode('utf-8'), stored_password)
        # Compare the hashed input password with the stored password
        return hashed_input_password == stored_password

    async def process_login(self):
        """Check the user's information."""
        self.user_name = self.user_entry.text()
        self.password = self.password_entry.text()

        stored_pw = await self.query_user_password(self.user_name)
        await self.handle_login_result(stored_pw)
    
    def login_with_change_pw(self):
        self.change_pw = True
        asyncio.create_task(self.process_login())

    async def handle_login_result(self, stored_pw):
        if stored_pw is None:
            return False

        # Convert stored password to bytes if needed
        if isinstance(stored_pw, (QByteArray, bytes)):
            stored_pw_bytes = stored_pw.data() if isinstance(stored_pw, QByteArray) else stored_pw
        else:
            stored_pw_bytes = stored_pw

        if self.compare_passwords(self.password, stored_pw_bytes):
            self.close()
            if self.change_pw:
                self.register_password_dialog()
            else:
                await asyncio.sleep(0.5)  # Pause slightly before showing the parent window
                self.start_main.emit(self.user_name)
                logger.debug("Passed!!!")
        else:
            QMessageBox.warning(self,
                              "Information Incorrect",
                              "The user name or password is incorrect.",
                              QMessageBox.Close)

    def register_password_dialog(self):
        """Set up the dialog box for the user to create a new user account."""
        self.hide()  # Hide the login window
        self.user_input_dialog = QDialog(self)
        # create a new user account
        if self.user_name is None:
            self.user_input_dialog.setWindowTitle("Create New User")
            header_label = QLabel("Create New User Account")
            self.user_name_label = QLineEdit()
        # change password
        else:
            self.user_input_dialog.setWindowTitle("Change Password")
            header_label = QLabel("Change Password")
            self.user_name_label = QLabel(self.user_name)

        self.new_password_le = QLineEdit()
        self.new_password_le.setEchoMode(QLineEdit.Password)

        self.confirm_password_le = QLineEdit()
        self.confirm_password_le.setEchoMode(QLineEdit.Password)

        dialog_form = QFormLayout()
        if self.user_name is None:
            dialog_form.addRow("User Name:", self.user_name_label)
        dialog_form.addRow("New Password", self.new_password_le)
        dialog_form.addRow("Confirm Password", self.confirm_password_le)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(lambda: asyncio.create_task(self.accept_user_info()))

        dialog_v_box = QVBoxLayout()
        dialog_v_box.setAlignment(Qt.AlignTop)
        dialog_v_box.addWidget(header_label)
        dialog_v_box.addSpacing(10)
        dialog_v_box.addLayout(dialog_form, 1)
        dialog_v_box.addWidget(ok_button)

        self.user_input_dialog.setLayout(dialog_v_box)
        self.user_input_dialog.show()

    async def accept_user_info(self):
        """Verify and save user info"""
        user_name_text = (
            self.user_name_label.text() 
            if isinstance(self.user_name_label, QLineEdit) 
            else self.user_name_label.text
        )
        pw_text = self.new_password_le.text()
        confirm_text = self.confirm_password_le.text()
        
        if pw_text != confirm_text:
            QMessageBox.warning(
                self,
                "Error Message",
                "The passwords you entered do not match. Please try again.",
                QMessageBox.Close
            )
        else:
            # If the passwords match, encrypt and save it to the db
            hashed_pw = self.encrypt_password(pw_text)
            is_inserted = await self.insert_user_info(user_name_text, hashed_pw)
            if is_inserted:
                self.user_input_dialog.close()
                self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    login_window = LoginWidget()
    login_window.show()
    
    with loop:
        loop.run_forever()