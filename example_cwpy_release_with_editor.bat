@echo off

rem 使い方:
rem  1. CWXEditor側のリリーススクリプト`cwx_release.bat`を準備しておきます。
rem  2. スクリプトを自分用にコピーして`cwpy_release_with_editor.bat`とし、各環境変数を設定します。
rem  3. 以下のコマンドでビルドとアーカイブの作成を行います(CardWirthPy 4・CWXEditor 7の場合)。
rem     cwpy_release_with_editor.bat 7.0 4.0 build
rem  4. ビルド・アーカイブ作成の結果が問題なければ以下のコマンドを実行してリモートリポジトリへ反映します。
rem     cwpy_release_with_editor.bat 7.0 4.0 release

rem 作業フォルダ(実在するフォルダを指定すること)
set DEST_DIR_ENGINE=%USERPROFILE%\Desktop\release_work
rem ZIP圧縮に使用するアーカイバ(コマンド)
set ARCHIVER="C:\Program Files\7-Zip\7z" a -tzip

rem CardWirthPyのローカルリポジトリ
set LOCAL_REPO_ENGINE=D:\path\to\cardwirthpy-reboot
rem CardWirthPyのリモートリポジトリ
set MAIN_REPO_ENGINE=https://<username>@bitbucket.org/<username>/cardwirthpy-reboot
rem CWXEditorのリモートリポジトリ
set MAIN_REPO_EDITOR=https://<username>@bitbucket.org/<username>/cwxeditor

rem 差分リリース用の旧バージョンのバージョン番号
set OLDVERSION=3.0
rem 差分リリース用の旧バージョンの位置(32-bit)
set OLDVERSION_PATH_32=D:\path\to\CardWirthPy_%OLDVERSION%_x86
rem 差分リリース用の旧バージョンの位置(64-bit)
set OLDVERSION_PATH_64=D:\path\to\CardWirthPy_%OLDVERSION%_x64

rem 差分作成スクリプトdirdiff.pyの位置
set DIRDIFF=D:\path\to\dirdiff.py
rem テキストエディタ
set EDITOR=notepad

rem リリースに含めるスキンのあるフォルダ。このフォルダにBloodWirthとJUDGEMENTが必要
rem Classicスキンだけはローカルリポジトリにあるものをコピーするので注意
set SKIN_DIR=D:\path\to\release_skins
rem リリースに含めるシナリオのあるフォルダ
rem `Ask/交易都市リューン`と`Ask\ゴブリンの洞窟`が含まれるはず
set SCENARIO_DIR=D:\path\to\Scenario

rem CWXEditorのローカルリポジトリのパス
set EDITOR_DIR=D:\path\to\cwxeditor
rem CardWirthPyプレイヤーズガイドのローカルリポジトリのパス
set CARDWIRTHPY_HELP_DIR=D:\path\to\CWPy_Help
rem ビルドされたCardWirthPyプレイヤーズガイドのパス
set CARDWIRTHPY_HELP=%CARDWIRTHPY_HELP_DIR%\CardWirthPy.chm

rem Python(32-bit)
set PYTHON_32="C:\Program Files (x86)\Python37-32\python.exe"
rem Python(64-bit)
set PYTHON_64="C:\Program Files\Python37\python.exe"

rem デイリービルドは最終リリースからの差分としてリリースされるが、その最終リリースを置くパス
set DIFF_BASE=D:\path\to\dirffbase

rem commit時のユーザ名
set USER=username
rem commit時のEメールアドレス
set EMAIL=username@example.com

rem -----------------------------------------------------------------------

if "%1"=="" exit /b -1
if "%2"=="" exit /b -2
if not "%3"=="build" (
	if not "%3"=="release" (
		echo buildかreleaseを指定してください。
		exit /b -1
	)
)

if "%3"=="build" (
	echo CardWirthPyとCWXEditorのプロセスは残っていませんか？(残っている場合は終了しておく)
	pause
)

@echo on

set COMMIT_MESSAGE_ENGINE=%1
set COMMIT_MESSAGE_ENGINE=%COMMIT_MESSAGE_ENGINE:beta=β%
set COMMIT_MESSAGE_ENGINE=%COMMIT_MESSAGE_ENGINE:a=α%

if "%3"=="build" (
	pushd "%CARDWIRTHPY_HELP_DIR%"
	git checkout master
	%PYTHON_32% build.py
	popd

	pushd %EDITOR_DIR%\cwxeditor_src
	call cwx_release.bat %2 test copy_builds
	if not errorlevel = 0 goto failure
	pushd %~dp0

	pushd %DEST_DIR_ENGINE%
	git clone %LOCAL_REPO_ENGINE% cardwirthpy-reboot
	cd cardwirthpy-reboot
	git config --local user.name "%USER%"
	git config --local user.email "%EMAIL%"
	%EDITOR% ChangeLog.txt
	git add ChangeLog.txt
	%EDITOR% ReadMe.txt
	git add ReadMe.txt
	%EDITOR% build_cx.py
	git add build_cx.py
	%EDITOR% cw\__init__.py
	git add cw\__init__.py
	%EDITOR% Data\SystemCoupons.xml
	git add Data\SystemCoupons.xml
	git commit -m "%COMMIT_MESSAGE_ENGINE%"
	git tag release_%1

	%PYTHON_32% build_cx.py -chm=%CARDWIRTHPY_HELP%
	xcopy /e %LOCAL_REPO_ENGINE%\Data\Skin\Classic CardWirthPy\Data\Skin\Classic\
	xcopy /e %SKIN_DIR%\BloodWirth CardWirthPy\Data\Skin\BloodWirth\
	xcopy /e %SKIN_DIR%\JUDGMENT CardWirthPy\Data\Skin\JUDGMENT\
	xcopy /e %SCENARIO_DIR%\Ask CardWirthPy\Scenario\Ask\
	xcopy /e %SCENARIO_DIR%\BloodWirth CardWirthPy\Scenario\BloodWirth\
	%PYTHON_32% %DIRDIFF% CardWirthPy %OLDVERSION_PATH_32% ..\CardWirthPy
	copy ReadMe.txt ..\CardWirthPy\
	copy License.txt ..\CardWirthPy\
	%ARCHIVER% ..\CardWirthPy_%1_x86.zip CardWirthPy
	%ARCHIVER% ..\CardWirthPy_%OLDVERSION%_x86_to_%1_x86.zip ..\CardWirthPy
	xcopy /e CardWirthPy ..\CardWirthPy_x86\
	xcopy /e ..\cwxeditor_x86\* CardWirthPy\
	%ARCHIVER% ..\CardWirthPy_%1_with_CWXEditor_%2_x86.zip CardWirthPy
	rmdir /Q /S ..\CardWirthPy

	%PYTHON_64% build_cx.py -chm=%CARDWIRTHPY_HELP%
	xcopy /e %LOCAL_REPO_ENGINE%\Data\Skin\Classic CardWirthPy\Data\Skin\Classic\
	xcopy /e %SKIN_DIR%\BloodWirth CardWirthPy\Data\Skin\BloodWirth\
	xcopy /e %SKIN_DIR%\JUDGMENT CardWirthPy\Data\Skin\JUDGMENT\
	xcopy /e %SCENARIO_DIR%\Ask CardWirthPy\Scenario\Ask\
	xcopy /e %SCENARIO_DIR%\BloodWirth CardWirthPy\Scenario\BloodWirth\
	%PYTHON_64% %DIRDIFF% CardWirthPy %OLDVERSION_PATH_64% ..\CardWirthPy
	copy License.txt ..\CardWirthPy\
	%ARCHIVER% ..\CardWirthPy_%1_x64.zip CardWirthPy
	%ARCHIVER% ..\CardWirthPy_%OLDVERSION%_x64_to_%1_x64.zip ..\CardWirthPy
	xcopy /e CardWirthPy ..\CardWirthPy_x64\
	xcopy /e ..\cwxeditor_x64\* CardWirthPy\
	%ARCHIVER% ..\CardWirthPy_%1_with_CWXEditor_%2_x64.zip CardWirthPy
	rmdir /Q /S ..\CardWirthPy

	pushd %DEST_DIR_ENGINE%

	rmdir /Q /S cwxeditor_x64
	rmdir /Q /S cwxeditor_x86

) else if "%3"=="release" (

	rem エンジンのメインストリームへのpush
	pushd %DEST_DIR_ENGINE%
	cd cardwirthpy-reboot
	git push %MAIN_REPO_ENGINE% master
	git push %MAIN_REPO_ENGINE% --tags
	if not errorlevel = 0 goto failure
	popd

	rem エンジンの作業リポジトリへのメインストリームからのpullとリモートへのpush
	pushd %LOCAL_REPO_ENGINE%
	git pull upstream master
	git pull upstream --tags
	git push origin master
	git push origin --tags
	if not errorlevel = 0 goto failure
	popd

	rem エディタのメインストリームへのpush
	pushd %DEST_DIR_ENGINE%
	cd cwxeditor_temp
	git push %MAIN_REPO_EDITOR% master
	git push %MAIN_REPO_EDITOR% --tags
	if not errorlevel = 0 goto failure
	popd

	rem エディタの作業リポジトリへのメインストリームからのpullとリモートへのpush
	pushd %EDITOR_DIR%
	git pull upstream master
	git pull upstream --tags
	git push origin master
	git push origin --tags
	if not errorlevel = 0 goto failure
	popd

	rem 今回の生成結果をデイリービルドの差分作成元にする(32-bit)
	pushd %DEST_DIR_ENGINE%
	rmdir /S /Q %DIFF_BASE%\CardWirthPy_x86
	xcopy /e /i CardWirthPy_x86 %DIFF_BASE%\CardWirthPy_x86\
	popd

	rem 今回の生成結果をデイリービルドの差分作成元にする(64-bit)
	pushd %DEST_DIR_ENGINE%
	rmdir /S /Q %DIFF_BASE%\CardWirthPy_x64
	xcopy /e /i CardWirthPy_x64 %DIFF_BASE%\CardWirthPy_x64\
	popd

	pushd %DEST_DIR_ENGINE%
	rmdir /Q /S CardWirthPy_x86
	rmdir /Q /S CardWirthPy_x64
	rmdir /Q /S cardwirthpy-reboot
	rmdir /Q /S cwxeditor_temp
	popd
)

:failure
