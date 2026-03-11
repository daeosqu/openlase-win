# OpenLase development

# Requirements

- [JACK 1.9.22 win64](https://github.com/jackaudio/jack2-releases/releases/download/v1.9.22/jack2-win64-v1.9.22.exe) JACK Audio Connection Kit for Windows 64bit
- [laserdock_jack](https://github.com/daeosqu/laserdock_jack.git) if you have LaserCube
- AutoHotkey

# Build requirements

- Visual Studio 2022 Community
- Powershell (v7 or later recomended)
- [Git for Windows 2.44.0.1](https://gitforwindows.org/)
- [Qt5 x86-5.14.2 (qt-opensource-windows-x86-5.14.2.exe)](https://download.qt.io/archive/qt/5.14/5.14.2/qt-opensource-windows-x86-5.14.2.exe)
- python 3.11.9 (64bit) (3.11 or older)
  - cython 3.2.x
- [wix3](https://github.com/wixtoolset/wix3/releases/)
- [Scoop](https://scoop.sh/)
  - cmake 3.29.2 64bit
  - yasm 1.3.0
  - ffmpeg 7.0
  - gsudo 2.4.4
- Libraries (vcpkg)
  - ffmpeg 7.1.1
  - freeglut3.4.0
  - getopt
  - libmodplug0.8.9.0
  - pdcurses3.9
  - pthreads3.0.0

# Install PowerShell 7.x (OPTIONAL)

PowerShell 7 を推薦。

```powershell
PS> winget install --id Microsoft.Powershell --source winget
```

# Install visual studio

[Visual Studio 2022 Community](https://c2rsetup.officeapps.live.com/c2r/downloadVS.aspx?sku=community&channel=Release&version=VS2022&source=VSLandingPage&cid=2030:9583320712cb4f7982ad59fe836f4b4e) をインストールします。

コンポーネントは以下のコンポーネントを選択します。

- C++ コア機能
- MSVC v143 - VS 2022 C++ x64/x86 ビルドツール (最新)
- Windows 11 SDK (10.0.22621.0)

コンポーネントの選択とインストールは以下の構成ファイルを Visual Studio Installer で読み込むことでも可能です。

```json:requirements.vsconfig
{
  "version": "1.0",
  "components": [
    "Microsoft.VisualStudio.Component.CoreEditor",
    "Microsoft.VisualStudio.Workload.CoreEditor",
    "Microsoft.VisualStudio.Component.VC.CoreIde",
    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
    "Microsoft.VisualStudio.Component.Windows11SDK.22621",
    "Microsoft.VisualStudio.ComponentGroup.WebToolsExtensions.CMake"
  ],
  "extensions": []
}
```

# Install with scoop (OPTIONAL)

scoop で必要なツール類をインストールします。

```powershell
scoop install cmake yasm ffmpeg gsudo vcpkg
scoop update cmake yasm ffmpeg gsudo vcpkg
```

# Install python3 (OPTIONAL)

Python3 をインストールします。

```
pyenv install 3.11.9
pyenv local 3.11.9
```

# ソースコードの準備

作業ディレクトリを作成してクローンします。

```powershell
mkdir C:/opt/el
cd C:/opt/el
cd C:/opt/el
git -c core.autocrlf=false clone https://github.com/daeosqu/openlase-win.git 
cd C:/opt/el/openlase-win
. openlase.cmd
```

# Cleanup

念のためビルドディレクトリ等をクリアしておきます。

```
rm -r venv
rm -r build
rm -r python\build
```

# 仮想環境

仮想環境を準備します。

```powershell
pyenv exec python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

# Build (GNU Make)

msys, make が必要です。

```
scoop install msys2 make
make shell
make build
make dist
```

# Build (windows)

または以下の様にコマンドを実行します。

Ninja の場合:

```powershell
$env:DISTUTILS_USE_SDK = "1"
Import-Module .\scripts\win\ol_utils.psm1
Enable-VsDevEnv
.\venv\Scripts\Activate.ps1
$env:DISTUTILS_USE_SDK = "1"
cmake -S . -B "build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=On -DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake" -DPython3_EXECUTABLE="venv\Scripts\python.exe" -DQt5_DIR="C:/Qt/Qt5.14.2/5.14.2/msvc2017_64/lib/cmake/Qt5"
ninja -C build
```

Visual Studio の場合:

```
$env:DISTUTILS_USE_SDK = "1"
Import-Module .\scripts\win\ol_utils.psm1
Enable-VsDevEnv
.\venv\Scripts\Activate.ps1
cmake -S . -B "build" -G "Visual Studio 17 2022" -A x64 -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=On -DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_ROOT\scripts\buildsystems\vcpkg.cmake" -DPython3_EXECUTABLE="venv\Scripts\python.exe" -DQt5_DIR="C:/Qt/Qt5.14.2/5.14.2/msvc2017_64/lib/cmake/Qt5"
cmake --build "build" --config Release --verbose
```

NOTE: インストール先を変更する場合は `-DCMAKE_INSTALL_PREFIX="./install"` のように指定します。

# Install (windows)

```
cmake --install build
```

# Build Package (windows)

```
cd build
cpack
```

生成された `build/openlase-0.0.5-win64.msi` をインストールします。

# Install PixivUtil2 (OPTIONAL)

ugoira_player2 を使うには PixivUtil2 をインストールしておく必要があります。

```
Invoke-WebRequest -Uri "https://github.com/Nandaka/PixivUtil2/releases/download/v20230105/pixivutil202305.zip" -OutFile pixivutil202305.zip
Expand-Archive pixivutil202305.zip -DestinationPath "$HOME/.local/pixivutil" -Force
del pixivutil202305.zip
```

# Yamaha AG06mk2 について

公式の Jack Audio バイナリーパッケージ (Windows) が AG06mk2 で動作しませんでした。その場合は [mingw-w64-ucrt-x86_64-jack2-1.9.22.zip](https://github.com/daeosqu/jack2-build-win/releases/download/v0.2/mingw-w64-ucrt-x86_64-jack2-1.9.22.zip) を使ってください。

QjackCtl の Server Prefix を `<PATH-TO-JACK2>\jackd.exe -S -X winmme` のように変更します。

# 2ch 以上として認識されるオーディオデバイスの場合

2ch 以上のオーディオデバイスが接続されている場合、Jack のパッチベイが混乱して接続が切れたり繋がったりを繰り返してしまいます。この場合は QjackCtl の Settings -> Advanced タブで Channels I/O を 2ch に設定してください。


