import asyncio
import random
import os
from faker import Faker
from curl_cffi.requests import AsyncSession
from loguru import logger
from eth_account.messages import encode_defunct
from web3 import AsyncWeb3, Web3

current_directory = os.path.dirname(os.path.abspath(__file__))


def read_wallets_from_files(file_names, current_directory, *directories):
    wallets = []
    for file_path in file_names:
        file_name = os.path.join(current_directory, *directories, file_path)
        with open(file_name, 'r', encoding='utf-8') as file:
            for line in file:
                address, private_key = line.strip().split(',')
                wallets.append({'address': address, 'private_key': private_key})
    return wallets


def write_to_file(filename, data, current_directory, *directories):
    file_path = os.path.join(current_directory, *directories, filename)

    # 创建目录（如果不存在）
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 定义每个字段的长度
    lengths = [42, 10, 10, 10, 10, 10]

    # 按定长格式化数据
    fields = data.split(',')
    formatted_data = ''.join([field.center(length) for field, length in zip(fields, lengths)])

    # 确保新数据总是写在新的一行
    with open(file_path, 'a+', encoding='utf-8') as file:
        file.seek(0, os.SEEK_END)
        if file.tell() > 0:
            file.seek(0, os.SEEK_END)  # 移动到文件末尾
            file.seek(file.tell() - 1, os.SEEK_SET)  # 移动到最后一个字符位置
            last_char = file.read(1)
            if last_char != '\n':
                file.write('\n')
        file.write(formatted_data + '\n')
        print(f"已经写入 {filename}")


class UltiverseUtil:
    def __init__(self, private_key, http_provider='https://204.rpc.thirdweb.com'):
        self.fake = Faker()
        self.private_key = private_key
        headers = {
            "Referer": "https://pilot.ultiverse.io/",
            "Origin": "https://pilot.ultiverse.io",
            "Ul-Auth-Api-Key": "YWktYWdlbnRAZFd4MGFYWmxjbk5s",
            "User-Agent": self.fake.chrome()
        }
        self.http = AsyncSession(timeout=30, headers=headers, impersonate="chrome120", verify=False)
        if PROXYS_LIST and len(PROXYS_LIST) > 0:
            randome_proxy = random.choice(PROXYS_LIST)
            if randome_proxy:
                proxies = {
                    "http": f"http://{randome_proxy}",
                    "https": f"http://{randome_proxy}",
                }
                self.thread_sleep = 0
                self.http = AsyncSession(timeout=30, headers=headers, impersonate="chrome120", proxies=proxies,
                                         verify=False)
        self.wb3 = Web3(Web3.HTTPProvider(http_provider))
        self.account = self.wb3.eth.account.from_key(private_key)
        self.http.headers.update({"Ul-Auth-Address": self.account.address})
        self.address = self.account.address

    async def get_tk(self):
        try:
            if 'Ul-Auth-Token' not in self.http.headers:
                await self.login()

            res = await self.http.post(f'https://rewards.ultiverse.io/api/token?wallet={self.account.address}')
            logger.info(f'[{self.address}] 获取空投返回信息：{res.text}')

            user_info_json = res.json()
            success = user_info_json.get('success', False)
            datas = user_info_json.get('data', {})
            if success:
                total_ = 0
                total_nft = 0
                total_soul = 0
                total_okx = 0
                total_safepal = 0
                for data in datas:
                    type = data.get('type')
                    tokenQuantities = data.get('tokenQuantities')
                    if type == 'nft':
                        total_nft = tokenQuantities
                    elif type == 'soul':
                        total_soul = tokenQuantities
                    elif type == 'okx-activity':
                        total_okx = tokenQuantities
                    elif type == 'safepal-activity':
                        total_safepal = tokenQuantities
                    total_ = total_ + tokenQuantities

                data = f'{self.address},{total_},{total_nft},{total_soul},{total_okx},{total_safepal}'
                write_to_file('drops2.txt', data, current_directory)

                return True
            return False
        except Exception as e:
            logger.error(f'[{self.address}] 获取信息异常：{e}')
            return False

    async def login(self):
        try:
            signature = await self.get_nonce()
            if signature is None:
                return False
            json_data = {
                "address": self.account.address,
                "signature": signature,
                "chainId": 204
            }
            res = await self.http.post('https://account-api.ultiverse.io/api/wallets/signin', json=json_data)
            if 'success' in res.text and res.json()['success']:
                access_token = res.json()['data']['access_token']
                self.http.headers.update({"Ul-Auth-Token": access_token})
                logger.info(f'[{self.address}] 登录成功：{res.text}')
                return True
            logger.error(f'[{self.address}] 登录失败：{res.text}')
            return False
        except Exception as e:
            logger.error(f'[{self.address}] 登录异常：{e}')
            return False

    async def get_nonce(self):
        try:
            json_data = {
                "address": self.account.address,
                "feature": "assets-wallet-login",
                "chainId": 204
            }
            res = await self.http.post('https://account-api.ultiverse.io/api/user/signature', json=json_data)
            if 'success' in res.text and res.json()['success']:
                message = res.json()['data']['message']
                signature = self.account.sign_message(encode_defunct(text=message))
                return signature.signature.hex()
            logger.error(f'[{self.address}] 获取nonce失败：{res.text}')
            return None
        except Exception as e:
            logger.error(f'[{self.address}] 获取nonce异常：{e}')
            return None


async def signTask(file_names):
    data = '钱包地址,总量,nft空投数量,soul空投数量,okx数量,safepal数量'
    write_to_file('drops2.txt', data, current_directory)

    # 从多个文件中读取钱包数据
    wallets = read_wallets_from_files(file_names, current_directory)
    processed_wallets = 0  # 用于计数已处理的钱包数量
    # 逐个取出数据
    for wallet in wallets:
        private_key = wallet['private_key']
        universe = UltiverseUtil(private_key)
        await universe.get_tk()
        processed_wallets += 1
        print(f"已处理 {processed_wallets} 个钱包")


if __name__ == '__main__':
    file_names = [
        'all.txt'
    ]
    PROXYS_LIST = []
    #PROXYS_LIST = ['127.0.0.1:1082']

    asyncio.run(signTask(file_names))
