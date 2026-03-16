from platform import system
from subprocess import Popen, TimeoutExpired, DEVNULL, run
from os import path, remove
from pathlib import Path
from signal import SIGTERM, SIGKILL
from time import sleep, time
from psutil import Process
from monero.const import NET_MAIN, NET_TEST, NET_STAGE
from re import search
from monero.backends import jsonrpc
from monero.seed import Seed
from monero.address import Address
from typing import Optional, Tuple, Union, Dict
from enum import Enum
from requests.exceptions import ConnectionError
from monero.backends.jsonrpc.exceptions import RPCError
from xmrsigner.helpers.network import Network
from hashlib import sha256


WALLET_DIR='/tmp'
WALLET_DAEMON_PATH = '/usr/bin/monero-wallet-rpc'
PIDFILE_BASE_PATH = '/tmp/monero-wallet-rpc'
WALLET_RPC_PORT_OFFSET = 0


class WALLET_PORT(Enum):
    MAIN = 18082
    TEST = 28082
    STAGE = 38082

    @classmethod
    def forNetwork(cls, net: Union[str, Network]) -> int:
        net = Network.ensure(net)
        if net == Network.MAIN:
            return cls.MAIN.value + WALLET_RPC_PORT_OFFSET
        elif net == Network.TEST:
            return cls.TEST.value + WALLET_RPC_PORT_OFFSET
        elif net == Network.STAGE:
            return cls.STAGE.value + WALLET_RPC_PORT_OFFSET
        else:
            raise ValueError("Invalid network type")

        def __int__(self) -> int:
            return self.value


class MoneroWalletRPCManager:

    instance: Optional['MoneroWalletRPCManager'] = None

    @classmethod
    def get_instance(cls) -> 'MoneroWalletRPCManager':
        if not cls.instance:
            cls.instance = cls()
        return cls.instance

    def __init__(self, daemon_path: Optional[str] = None, pidfile_base_path: Optional[str] = None):
        self.user: Optional[str] = None
        self.password: Optional[str] = None
        self.fingerprint: Option[str] = None
        self.networks = [NET_MAIN, NET_TEST, NET_STAGE]
        self.daemon_path = daemon_path or WALLET_DAEMON_PATH
        self.pidfile_base = pidfile_base_path or PIDFILE_BASE_PATH
        self.timeout: int = 300
        self.processes = {}

    def _get_command(self, network: Union[str, Network]):
        port = WALLET_PORT.forNetwork(network)
        out = [
            self.daemon_path,
            '--offline',
            '--no-dns',
            '--rpc-ssl=disabled',
            '--disable-rpc-ban',
            '--no-initial-sync',
            '--log-level=0',
            f'--rpc-bind-port={port}',
            f'--wallet-dir={WALLET_DIR}',
            f'--rpc-login={self.user}:{self.password}' if self.user and self.password else '--disable-rpc-login',
            f'--log-file=/tmp/monero-wallet-rpc-{network}.log'
        ]
        if network != Network.MAIN:
            out.append(f'--{network}')
        return out

    def start_daemon(self, network: Union[str, Network]):
        network = Network.ensure(network)
        if str(network) not in self.networks:
            raise ValueError(f"Invalid network: {network}")

        if self.is_daemon_running(network):
            return True

        cmd = self._get_command(network)
        print(f'Start Wallet RPC with command: {cmd}')
        print(f'Start Wallet RPC with command: {" ".join(cmd)}')
        process = Popen(cmd)
        self.processes[network] = process

        # Wait a bit to ensure the process started
        timeout: int = int(time()) + self.timeout
        while timeout > int(time()) and not self.is_daemon_running(network):
            sleep(0.1)
        return self.is_daemon_running(network)

    def stop_daemon(self, network: Union[str, Network]) -> bool:
        network = Network.ensure(network)
        if str(network) not in self.networks:
            raise ValueError(f"Invalid network: {network}")
        if not self.is_daemon_running(network):
            return True
        process = self.processes.get(network)
        if process:
            print(f'Terminate wallet rpc for {str(network)}...')
            process.terminate()
            try:
                print(f'Wait wallet rpc for {str(network)} for finishing peacefully...')
                process.wait(timeout=10)
            except TimeoutExpired:
                print(f'Kill wallet rpc for {str(network)}...')
                process.kill()
            if process.poll() is not None and system() != 'Windows':
                sleep(1)
                print(f'Send signal 9 to wallet rpc for {str(network)}...')
                process.send_signal(9)
                sleep(1)
            del self.processes[network]
        return not self.is_daemon_running(network)

    def restart_daemon(self, network: Union[str, Network]):
        network = Network.ensure(network)
        self.stop_daemon(network)
        return self.start_daemon(network)

    def is_daemon_running(self, network: Union[str, Network]):
        network = Network.ensure(network)
        if str(network) not in self.networks:
            raise ValueError(f"Invalid network: {network}")
        process = self.processes.get(network)
        if process:
            return process.poll() is None
        return False

    def get_all_daemon_statuses(self) -> Dict[Network, bool]:
        return {network: self.is_daemon_running(network) for network in Network.list}

    def get_daemon_resource_usage(self, network: Union[str, Network]):
        network = Network.ensure(network)
        if not self.is_daemon_running(network):
            return None

        process = Process(self.processes[network].pid)
        return {
            'cpu_percent': process.cpu_percent(interval=1),
            'memory_info': process.memory_info(),
            'num_threads': process.num_threads(),
            'connections': len(process.connections())
        }

    def cleanup(self):
        for network in self.networks:
            self.stop_daemon(network)

    def get_version_string(self) -> Optional[str]:
        print(f'monero-wallet-rpc: {self.daemon_path}')
        try:
            result = run([self.daemon_path, '--version'], capture_output=True, text=True, timeout=10)
            version_string = result.stdout.strip()
            print(version_string)
            version = search(r'v(\d+.\d+.\d+.\d+)', version_string)
            if version:
                return version.group(1)
        except Exception as e:
            print(f'Error retrieving Monero version: {e}')
        return None

    def get_version(self) -> Optional[Tuple[int, int, int]]:
        version = self.get_version_string()
        if version:
            version = version.split('.')
            return (int(version[0]), int(version[1]), int(version[2]), int(version[3]))
        return None

    def open_wallet(self, wallet_name: str, network: Union[str, Network]) -> bool:
        try:
            rpc = jsonrpc.JSONRPCWallet(host='127.0.0.1', port=WALLET_PORT.forNetwork(network), timeout=300)
            result = rpc.raw_request('open_wallet', {'filename': wallet_name})
            if 'result' in result and 'error' not in result:
                return True
        except ConnectionError as ce:
            print(f'No wallet rpc open to close for network: {network}: {ce}')
        except RPCError:
            pass
        return False

    def wallet_exists(self, wallet_name: str) -> bool:
        print(f'check if wallet {wallet_name} exists on path: {Path(WALLET_DIR, wallet_name)}...')
        return Path(WALLET_DIR, wallet_name).exists() and Path(WALLET_DIR, f'{wallet_name}.key')

    def purge_wallet(self, wallet_name: str) -> bool:
        print(f'purge wallet {wallet_name} on path: {Path(WALLET_DIR, wallet_name)}...', end='', flush=True)
        wallet_path: Path = Path(WALLET_DIR, wallet_name)
        wallet_key_path: Path = Path(WALLET_DIR, f'{wallet_name}.key')
        try:
            if wallet_path.exists():
                remove(wallet_path)
            if wallet_key_path.exists():
                remove(wallet_key_path)
            print('done')
            return True
        except FileNotFoundError:  # should never happen
            pass
            # return False
        except OSError:  # should also not happen that path is not a file
            pass
            # return False
        print('failed')
        raise Exception('Something unexpected happend in MoneroWalletRPCManager.purge_wallet()')  # should never reach here

    def load_wallet_from_seed(self, seed: Seed) -> bool:
        wallet_name: str = seed.fingerprint
        if self.wallet_exists(wallet_name) and self.open_wallet(wallet_name, network):
            return True
        # if wallet could not be opened let's wipe the wallet file and/or wallet key file to avoid issues
        self.purge_wallet(wallet_name)
        try:
            rpc = jsonrpc.JSONRPCWallet(host='127.0.0.1', port=WALLET_PORT.forNetwork(Network.fromString(seed.network)), timeout=300)
            response = rpc.raw_request(
                'restore_deterministic_wallet',
                {
                    'restore_height': seed.height,
                    'filename': wallet_name,
                    'seed': seed.mnemonic_str
                }
            )
            if 'address' in response and 'info' in response and response['address'] == public_address:
                return True
            if 'address' in response and response['address'] != public_address:
                print(f'address mismatch, expected "{public_address}" but got "{response["address"]}')
                raise Exception('Address mismatch')
        except ConnectionError as ce:
            print(f'No wallet rpc open to close for network: {network}: {ce}')
        except RPCError:
            pass
        return False

    def load_wallet(
            self,
            network: Union[str, Network],
            wallet_name: str,
            public_address: Union[str, Address],
            view_key: str,
            spend_key: str,
            restore_height: int = 0,
            password: Optional[str] = None
        ) -> bool:
        network = Network.ensure(network)
        if type(public_address) != str:
            public_address = str(public_address)
        if self.wallet_exists(wallet_name) and self.open_wallet(wallet_name, network):
            return True
        # if wallet could not be opened let's purge the wallet file and/or wallet key file to avoid issues
        self.purge_wallet(wallet_name)
        try:
            rpc = jsonrpc.JSONRPCWallet(host='127.0.0.1', port=WALLET_PORT.forNetwork(network), timeout=300)
            response = rpc.raw_request(
                'generate_from_keys',
                {
                    'filename': wallet_name,
                    'address': public_address,
                    'viewkey': view_key,
                    'spendkey': spend_key,
                    'restore_height': restore_height
                }
            )
            if 'address' in response and 'info' in response and response['address'] == public_address:
                return True
            if 'address' in response and response['address'] != public_address:
                print(f'address mismatch, expected "{public_address}" but got "{response["address"]}')
                raise Exception('Address mismatch')
        except ConnectionError as ce:
            print(f'No wallet rpc open to close for network: {network}: {ce}')
        except RPCError:
            pass
        return False

    def close_wallet(self, network: Union[str, Network]):
        network = Network.ensure(network)
        # wallet = jsonrpc.JSONRPCWallet(f'http://127.0.0.1:{WALLET_PORT.forNetwork(network)}')
        try:
            wallet = jsonrpc.JSONRPCWallet(host='127.0.0.1', port=WALLET_PORT.forNetwork(network))
            wallet.raw_request('close_wallet')
        except ConnectionError as ce:
            print(f'No wallet rpc open to close for network: {network}: {ce}')
        except RPCError:
            pass

    def is_rpc_running(self, network: Union[str, Network]) -> bool:
        network = Network.ensure(network)
        try:
            wallet = jsonrpc.JSONRPCWallet(host='127.0.0.1', port=WALLET_PORT.forNetwork(network))
            response = wallet.raw_request('get_version')
            return True
        except ConnectionError:
            return False
        except Exception:
            pass
        raise Exception('Something unexpected happened in MoneroWalletRPCManager.is_rpc_running()')

    def get_fingerprint(self, network: Union[str, Network]) -> Optional[str]:
        network = Network.ensure(network)
        port = WALLET_PORT.forNetwork(network)
        print(f'wallet-rpc port for network {str(network)} is {port}')
        try:
            wallet = jsonrpc.JSONRPCWallet(host='127.0.0.1', port=WALLET_PORT.forNetwork(network))
            response = wallet.raw_request('get_address', {'account_index': 0})
            print(response)
            if 'address' in response:
                return sha256(response['address'].encode()).hexdigest()[-6:].upper()
            return None
        except ConnectionError:
            return None
        except Exception:
            pass
        raise Exception('Something unexpected happened in MoneroWalletRPCManager.is_rpc_running()')
