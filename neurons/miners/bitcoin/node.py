import argparse
import itertools
import os
import sys
import bittensor as bt
from datetime import time
from bitcoinrpc.authproxy import AuthServiceProxy

parser = argparse.ArgumentParser()
bt.logging.add_args(parser)

class BitcoinNode:
    def __init__(self, node_rpc_url: str = None):
        """
        Args:
            node_rpc_url:
        """
        if node_rpc_url is None:
            self.node_rpc_url = (
                os.environ.get("NODE_RPC_URL")
                or "http://bitcoinrpc:rpcpassword@127.0.0.1:8332"
            )
        else:
            self.node_rpc_url = node_rpc_url

    def get_current_block_height(self):
        rpc_connection = AuthServiceProxy(self.node_rpc_url)
        return rpc_connection.getblockcount()

    def get_block_by_height(self, block_height):
        rpc_connection = AuthServiceProxy(self.node_rpc_url)
        block_hash = rpc_connection.getblockhash(block_height)
        block_data = rpc_connection.getblock(block_hash, 2)
        return block_data
