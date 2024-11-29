import sys
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QWidget, QHBoxLayout,
    QVBoxLayout, QFileDialog, QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QFile
from PySide6.QtGui import QAction, QIcon
from ui.login_widget import LoginWidget
from common.async_helper import AsyncHelper
from db.di_lab import Lab
from model.item_model import ItemModel
from model.sku_model import SkuModel
from model.tr_model import TrModel
from ui.item_widget import ItemWidget
from ui.sku_widget import SkuWidget
from ui.tr_widget import TrWidget
from common.d_logger import Logs
from constants import ConfigReader, ADMIN_GROUP
from model.emr_tr_reader import EmrTransactionReader
from ui.emr_import_widget import ImportWidget


logger = Logs().get_logger("main")


class InventoryWindow(QMainWindow):
    start_signal = Signal(str)
    done_signal = Signal(str)
    edit_lock_signal = Signal(str)
    edit_unlock_signal = Signal(str)
    update_all_signal = Signal()
    import_trs_signal = Signal(pd.DataFrame)

    def __init__(self):
        super().__init__()
        is_test: str = ConfigReader().get_options("Testmode")

        self.login_widget = LoginWidget(self)
        self.login_widget.start_main.connect(self.start_app)
        self.update_all_signal.connect(self.update_all)
        self.import_trs_signal.connect(self.import_transactions)

        if is_test.lower() == "true":
            self.start_app("test")
        elif is_test.lower() == "admin":
            self.start_app("admin")
        else:
            self.login()

        self.import_widget = None

    def login(self):
        self.login_widget.show()

    @Slot(str)
    def start_app(self, user_name: str):
        self.setup_models(user_name)
        self.async_helper = AsyncHelper(self, self.do_db_work)
        self.initUi(user_name)

    def setup_models(self, user_name):
        self.item_model = ItemModel(user_name)
        self.sku_model = SkuModel(user_name, self.item_model)
        self.tr_model = TrModel(user_name, self.sku_model)

    def initUi(self, user_name):
        self.setWindowTitle("다나을 재고관리")

        self.setup_menu()
        if user_name in ADMIN_GROUP:
            self.admin_menu.menuAction().setVisible(True)
        else:
            self.admin_menu.menuAction().setVisible(False)

        self.setup_child_widgets()

        # self.setup_dock_widgets()
        self.setup_central_widget()
        self.show()

    def setup_menu(self):
        self.statusBar()
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)

        # File menu
        exit_action = QAction(QIcon('../assets/exit.png'), 'Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(QApplication.instance().quit)

        import_tr_action = QAction(QIcon('../assets/import.png'), 'Import transactions', self)
        import_tr_action.setShortcut('Ctrl+O')
        import_tr_action.setStatusTip('Import transactions')
        import_tr_action.triggered.connect(self.show_file_dialog)

        change_user_action = QAction(QIcon('../assets/user.png'), 'Change user', self)
        change_user_action.triggered.connect(self.change_user)

        file_menu = menubar.addMenu('&File')
        file_menu.addAction(exit_action)
        file_menu.addAction(import_tr_action)
        file_menu.addAction(change_user_action)

        # View menu
        self.inactive_item_action = QAction('Show inactive items', self)
        self.inactive_item_action.setStatusTip('Show inactive items')
        self.inactive_item_action.triggered.connect(self.view_inactive_items)

        view_menu = menubar.addMenu('&View')
        view_menu.addAction(self.inactive_item_action)

        # Admin menu
        reset_pw_action = QAction('Reset password', self)
        reset_pw_action.triggered.connect(self.reset_password)

        self.admin_menu = menubar.addMenu('Admin')
        self.admin_menu.addAction(reset_pw_action)
        self.admin_menu.menuAction().setVisible(False)


    def setup_child_widgets(self):
        self.item_widget = ItemWidget(self)
        self.item_widget.set_source_model(self.item_model)

        self.sku_widget = SkuWidget(self)
        self.sku_widget.set_source_model(self.sku_model)

        self.tr_widget = TrWidget(self)
        self.tr_widget.set_source_model(self.tr_model)

        self.setMinimumSize(1200, 800)
        self.setMaximumSize(1600, 1000)
        self.item_widget.setMinimumWidth(400)
        self.item_widget.setMaximumWidth(500)
        self.sku_widget.setMinimumWidth(800)
        self.sku_widget.setMaximumWidth(1100)
        self.tr_widget.setMinimumWidth(1200)
        self.tr_widget.setMaximumWidth(1600)

    def setup_central_widget(self):
        central_widget = QWidget(self)

        hbox1 = QHBoxLayout()
        hbox1.addWidget(self.item_widget)
        hbox1.addWidget(self.sku_widget)
        hbox2 = QHBoxLayout()
        hbox2.addWidget(self.tr_widget)
        vbox = QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        central_widget.setLayout(vbox)
        self.setCentralWidget(central_widget)

    def setup_dock_widgets(self):
        item_dock_widget = QDockWidget('품목', self)
        item_dock_widget.setAllowedAreas(Qt.TopDockWidgetArea |
                                         Qt.LeftDockWidgetArea)
        item_dock_widget.setWidget(self.item_widget)
        self.addDockWidget(Qt.TopDockWidgetArea, item_dock_widget)
        sku_dock_widget = QDockWidget('세부품목', self)
        sku_dock_widget.setAllowedAreas(Qt.TopDockWidgetArea |
                                        Qt.RightDockWidgetArea)
        sku_dock_widget.setWidget(self.sku_widget)
        self.addDockWidget(Qt.TopDockWidgetArea, sku_dock_widget)
        tr_dock_widget = QDockWidget('거래내역', self)
        tr_dock_widget.setAllowedAreas(Qt.BottomDockWidgetArea |
                                       Qt.LeftDockWidgetArea)
        tr_dock_widget.setWidget(self.tr_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, tr_dock_widget)

    @Slot(str)
    def async_start(self, action: str):
        # send signal to AsyncHelper to schedule the guest (asyncio) event loop
        # inside the host(Qt) event loop
        # AsyncHelper will eventually call self.save_to_db(action, action)
        self.start_signal.emit(action)

    async def do_db_work(self, action: str):
        """
        This is the function registered to async_helper as a async coroutine
        :param action:
        :param df:
        :return:
        """
        logger.debug(f"{action}")
        result_str = None
        if action == "item_save":
            logger.debug("Saving items ...")
            result_str = await self.item_widget.save_to_db()
            logger.debug("Updating items ...")
            await self.item_model.update()
            await self.sku_model.update()
            self.tr_model.selected_upper_id = None
            await self.tr_model.update()
        elif action == "sku_save":
            logger.debug("Saving skus ...")
            result_str = await self.sku_widget.save_to_db()
            await self.sku_model.update()
            self.tr_model.selected_upper_id = None
            await self.tr_model.update()
        elif action == "tr_save":
            logger.debug("Saving transactions ...")
            await self.sku_widget.save_to_db()
            result_str = await self.tr_widget.save_to_db()
            await self.sku_model.update()
            await self.tr_model.update()
        elif action == "item_update":
            await self.item_model.update()
        elif action == "sku_update":
            await self.sku_model.update()
        elif action == "tr_update":
            await self.tr_model.update()
        elif action == "all_update":
            await self.item_model.update()
            await self.sku_model.update()
            self.tr_model.selected_upper_id = None
            await self.tr_model.update()

        self.done_signal.emit(action)

        if result_str is not None:
            QMessageBox.information(self,
                                    '저장결과',
                                    result_str,
                                    QMessageBox.Close)

    def item_selected(self, item_id: int):
        """
        A double-click event in the item view triggers this method,
        and this method consequently calls the sku view to display
        the item selected
        """
        self.sku_widget.filter_for_selected_upper_id(item_id)

    def sku_selected(self, sku_id: int):
        """
        A double-click event in the sku view triggers this method,
        and this method consequently calls transaction view to display
        the sku selected
        """
        self.tr_widget.filter_for_selected_upper_id(sku_id)

    def show_file_dialog(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', '../')
        if fname[0]:
            self.read_emrfile(fname[0])

    def read_emrfile(self, file_name):
        reader = EmrTransactionReader(file_name, self)
        if reader is None:
            logger.debug("Invalid file")
            return

        emr_df = reader.read_df_from()

        if self.import_widget is None:
            self.import_widget = ImportWidget(emr_df, self)
        else:
            self.import_widget.load(emr_df)

        self.import_widget.show()

    @Slot(pd.DataFrame)
    def import_transactions(self, emr_df):
        if emr_df is None or emr_df.empty:
            logger.debug("emr_df is empty")
        else:
            logger.debug(f"\n{emr_df}")
            result_s = self.tr_model.append_new_rows_from_emr(emr_df)
            if not result_s.empty:
                QMessageBox.information(self,
                                        'Import Result',
                                        result_s.to_string(index=False),
                                        QMessageBox.Close)


    def view_inactive_items(self):
        if Lab().show_inactive_items:
            Lab().show_inactive_items = False
            self.inactive_item_action.setText('Show inactive items')
        else:
            Lab().show_inactive_items = True
            self.inactive_item_action.setText('Hide inactive items')

        self.update_all()

    @Slot()
    def update_all(self):
        self.async_start("all_update")

    def reset_password(self):
        u_name, ok = QInputDialog.getText(self, "Reset Password", "Enter user name:")
        if ok:
            hashed_pw = self.login_widget.encrypt_password("a")
            self.login_widget.insert_user_info(u_name, hashed_pw)

    def change_user(self):
        self.close()
        self.login_widget.start_main.disconnect()
        self.login_widget.start_main.connect(self.initUi)
        self.login_widget.show()


def main():
    app = QApplication(sys.argv)

    # style_file = QFile("qss/aqua.qss")
    # style_file = QFile("qss/dark_orange.qss")
    # style_file = QFile("qss/light_blue.qss")
    style_file = QFile("qss/di_custom.qss")
    style_file.open(QFile.ReadOnly)
    app.setStyleSheet(style_file.readAll().toStdString())

    InventoryWindow()
    app.exec()


try:
    main()
except Exception as e:
    logger.error("Unexpected exception! %s", e)
