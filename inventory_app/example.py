import sys
import asyncio
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QListWidget
from PySide6.QtCore import Qt
import qasync
from qasync import QEventLoop, asyncSlot
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import select, update, delete
from sqlalchemy import Column, Integer, String

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User CRUD Example")
        self.setGeometry(100, 100, 300, 400)

        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter user name")
        layout.addWidget(self.name_input)

        self.add_button = QPushButton("Add User")
        self.add_button.clicked.connect(self.add_user)
        layout.addWidget(self.add_button)

        self.user_list = QListWidget()
        layout.addWidget(self.user_list)

        self.update_button = QPushButton("Update Selected User")
        self.update_button.clicked.connect(self.update_user)
        layout.addWidget(self.update_button)

        self.delete_button = QPushButton("Delete Selected User")
        self.delete_button.clicked.connect(self.delete_user)
        layout.addWidget(self.delete_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.engine = create_async_engine("sqlite+aiosqlite:///example.db", echo=True)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await self.load_users()

    @asyncSlot()
    async def load_users(self):
        self.user_list.clear()
        async with self.async_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            for user in users:
                self.user_list.addItem(f"{user.id}: {user.name}")

    @asyncSlot()
    async def add_user(self):
        name = self.name_input.text()
        if name:
            async with self.async_session() as session:
                new_user = User(name=name)
                session.add(new_user)
                await session.commit()
            await self.load_users()
            self.name_input.clear()

    @asyncSlot()
    async def update_user(self):
        selected_item = self.user_list.currentItem()
        if selected_item:
            user_id = int(selected_item.text().split(":")[0])
            new_name = self.name_input.text()
            if new_name:
                async with self.async_session() as session:
                    await session.execute(
                        update(User).where(User.id == user_id).values(name=new_name)
                    )
                    await session.commit()
                await self.load_users()
                self.name_input.clear()

    @asyncSlot()
    async def delete_user(self):
        selected_item = self.user_list.currentItem()
        if selected_item:
            user_id = int(selected_item.text().split(":")[0])
            async with self.async_session() as session:
                await session.execute(delete(User).where(User.id == user_id))
                await session.commit()
            await self.load_users()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_until_complete(window.init_db())
        loop.run_forever()