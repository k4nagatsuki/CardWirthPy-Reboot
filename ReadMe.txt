CardWirthPy ver0.12
  作者: logの中の人
  URL: http://sites.google.com/site/cardwirthpy/

==================================


このソフトは
--------------------------------------------------------------------------

  GroupAskが開発したCardWirthの動作を再現・改良することを
  目的としたフリーのゲームソフトです。


仕様
--------------------------------------------------------------------------

  32bit版のWindows2000, XP, VISTA, 7以外のOSでの動作は未保証。
  いちおうマルチプラットフォーム化を視野に入れてます。

    サポートしている画像形式:
      BMP, JPG, PNG, GIF(non animated)

    サポートしている音楽形式:
      MIDI, MP3, OGG

    サポートしている効果音形式:
      WAV(uncompressed), OGG


操作方法
--------------------------------------------------------------------------

  基本的な操作方法はCardWirthと同じです。


CardWirthのデータの引継
--------------------------------------------------------------------------

  CardWirthPyは、CardWirthの宿データ・シナリオデータを
  CardWirthPyであつかえるデータ(XML形式)に変換し、
  引き継いで利用することができます。

  宿データは「宿の選択」ダイアログ、
  シナリオデータは「貼紙を見る」ダイアログに
  それぞれデータフォルダをドラッグアンドドロップして
  変換してください。
  
  CAB形式で圧縮されたシナリオファイルは変換できません。


シナリオエディタ
--------------------------------------------------------------------------

  有志の方が作ってくださったCWXEditorというエディタで、
  CardWirthPyのシナリオデータを作成・編集することができます。

    CWXEditor
      URL: http://mo-6.com/up/upfiles/1186.zip


CardWirthと違うところメモ
--------------------------------------------------------------------------

  ・シナリオは"wsn"という拡張子の単一ファイル(ZIP形式で圧縮した
    ファイルの拡張子をリネームしたもの)で管理。
  ・マウスホイールの操作に対応。
  ・バリアントの代わりにスキン方式を採用。
  ・冒険者の新規作成時にはスキンで定義した種族を設定できる。
  ・長いカード名もカードの横幅に合わせて縮小し、表示できる。
  ・PNG形式やGIF形式などの透過処理に対応した画像ファイルを使用できる。
  ・MP3またはOgg VorbisをBGMに使用できる。
  ・Ogg Vorbisを効果音に使用可能。MP3は未対応。
  ・効果音のWAVは無圧縮のみ対応。GSMなどで圧縮されてるものは再生不可。
  ・プレイ中にF1キーを押すと、ゲーム画面をフルスクリーン化できる。
  ・無効・無意味な効果モーションを適用させても無効化音は鳴らさない。
  ・負傷時の単体回復系召喚獣は、配布されている数だけ複数動作させる
    (CardWirthでは一体しか動作しない)。
  ・状態変数インスペクタをデバッガに改称。
  ・F9でシナリオを中断した場合、シナリオ中に取得したゴシップも消去。
  ・確率分岐コンテントは実際に設定した値の確率で分岐させる
    (CardWirthでは設定した値+1の確率で分岐する) 。
  ・JPTXファイルのフォント指定では、自動的に適切なIPAフォントを指定。
  ・JPY1ファイルのdirtypeオプションで
    3を指定すると、"Data/EffectBooster"が、
    4を指定すると、"(シナリオが展開したディレクトリ)/Material"が設定される。
  ・対象レベルの下限上限が同じとき、「1～1」ではなく「1」と表示。


エラーが出たとき
--------------------------------------------------------------------------

  CardWirthPyは未完成です。

  不可解なエラーでプログラムが機能しなかった場合は、
  "CardWirthPy.exe.log"に記されているエラーログを添えて
  作者までお知らせください。


ライセンス
--------------------------------------------------------------------------

  CardWirthPyはプログラミング言語Pythonで書かれました。
  実行ファイルの作成にはpy2exeを使用しています。

    Python ver2.6.4
      License: Python Software Foundation License
      URL: http://www.python.org/

    py2exe ver0.6.9
      URL: http://www.py2exe.org/

  CardWirthPyは以下のPythonの外部モジュールを使用しています。

    wxPython ver2.8.10.1
      License: wxWindows Library License
      URL: http://www.wxpython.org/

    Pygame ver1.9.1
      License: GNU Lesser General Public License
      URL: http://www.pygame.org/

  CardWirthPyは以下のMicrosoftのライブラリを同梱しています。

    gdiplus.dll
      License: Microsoft Redistributable
      URL: http://www.microsoft.com/downloads/details.aspx?familyid=6A63AB9C-DF12-4D41-933C-BE590FEAA05A&displaylang=en

    msvcp90.dll, msvcr90.dll
      License: Visual Studio 2008 Redistributable Code
      URL: http://www.microsoft.com/japan/msdn/vstudio/

  CardWirthPyは一般利用者向けIPAフォントを同梱しています。

    Data/Font/gothic.ttf, mincho.ttf, uigothic.ttf, pgothic.ttf, pmincho.ttf
      License: 一般利用者向けIPAフォント エンド・ユーザ・ライセンス
      URL: http://ossipedia.ipa.go.jp/ipafont/

  CardWirthPyは"CWXEditor"のリソースの画像ファイルを一部改変して
  同梱しています。

    Resource/Image/Debug にあるすべての画像ファイル
      License: Public Domain
      URL: http://mo-6.com/up/upfiles/1186.zip

  "src.zip"に同梱しているプログラミングコードの
  著作権は作者が保持し、以下のライセンスが適用されます。

      License: The MIT License
      URL: http://www.opensource.org/licenses/mit-license.php

  CardWirthPyの実行形式には以下のライセンスが適用されます。

      License: GNU Lesser General Public License
      URL: http://www.gnu.org/copyleft/lesser.html

  各ライセンスの条文は、"License.txt"を参照してください。
  同梱しているスキンデータの取り扱いについては、個別に、
  "Data/Skin"の各スキンフォルダにある"ReadMe.txt"を参照してください。


謝辞
--------------------------------------------------------------------------

  CardWirthPyを開発するにあたって、お世話になった方々に、
  心から感謝申し上げます。

    groupAsk様
      URL: http://www.ask.sakura.ne.jp/

    カードワース愛護協会および書類の谷様
      URL: http://cardwirthaigo.sakura.ne.jp/

    どうせモテないしカードワースシナリオ作ろうぜスレの方々
      URL: http://hideyoshi.2ch.net/motenai/

    Thomas様
      URL: http://thomascw.hp.infoseek.co.jp/

    wanderer7様
      URL: http://wanderer7.hp.infoseek.co.jp/cw/

    古山シウ様
      URL: http://hp.vector.co.jp/authors/VA016101/

    CW GURUの投稿者の方々
      URL: http://hp.vector.co.jp/authors/VA016101/cwguru/
    
    gulafu様
      URL: http://www.geocities.co.jp/Playtown/7299/cw/

    CardWirth Skill Wikiの管理人様
      URL: http://www9.atwiki.jp/cwskill/

    きりう様
      URL: http://homepage3.nifty.com/kiryu/cg/garden/jpy.html

    その他、バグ報告・仕様提案などご意見くださったすべての方々

