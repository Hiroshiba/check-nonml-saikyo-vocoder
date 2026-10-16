"""Path-only context configured by run_extended; not a measurement algorithm."""

from pathlib import Path
import vocoderbench

REPO = Path(vocoderbench.__file__).resolve().parents[1]
ROOT = CORPORA = HISTORICAL = ASV_INPUT = MODEL_CACHE = None


def configure(args):
    global ROOT, CORPORA, HISTORICAL, ASV_INPUT, MODEL_CACHE
    ROOT = args.run_root.resolve()
    CORPORA = args.corpora_root.resolve()
    HISTORICAL = args.historical_root.resolve()
    ASV_INPUT = args.asv_input_root.resolve()
    MODEL_CACHE = args.model_cache.resolve()
