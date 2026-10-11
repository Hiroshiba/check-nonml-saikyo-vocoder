"""CLIの警告・エラーと外部処理の出力を、後から読めるログに残す。"""
from datetime import datetime, timezone
import argparse
import faulthandler
import logging
import os
from pathlib import Path
import subprocess
import sys
import time
import warnings

_log_path = None
_fault_file = None


class LoggedArgumentParser(argparse.ArgumentParser):
    """引数の具体的な誤りを、画面だけでなくログにも残す。"""

    def error(self, message):
        logging.error('コマンド引数が不正です: %s', message, stack_info=True)
        super().error(message)


def configure_logging(command):
    global _log_path, _fault_file
    if _log_path is not None:
        return _log_path
    root = Path(__file__).resolve().parents[1]
    directory = Path(os.environ.get('VOCODERBENCH_LOG_DIR', root / 'runs/logs'))
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    _log_path = directory / f'{stamp}-{command}-{os.getpid()}.log'
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(level=logging.INFO, format='%(asctime)sZ %(levelname)s %(name)s: %(message)s',
                        handlers=[logging.FileHandler(_log_path, encoding='utf-8'), logging.StreamHandler()], force=True)
    logging.captureWarnings(True)
    warnings.simplefilter('always')
    sys.excepthook = lambda kind, value, tb: logging.getLogger('cli').critical(
        '未処理の例外で終了しました', exc_info=(kind, value, tb))
    _fault_file = _log_path.open('a', encoding='utf-8')
    faulthandler.enable(file=_fault_file)
    logging.info('開始: %s。ログ: %s', command, _log_path)
    return _log_path


def run_cli(function, command):
    configure_logging(command)
    try:
        return function() or 0
    except SystemExit as error:
        if error.code not in (0, None):
            logging.exception('コマンドが異常終了しました: %s', error.code)
        return error.code
    except KeyboardInterrupt:
        logging.exception('操作により中断されました')
        return 130
    except Exception:
        logging.exception('コマンドが失敗しました')
        return 1


def run_process(argv, **kwargs):
    kwargs.pop('capture_output', None)
    kwargs.pop('check', None)
    kwargs.pop('text', None)
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False, **kwargs)
        if result.stdout:
            logging.info('外部処理の出力 (%s):\n%s', argv[0], result.stdout.replace('\0', '\n').rstrip())
        if result.stderr:
            logging.warning('外部処理の標準エラー出力 (%s):\n%s', argv[0], result.stderr.rstrip())
        result.check_returncode()
        return result
    except Exception:
        logging.exception('外部処理に失敗しました: %s', argv[0])
        raise
