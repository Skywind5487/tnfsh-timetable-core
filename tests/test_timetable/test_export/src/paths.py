from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parents[4]

# test_export 根目錄
TEST_EXPORT_ROOT = Path(__file__).resolve().parent.parent

# 測試輸出目錄
TEST_OUTPUT_DIR = TEST_EXPORT_ROOT / "test_outputs"
TEST_OUTPUT_DIR.mkdir(exist_ok=True)

# 測試資產目錄
TEST_ASSETS_DIR = TEST_EXPORT_ROOT / "assests"
