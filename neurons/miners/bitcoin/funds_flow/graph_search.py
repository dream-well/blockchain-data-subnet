import os

from neo4j import GraphDatabase


class GraphSearch:
    def __init__(
        self,
        graph_db_url: str = None,
        graph_db_user: str = None,
        graph_db_password: str = None,
    ):
        if graph_db_url is None:
            self.graph_db_url = (
                os.environ.get("GRAPH_DB_URL") or "bolt://localhost:7687"
            )
        else:
            self.graph_db_url = graph_db_url

        if graph_db_user is None:
            self.graph_db_user = os.environ.get("GRAPH_DB_USER") or ""
        else:
            self.graph_db_user = graph_db_user

        if graph_db_password is None:
            self.graph_db_password = os.environ.get("GRAPH_DB_PASSWORD") or ""
        else:
            self.graph_db_password = graph_db_password

        self.driver = GraphDatabase.driver(
            self.graph_db_url,
            auth=(self.graph_db_user, self.graph_db_password),
        )

    def execute_query(self, network, query):
        # TODO: Implement this
        return []

    def get_block_transaction(self, block_height):
        with self.driver.session() as session:
            data_set = session.run(
                """
                MATCH (t:Transaction { block_height: $block_height })-[r:SENT]->(a:Address)
                RETURN t.block_height AS block_height, SUM(r.value_satoshi) AS total_value_satoshi, COUNT(t) AS transaction_count
                """,
                block_height=block_height
            )
            result = data_set.single()
            return {
                "block_height": result["block_height"],
                "total_value_satoshi": result["total_value_satoshi"],
                "transaction_count": result["transaction_count"],
            }

    def get_latest_block_number(self):
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (t:Transaction)
                RETURN MAX(t.block_height) AS latest_block_height
                """
            )
            single_result = result.single()
            if single_result[0] is None:
                return 0
            return single_result[0]
