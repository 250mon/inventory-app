import asyncio
import asyncpg
from asyncpg import UndefinedTableError
from asyncpg import Record
from types import TracebackType
from typing import Optional, Type, List, Tuple
from common.d_logger import Logs
from constants import ConfigReader


logger = Logs().get_logger("db")


async def connect_pg():
    config = ConfigReader()
    try:
        conn = await asyncpg.connect(host=config.get_options("Host"),
                                     port=config.get_options("Port"),
                                     user=config.get_options("User"),
                                     database=config.get_options("Database"),
                                     password=config.get_options("Password"))
        return conn
    except Exception as e:
        logger.debug('Error while connecting to DB')
        logger.debug(e)
        raise e



class ConnectPg:
    def __init__(self):
        self.config = ConfigReader()
        self._conn = None

    async def __aenter__(self):
        logger.debug("Trying to connect to db ...")
        logger.debug("Entering context manager, waiting for connection")
        try:
            self._conn = await asyncpg.connect(host=self.config.get_options("Host"),
                                               port=self.config.get_options("Port"),
                                               user=self.config.get_options("User"),
                                               database=self.config.get_options("Database"),
                                               password=self.config.get_options("Password"))
            logger.debug("Successfully connected!!!")
            return self._conn
        except Exception as e:
            logger.debug('Error while connecting to DB')
            logger.debug(e)
            return None

    async def __aexit__(self,
                        exc_type: Optional[Type[BaseException]],
                        exc_val: Optional[BaseException],
                        exc_tb: Optional[TracebackType]):
        logger.debug("Exiting context manager")
        if self._conn:
            logger.debug("Closed connection")
            await self._conn.close()


class DbUtil:

    async def create_tables(self, statements: List[str]):
        """
        Create tables
        sync_execute can be used instead.
        :param statements: sql statments
        :return:
        """
        results = []
        async with ConnectPg() as conn:
            if conn is None:
                logger.debug("Error while connecting to DB during creating tables")
                return

            logger.info("Creating the tables")
            for statement in statements:
                try:
                    logger.info(f"{statement}")
                    status = await conn.execute(statement)
                    results.append(status)
                    logger.info(status)
                except Exception as e:
                    logger.info(f'create_tables: Error while creating table: {statement}')
                    logger.info(e)
            logger.info("Finished creating the tables")
        return results

    async def drop_tables(self, table_names: List[str]):
        """
        Remove the tables
        :param table_names:
        :return:  the list of results of dropping the tables or
                  None if connection fails
        """
        results = []
        async with ConnectPg() as conn:
            if conn is None:
                logger.debug("Error while connecting to DB during removing tables")
                return None

            logger.info("Removing the tables")
            for table in table_names:
                try:
                    sql_stmt = f'DROP TABLE {table} CASCADE;'
                    result = await conn.execute(sql_stmt)
                    results.append(result)
                except UndefinedTableError as ute:
                    logger.info('drop_table: Trying to drop an undefined table', ute)
                except Exception as e:
                    logger.info('drop_table: Error while dropping tables')
                    logger.info(e)
            logger.info("Finished removing the tables")
        return results

    async def select_query(self, query: str, args: List = None):
        """
        Select query
        :param query
        :return: all results if successful, otherwise None
        """
        async with ConnectPg() as conn:
            if conn is None:
                logger.debug("Error while connecting to DB during querying tables")
                return None

            try:
                query = await conn.prepare(query)
                if args:
                    results: List[Record] = await query.fetch(*args)
                else:
                    results: List[Record] = await query.fetch()
                return results
            except Exception as e:
                logger.debug(f'select_query: Error while executing {query}')
                logger.debug(e)
                return None


    async def executemany(self, statement: str, args: List[Tuple]):
        """
        Execute a statement through connection.executemany()
        :param statement: statement to execute
        :param args: list of arguments which are supplied to the statement one by one
        :return:
            if successful, None
            otherwise, exception or string
        """
        async with ConnectPg() as conn:
            if conn is None:
                logger.debug("Error while connecting to DB during sync_executing")
                return "Connection failed"

            logger.debug("Synchronous executing")
            try:
                results = await conn.executemany(statement, args)
                logger.debug(f"results::\n{results}")
                return results
            except Exception as e:
                logger.debug('executemany: Error during synchronous executing')
                logger.debug(e)
                return e


    async def pool_execute(self, statement: str, args: List[Tuple]):
        """
        Execute a statement through ascynpg.pool
        :param statement: statement to execute
        :param args: list of argements which are supplied to the statement one by one
        :return:
            if successful, list of results of queries
            otherwise, exception
        """
        async def execute(stmt, arg, pool):
            async with pool.acquire() as conn:
                logger.debug(stmt)
                logger.debug(arg)
                return await conn.execute(stmt, *arg)

        logger.debug("Asynchronous executing")
        config = ConfigReader()
        async with asyncpg.create_pool(host=config.get_options("Host"),
                                       port=config.get_options("Port"),
                                       user=config.get_options("User"),
                                       database=config.get_options("Database"),
                                       password=config.get_options("Password")) as pool:
            queries = [execute(statement, arg, pool) for arg in args]
            results = await asyncio.gather(*queries, return_exceptions=True)
            logger.debug(f":\n{results}")
            return results

    async def delete(self, table, col_name, args: List[Tuple]):
        """
        Delete rows where col value is in the args list from table
        :param table: table name
        :param col_name: column name to check
        :param args: argments to search for
        :return:
            When using executemany,
                if successful, None
                otherwise, exception or string
            When using pool_execute,
                if successful, list of results of queries
                otherwise, exception
        """
        if not isinstance(args, List):
            logger.error(f"args' type{type(args)} must be List[Tuple]")
            return None
        if not isinstance(args[0], Tuple):
            logger.error(f"args element's type{type(args[0])} must be Tuple")
            return None

        stmt = f"DELETE FROM {table} WHERE {col_name} = $1"

        logger.debug(f"Delete rows ...")
        logger.debug(args)

        # results = await self.pool_execute(stmt, args)
        results = await self.executemany(stmt, args)
        logger.debug(f":\n{results}")
        return results
