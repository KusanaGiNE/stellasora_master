import zipfile
import os
import sys
import shutil
import json
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

# === 配置 ===
SERVER_URL = "http://103.239.245.46:52176/version.json"


def get_install_root() -> Path:
    # 打包环境：以 exe 所在目录作为安装根目录
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # 源码/脚本环境：以 update.py 所在目录作为安装根目录
    return Path(__file__).resolve().parent


BASE_DIR = get_install_root()
CURRENT_VERSION_FILE = BASE_DIR / "version.txt"  # 本地版本文件


def _parse_version_tuple(v: str) -> tuple[int, int, int, str]:
    # 仅做“足够稳”的语义版本比较：x.y.z[-suffix]
    # suffix 只参与最后的稳定性排序（无 suffix > 有 suffix）。
    v = (v or "").strip()
    if v.startswith("v") or v.startswith("V"):
        v = v[1:]

    core, sep, suffix = v.partition("-")
    parts = core.split(".")
    nums: list[int] = []
    for p in parts[:3]:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2], suffix


def _is_remote_newer(remote_ver: str, local_ver: str) -> bool:
    r = _parse_version_tuple(remote_ver)
    l = _parse_version_tuple(local_ver)
    if r[:3] != l[:3]:
        return r[:3] > l[:3]
    # 同主版本：无 suffix 认为更“新/稳定”
    if bool(r[3]) != bool(l[3]):
        return not bool(r[3])
    return r[3] > l[3]

def get_local_version():
    if CURRENT_VERSION_FILE.exists():
        try:
            return CURRENT_VERSION_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            try:
                return CURRENT_VERSION_FILE.read_text().strip()
            except Exception:
                return "1.0.0"
    return "1.0.0"


def _download(url: str, dst: Path, timeout: int = 10) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "StellasoraMasterUpdater/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if getattr(resp, "status", 200) != 200:
                raise RuntimeError(f"下载失败，HTTP 状态码: {getattr(resp, 'status', 'unknown')}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"下载失败: HTTP {e.code} {e.reason}\n"
            f"URL: {url}\n"
            "提示：如果是 404，通常表示更新服务器未上传补丁文件或 version.json 的 download_url 配置错误。"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"下载失败: {e.reason}\nURL: {url}") from e


def _copy_merge(src_dir: Path, dst_dir: Path, skip_dst: set[Path] | None = None) -> None:
    skip_dst = skip_dst or set()
    for root, dirs, files in os.walk(src_dir):
        root_path = Path(root)
        rel = root_path.relative_to(src_dir)
        target_root = dst_dir / rel
        target_root.mkdir(parents=True, exist_ok=True)

        for d in dirs:
            (target_root / d).mkdir(parents=True, exist_ok=True)

        for fn in files:
            src_file = root_path / fn
            dst_file = target_root / fn
            if dst_file.resolve() in skip_dst:
                continue
            shutil.copy2(src_file, dst_file)


def _candidate_download_urls(download_url: str) -> list[str]:
    url = (download_url or "").strip()
    if not url:
        return []

    candidates: list[str] = [url]

    # 兼容：服务器实际站点根目录就是 /www/wwwroot/stellasora
    # 但 version.json 误写成 /stellasora/patches/xxx.zip，导致 HTTP 404。
    try:
        parts = urlsplit(url)
        path = parts.path or ""

        if path.startswith("/stellasora/"):
            new_path = path[len("/stellasora"):]
            candidates.append(urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment)))
    except Exception:
        pass

    # 去重但保序
    deduped: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        if c not in seen:
            deduped.append(c)
            seen.add(c)
    return deduped

def update():
    print("正在检查更新...")
    print(f"安装目录: {BASE_DIR}")
    try:
        # 1. 获取远程版本信息
        with urllib.request.urlopen(SERVER_URL, timeout=5) as resp:
            if getattr(resp, "status", 200) != 200:
                print("无法连接到更新服务器")
                return
            remote_data = json.loads(resp.read().decode("utf-8"))

        remote_ver = remote_data["latest_version"]
        local_ver = get_local_version()
        
        print(f"当前版本: {local_ver}, 最新版本: {remote_ver}")
        
        if not _is_remote_newer(remote_ver, local_ver):
            print("已经是最新版本。")
            time.sleep(2)
            return

        print(f"\n发现新版本！更新内容:\n{remote_data['changelog']}\n")
        
        # 2. 下载补丁
        print("正在下载更新包...")
        zip_path = BASE_DIR / "update_temp.zip"
        download_url = str(remote_data.get("download_url", "")).strip()
        print(f"下载链接: {download_url}")
        if not download_url:
            raise RuntimeError("更新信息缺少 download_url，无法下载补丁。")

        last_error: Exception | None = None
        for candidate in _candidate_download_urls(download_url):
            try:
                if candidate != download_url:
                    print(f"尝试备用链接: {candidate}")
                _download(candidate, zip_path, timeout=20)
                last_error = None
                break
            except Exception as e:
                last_error = e
                continue

        if last_error is not None:
            raise last_error
                
        # 3. 解压覆盖
        print("正在安装更新...")
        extract_dir = BASE_DIR / "_update_extract"
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)

        # 兼容 zip 内有顶层目录的情况：若只有一个目录且没有文件，则下钻一层
        children = list(extract_dir.iterdir())
        payload_root = extract_dir
        if len(children) == 1 and children[0].is_dir():
            payload_root = children[0]

        # 避免尝试覆盖“当前正在运行的 exe”
        skip: set[Path] = set()
        if getattr(sys, "frozen", False):
            skip.add(Path(sys.executable).resolve())

        _copy_merge(payload_root, BASE_DIR, skip_dst=skip)
            
        # 4. 更新本地版本号
        CURRENT_VERSION_FILE.write_text(remote_ver, encoding="utf-8")
            
        # 5. 清理
        try:
            zip_path.unlink(missing_ok=True)
        except TypeError:
            if zip_path.exists():
                zip_path.unlink()

        shutil.rmtree(extract_dir, ignore_errors=True)
        
        print("更新成功！正在启动主程序...")
        time.sleep(1)
        
        # 启动主程序
        exe_path = BASE_DIR / "StellasoraMaster.exe"
        if exe_path.exists():
            os.startfile(str(exe_path))
        else:
            print("未找到主程序，请手动启动。")
        
    except Exception as e:
        print(f"更新失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    # 确保不在 _internal 中运行，而是作为独立进程
    update()
