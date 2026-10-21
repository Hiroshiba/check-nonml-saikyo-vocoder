"""比較対象・既定値。列挙だけでは重みの取得も推論も行わない。"""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE = ROOT / ".cache/references"


@dataclass(frozen=True)
class Method:
    label: str
    sample_rate: int
    sources: tuple[str, ...]
    variant: str
    optional: bool = False


METHODS = {
    "yubiwa": Method("指輪（現作業ベース）", 24000, ("llsm", "ciglet"), "LLSM2 Layer1・未測定", True),
    "world_harvest": Method("WORLD（Harvest）", 16000, (), "既存の固定版WORLD"),
    "facodec": Method("FACodec", 16000, ("facodec",), "v1・全6コードブック"),
    "hifiglot": Method("HiFi-Glot", 44100, ("hifiglot",), "公開学習済み44.1 kHz"),
    "golf": Method("GOLF-ff", 24000, ("golf",), "Interspeech 2024・フレーム近似"),
    "sifigan": Method("SiFi-GAN", 24000, ("sifigan",), "24 kHz多話者音声・歌唱"),
    "llsm2": Method("LLSM2", 24000, ("llsm", "ciglet"), "Layer 0・DIO+StoneMask"),
    "magphase": Method("MagPhase", 48000, ("magphase", "reaper"), "圧縮特徴100/45/45"),
    "dac": Method("Descript Audio Codec", 44100, ("dac",), "44.1 kHz・全9コードブック", True),
}
DEFAULT_METHODS = tuple(key for key, spec in METHODS.items() if not spec.optional)


def add_arguments(parser):
    parser.add_argument("--methods", nargs="+", choices=DEFAULT_METHODS, default=list(DEFAULT_METHODS),
                        help="標準はWORLDと既存6方式。部分実行は指定した方式のみ")
    parser.add_argument("--include-dac", action="store_true", help="DACの取得・計測を明示的に追加する")
    parser.add_argument("--runtime-cache", type=Path, default=DEFAULT_CACHE)


def selected(args):
    return list(dict.fromkeys([*args.methods, *(["dac"] if args.include_dac else [])]))
