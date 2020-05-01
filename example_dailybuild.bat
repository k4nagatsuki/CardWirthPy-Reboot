@echo off

rem デイリービルドの手間を少し削減するためのスクリプトです。引数はありません。

rem 作業フォルダ(実在するフォルダを指定すること)
set DEST_DIR=%USERPROFILE%\Desktop\release_work

rem デイリービルドは最終リリースからの差分としてリリースされるが、その最終リリースを置くパス
set DIFF_BASE=D:\path\to\dirffbase
rem CardWirthPyのローカルリポジトリ
set LOCAL_REPO_ENGINE=D:\path\to\cardwirthpy-reboot

rem Python(32-bit)
set PYTHON_32="C:\Program Files (x86)\Python38-32\python.exe"
rem Python(64-bit)
set PYTHON_64="C:\Program Files\Python38\python.exe"

rem CardWirthPyプレイヤーズガイドのローカルリポジトリのパス
set CARDWIRTHPY_HELP_DIR=D:\path\to\CWPy_Help
rem ビルドされたCardWirthPyプレイヤーズガイドのパス
set CARDWIRTHPY_HELP=%CARDWIRTHPY_HELP_DIR%\CardWirthPy.chm

rem -----------------------------------------------------------------------

pushd %LOCAL_REPO_ENGINE%
%PYTHON_64% dailybuild.py %DEST_DIR% -chm=%CARDWIRTHPY_HELP% -diff-base="%DIFF_BASE%\CardWirthPy_x64"
%PYTHON_32% dailybuild.py %DEST_DIR% -chm=%CARDWIRTHPY_HELP% -diff-base="%DIFF_BASE%\CardWirthPy_x86"
