import io
import logging
import os
import pathlib
from contextlib import closing
from ftplib import FTP, error_perm
from typing import BinaryIO, Iterator, List

from dotenv import load_dotenv


class FtpAccessor:
    """
    FTP サーバーへの接続・切断・ファイルアップロードを行うためのアクセサクラス。

    本クラスは .env ファイルから FTP 接続情報（ホスト名、ポート、ユーザー名、
    パスワード、アップロード先ディレクトリ）を読み込み、FTP を使用した
    ファイル操作を提供する。

    主な機能:
        - FTP サーバーへの接続 (`connect`)
        - FTP サーバーからの切断 (`disconnect`)
        - 指定ファイルのアップロード (`upload`)
        - FTP 上のディレクトリ作成 (`make_dirs`)
    """

    def __init__(self):
        """
        クラスの初期化処理を行う。

        .env ファイルを読み込み、以下の環境変数から FTP 接続情報を設定する:
            - FTP_HOST: FTP サーバーのホスト名
            - FTP_PORT: 接続ポート番号
            - FTP_USER: ログインユーザー名
            - FTP_PASS: ログインパスワード
            - FTP_S_TLTP_UPLOAD_PATH: アップロード先のディレクトリパス

        また、ログ設定を初期化し、ログ出力用の logger を生成する。
        """
        load_dotenv()  # .envファイルを読み込む
        # FTP環境変数名
        self.ftp = None
        self.ftp_host = os.environ["FTP_HOST"]
        # self.ftp_host = "127.0.0.01"
        self.ftp_port = int(os.environ["FTP_PORT"])
        self.ftp_user = os.environ["FTP_USER"]
        self.ftp_pass = os.environ["FTP_PASS"]
        # self.ftp_base_path = os.environ["FTP_S_TLTP_UPLOAD_PATH"]
        # ログ作成
        self.logger = logging.getLogger(__name__)

    def connect(self) -> bool:
        """
        FTP サーバーへ接続し、ログインを行う。

        接続後、PASV モードを有効に設定する。
        接続またはログインに失敗した場合は False を返し、ログを出力する。

        Returns:
            bool: 接続が成功した場合 True、失敗した場合 False
        """
        try:
            self.ftp = FTP()
            # 接続・ログイン・PASV設定
            self.ftp.connect(host=self.ftp_host, port=self.ftp_port, timeout=30)
            self.ftp.login(user=self.ftp_user, passwd=self.ftp_pass)
            self.ftp.set_pasv(True)
            self.ftp.encoding = os.environ.get("FTP_ENCODING", "cp932")
        except Exception as ex:  # pragma: no cover
            self.logger.error(
                f"FTP Exception from connect: host={self.ftp_host}  port={self.ftp_port}  user={self.ftp_user}  ex={ex}"
            )
            self.ftp = None
            return False
        return True

    def disconnect(self) -> bool:
        """
        FTP サーバーからの切断処理を行う。

        接続中であれば `quit()` を呼び出して明示的に切断し、
        最後に FTP インスタンスを None にリセットする。

        Returns:
            bool: 切断処理が成功した場合 True、失敗した場合 False
        """
        try:
            if self.ftp:
                self.ftp.quit()
            return True
        except Exception as ex:  # pragma: no cover
            self.logger.error(f"FTP Exception from disconnect: {ex}")
            return False
        finally:
            self.ftp = None

    def upload(self, save_file_path: str, ftp_dst_base_path: str) -> bool:
        """
        指定したローカルファイルを FTP サーバーの所定ディレクトリにアップロードする。

        Args:
            save_file_path (str): ローカル側のアップロード対象ファイルパス
            save_file_name (str): FTP サーバー上に保存するファイル名
            ftp_dst_base_path(str): アップロード先のFTPディレクトリパス

        Returns:
            bool: アップロード成功時 True、失敗時 False

        Raises:
            ログ出力のみで例外は外に送出しない。
        """
        if not self.ftp:  # pragma: no cover
            self.logger.error("ftp not initialized.")
            return False
        # 対象のファイル名とファイルまでのディレクトリ名を取得
        filename = pathlib.Path(save_file_path).name
        try:
            # FTP保存先フォルダ作成+移動
            self.ftp.cwd("/")
            if not self.__makedirs_ftp(ftp_dst_base_path):
                self.logger.error(
                    f"Failed to prepare FTP directory: {ftp_dst_base_path}"
                )
                return False
            # ファイルアップロード処理
            with open(save_file_path, "rb") as f:
                self.ftp.storbinary(f"STOR {filename}", f)
        except Exception as ex:  # pragma: no cover
            self.logger.exception(f"FTP Exception from upload: {ex}")
            return False
        return True

    def upload_bytes(
        self, save_file_name: str, data: BinaryIO, ftp_dst_base_path: str
    ) -> bool:
        """
        バイナリファイルライクオブジェクトを FTP サーバーの所定ディレクトリにアップロードする。

        Args:
            save_file_name (str): FTP サーバー上に保存するファイル名
            data (BinaryIO): アップロード対象のバイナリストリーム
            ftp_dst_base_path(str): アップロード先のFTPディレクトリパス

        Returns:
            bool: アップロード成功時 True、失敗時 False
        """
        if not self.ftp:  # pragma: no cover
            return False
        if not save_file_name:  # pragma: no cover
            self.logger.error("Upload file name is empty.")
            return False
        try:
            # FTP保存先フォルダ作成+移動
            self.ftp.cwd("/")
            self.__makedirs_ftp(ftp_dst_base_path)
            self.__move_directory(ftp_dst_base_path)
            if hasattr(data, "seek"):
                data.seek(0)
            self.ftp.storbinary(f"STOR {save_file_name}", data)
        except Exception as ex:  # pragma: no cover
            self.logger.error(f"FTP Exception from upload_bytes: {ex}")
            return False
        return True

    def file_exist(self, target_file_path: str) -> bool:
        # ftp未接続
        if not self.ftp:
            return False
        # 対象のファイル名とファイルまでのディレクトリ名を取得
        directory, filename = os.path.split(target_file_path)
        # ルートディレクトリへ移動
        self.ftp.cwd("/")
        # 対象のディレクトリへ移動
        self.__move_directory(directory=directory)
        try:
            # ディレクトリ内のファイル一覧を取得
            files = self.ftp.nlst()
        except Exception as ex:
            self.logger.info(
                f"Failed get file. target_file_path:{target_file_path}. file:{filename} exception:{ex}"
            )
            return False
        return filename in files

    def delete_file(self, target_file_path: str) -> bool:
        """
        FTP サーバ上の指定パスのファイルを削除する。

        Args:
            target_file_path (str): 削除したいファイルのフルパス
                                   例: "/upload/data/test.txt"

        Returns:
            bool: 削除成功時 True、失敗時 False
        """
        if not self.ftp:
            self.logger.error("FTP is not connected.")
            return False
        directory, filename = os.path.split(target_file_path)
        try:
            # ルートに移動
            self.ftp.cwd("/")
            # 対象のディレクトリへ移動
            self.__move_directory(directory=directory)
            # ファイル削除
            self.ftp.delete(filename)
            return True

        except Exception as ex:
            self.logger.exception(
                f"FTP Exception from delete_file. target_file_path:{target_file_path}. {ex}"
            )
            return False

    def rename_file(self, source_file_path: str, target_file_path: str) -> bool:
        """
        FTP サーバ上の指定ファイルをリネームまたは移動する。

        Args:
            source_file_path (str): リネーム元ファイルのフルパス
                                   例: "/upload/data/test.txt"
            target_file_path (str): リネーム先ファイルのフルパス
                                   例: "/upload/archive/test.txt"

        Returns:
            bool: リネーム成功時 True、失敗時 False
        """
        if not self.ftp:
            self.logger.error("FTP is not connected.")
            return False
        try:
            self.ftp.rename(source_file_path, target_file_path)
            return True

        except Exception as ex:
            self.logger.exception(
                f"FTP Exception from rename_file. source_file_path:{source_file_path}. target_file_path:{target_file_path}. {ex}"
            )
            return False

    def make_dirs(self, target_dir_path: str) -> bool:
        """
        FTP サーバ上に指定ディレクトリを作成する。

        Args:
            target_dir_path (str): 作成したいディレクトリのフルパス
                                   例: "/upload/archive"

        Returns:
            bool: 作成成功時 True、失敗時 False
        """
        if not self.ftp:
            self.logger.error("FTP is not connected.")
            return False
        try:
            return self.__makedirs_ftp(target_dir_path)

        except Exception as ex:
            self.logger.exception(
                f"FTP Exception from make_dirs. target_dir_path:{target_dir_path}. {ex}"
            )
            return False

    def delete_dir(self, target_dir_path: str) -> bool:
        """
        FTP サーバ上の指定パスのディレクトリを再帰的に削除する。

        Args:
            target_dir_path (str): 削除したいディレクトリのフルパス
                                   例: "/upload/data"

        Returns:
            bool: 削除成功時 True、失敗時 False
        """
        if not self.ftp:
            self.logger.error("FTP is not connected.")
            return False
        try:
            # ディレクトリ内の一覧取得
            items = self.ftp.nlst(target_dir_path)
        except error_perm as ex:
            # ディレクトリが存在しない or アクセス不可
            self.logger.exception(
                f"FTP Exception from delete_dir (cannot access or not found {target_dir_path}): ({ex})"
            )
            return False

        for item in items:
            try:
                self.ftp.delete(item)
            except error_perm:
                # ファイルでなければディレクトリとして再帰処理
                self.delete_dir(item)

        try:
            # 中身削除後にディレクトリ削除
            self.ftp.rmd(target_dir_path)
            return True

        except Exception as ex:
            self.logger.exception(
                f"FTP Exception from delete_dir (cannot delete {target_dir_path}): ({ex})"
            )
            return False

    def __makedirs_ftp(self, create_path: str) -> bool:
        if not self.ftp:
            return False

        self.ftp.cwd("/")  # ユーザールート
        for part in create_path.strip("/").split("/"):
            try:
                self.ftp.mkd(part)
            except error_perm:
                pass  # 既存はOK
            try:
                self.ftp.cwd(part)
            except Exception as ex:
                self.logger.exception(f"Cannot cwd to {part}: {ex}")
                return False
        return True

    def __move_directory(self, directory: str) -> bool:
        if not self.ftp:
            return False
        self.ftp.cwd("/")
        # ディレクトリ移動
        if directory:
            for part in directory.split("/"):
                if not part:
                    continue
                try:
                    self.ftp.cwd(part)
                except Exception as ex:
                    self.logger.exception(
                        f"Not found FTP folder during delete. folder:{part} exception:{ex}"
                    )
                    return False
        return True

    def download_dir(self, remote_dir: str, local_dir: str) -> bool:
        """
        指定した FTP 上のディレクトリをローカルへ再帰的にダウンロードする。

        Args:
            remote_dir (str): FTP上のダウンロード元ディレクトリ
            local_dir (str): ローカルの保存先ディレクトリ
        """
        self.logger.info(f"download dir. remote={remote_dir}, local={local_dir}")
        if not self.ftp:
            return False
        try:
            self.ftp.cwd("/")
            self.__download_ftp_dir(remote_dir, local_dir)
            return True
        except Exception as ex:  # pragma: no cover
            self.logger.error(
                f"FTP Exception from download_dir. remote_dir:{remote_dir}. local_dir:{local_dir}. {ex}"
            )
            return False

    def upload_dir(self, local_dir: str, remote_dir: str) -> bool:
        """
        ローカルディレクトリの内容を FTP 上へ再帰的にアップロードする。

        Args:
            local_dir (str): ローカルのアップロード元ディレクトリ
            remote_dir (str): FTP上のアップロード先ディレクトリ
        """
        if not self.ftp:
            return False
        try:
            self.ftp.cwd("/")
            self.__upload_ftp_dir(local_dir, remote_dir)
            return True
        except Exception as ex:  # pragma: no cover
            self.logger.error(
                f"FTP Exception from upload_dir: local_dir: {local_dir}, remote_dir: {remote_dir}.  {ex}"
            )
            return False

    # def __download_ftp_dir(self, remote_dir: str, local_dir: str) -> bool:
    #     if not self.ftp:
    #         return False
    #     os.makedirs(local_dir, exist_ok=True)
    #     self.logger.info(f"change to {remote_dir}")
    #     self.ftp.cwd(remote_dir)

    #     file_list = []
    #     self.ftp.retrlines("LIST", file_list.append)

    #     for item in file_list:
    #         parts = item.split()
    #         if not parts:
    #             continue
    #         name = parts[-1]
    #         kind = item[0]

    #         if kind == "d":  # ディレクトリ
    #             self.__download_ftp_dir(name, os.path.join(local_dir, name))
    #             self.ftp.cwd("..")
    #         else:
    #             local_file = os.path.join(local_dir, name)
    #             with open(local_file, "wb") as f:
    #                 self.ftp.retrbinary(f"RETR {name}", f.write)
    #     return True

    def __download_ftp_dir(self, remote_dir: str, local_dir: str) -> bool:
        if not self.ftp:
            return False
        os.makedirs(local_dir, exist_ok=True)

        try:
            self.logger.info(f"change to {remote_dir}")
            self.ftp.cwd(remote_dir)
        except Exception as ex:
            self.logger.error(
                f"Cannot cwd to {remote_dir}: local_dir: {local_dir}:  {ex}"
            )
            return False

        try:
            names = self.ftp.nlst()
        except Exception as ex:
            self.logger.error(f"NLST not permitted in {remote_dir}: {ex}")
            return False

        for name in names:
            # nlst がフルパスを返す環境対策
            if name.startswith(remote_dir):
                next_remote = name
                basename = os.path.basename(name)
            else:
                next_remote = f"{remote_dir}/{name}".replace("//", "/")
                basename = name

            local_path = os.path.join(local_dir, basename)

            try:
                # ディレクトリか試す
                self.ftp.cwd(next_remote)

                # 再帰
                self.__download_ftp_dir(next_remote, local_path)

                # 元に戻る
                self.ftp.cwd(remote_dir)

            except error_perm:
                # ファイル
                try:
                    with open(local_path, "wb") as f:
                        self.ftp.retrbinary(f"RETR {next_remote}", f.write)
                except Exception as ex:
                    self.logger.error(f"RETR failed: {next_remote} ({ex})")
        return True

    def __upload_ftp_dir(self, local_dir: str, remote_dir: str) -> bool:
        if not self.ftp:
            return False
        try:
            self.ftp.mkd(remote_dir)
        except error_perm as e:
            self.logger.info(f"Directory may already exist: {remote_dir} ({e})")

        self.ftp.cwd(remote_dir)

        for item in os.listdir(local_dir):
            local_path = os.path.join(local_dir, item)
            if os.path.isdir(local_path):
                self.__upload_ftp_dir(local_path, item)
                self.ftp.cwd("..")
            else:
                with open(local_path, "rb") as f:
                    self.ftp.storbinary(f"STOR {item}", f)
        return True

    def list_files(self, remote_dir: str, extension: str | None) -> List[str]:
        """
        指定した FTP 上のディレクトリに存在するファイルのパスを取得する。

        Args:
            remote_dir (str): FTP上の対象ディレクトリ
            extension (str | None): 取得対象拡張子(ex:".json")、指定しない場合は全ファイル
        """
        if not self.ftp:
            return []
        if not self.__move_directory(remote_dir):
            self.logger.error(f"Directory not found: {remote_dir}")
            return []
        try:
            files = self.ftp.nlst()
            if extension:
                return [file for file in files if file.endswith(extension)]
            return files
        except Exception as ex:  # pragma: no cover
            self.logger.error(
                f"FTP Exception from list_files: remote_dir:{remote_dir}, extension:{extension}, {ex}"
            )
            return []

    def download_bytes(self, target_file_path: str) -> bytes:
        """
        FTP 上の指定ファイルをバイト列でダウンロードする。

        Args:
            target_file_path (str): 取得対象ファイルのフルパス

        Returns:
            bytes: ファイル内容のバイト列

        Raises:
            RuntimeError: FTP 未接続時
            FileNotFoundError: ディレクトリが存在しない場合
            Exception: ダウンロード処理の失敗時
        """
        if not self.ftp:
            raise RuntimeError("FTP is not connected.")

        directory, filename = os.path.split(target_file_path)
        if not self.__move_directory(directory):
            raise FileNotFoundError(f"Directory not found on FTP: {directory}")

        buffer = io.BytesIO()
        try:
            self.ftp.retrbinary(f"RETR {filename}", buffer.write)
            buffer.seek(0)
            return buffer.getvalue()
        except Exception as ex:
            self.logger.exception(
                f"FTP Exception from download_bytes: {target_file_path}, ex: {ex}"
            )
            raise

    def stream_file(
        self, target_file_path: str, chunk_size: int = 1024 * 1024
    ) -> Iterator[bytes]:
        """
        FTP 上の指定ファイルをチャンク単位で取得する。

        Args:
            target_file_path (str): 取得対象ファイルのフルパス
            chunk_size (int): 1回に読み込むバイト数

        Yields:
            bytes: ファイルデータのチャンク

        Raises:
            RuntimeError: FTP 接続失敗時
            FileNotFoundError: ディレクトリが存在しない場合
            Exception: ダウンロード処理の失敗時
        """
        try:
            if not self.connect():
                raise RuntimeError("Failed to connect to FTP server.")
            if not self.ftp:
                raise RuntimeError("FTP is not connected.")

            directory, filename = os.path.split(target_file_path)
            if not self.__move_directory(directory):
                raise FileNotFoundError(f"Directory not found on FTP: {directory}")

            with closing(self.ftp.transfercmd(f"RETR {filename}")) as conn:
                while True:
                    chunk = conn.recv(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            self.ftp.voidresp()
        except Exception as ex:
            self.logger.exception(
                f"FTP Exception from stream_file: {target_file_path}, ex: {ex}"
            )
            raise
        finally:
            self.disconnect()
