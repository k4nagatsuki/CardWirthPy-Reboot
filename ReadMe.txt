CardWirthPy ver0.12.1
  作者: logの中の人
  URL: http://sites.google.com/site/cardwirthpy/
       https://bitbucket.org/k4nagatsuki/cardwirthpy-reboot (暫定)

==================================


このソフトは
--------------------------------------------------------------------------

  GroupAskが開発したCardWirthの動作を再現・改良することを
  目的としたフリーのゲームソフトです。


仕様
--------------------------------------------------------------------------

  次のOSで動作確認を行っています。

  ・Windows XP(32bit)
  ・Windows 7(64bit)

  次のOSでは、以前動作確認していましたが現在は未保証です。

  ・Windows2000(32bit)
  ・Windows Vista(32bit)

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
  ※ ver0.12.1からシナリオデータの変換は不要になりました。
     Scenarioフォルダ内のショートカットにも対応したため、
     移動させる必要もありません。

  宿データは「宿の選択」ダイアログ、
  シナリオデータは「貼紙を見る」ダイアログに
  それぞれデータフォルダをドラッグアンドドロップして
  変換してください。

  現状、CAB形式で圧縮されたシナリオファイルは読込・変換
  できません。


シナリオエディタ
--------------------------------------------------------------------------

  CWXEditorというエディタで、CardWirthPyのシナリオデータを
  作成・編集することができます。

    CWXEditor
      URL: https://bitbucket.org/k4nagatsuki/cwxeditor/


CardWirthと違うところメモ
--------------------------------------------------------------------------

データ形式について

  ・CWPy形式のシナリオは"wsn"という拡張子の単一ファイル(ZIP形式で
    圧縮したファイルの拡張子をリネームしたもの)で管理。
  ・バリアントの代わりにスキン方式を採用。
    CardWirthやそのバリアントからスキンを自動生成できる。
  ・CABだけではなくZIP圧縮されたシナリオも直接プレイできる。
  ・シナリオを含むフォルダだけでなく、シナリオ本体のファイルや
    フォルダのショートカットにも対応。
  ・宿がフォルダ名に直結しておらず、ファイル名に使用できない文字も
    使用でき、自由に改名もできる。
  ・シナリオで得たカードを持ち帰る時、そのカードが使用する素材が
    あればそれも一緒に持ち帰る。
  ・JPY1ファイルのdirtypeオプションで
    3を指定すると、"Data/EffectBooster"が、
    4を指定すると、"(シナリオが展開したディレクトリ)/Material"が設定される。
  ・カード1枚ごとにデータを保存。入手元シナリオ名や画像等が
    勝手に揃えられることがなく、そのまま記録される。

インタフェースについて

  ・宿帳やシナリオ選択に一覧機能を追加。
  ・マウスホイールの操作により細かく対応し、キャラクターの
    画像の選択やメッセージ送り等にも使用可能。
  ・プレイ中にF4キーを押すと、ゲーム画面を拡大する。
    拡大モードはフルスクリーン・1.5倍・2.0倍等から選択できる。
  ・シナリオ選択ダイアログが選択中のシナリオを記憶する。
  ・シフトキーか右クリックでメッセージを非表示にできる。
  ・キャンプメニューへの切り替えを高速化。オプションで無効化可能。
  ・常にではなく、セーブせずに終了しようとした場合のみ警告する。
  ・レベル調節で手放したカードをレベルを戻した際に自動的に戻す機能。
  ・Enterを押下し続けるとアニメーションも省略する。
  ・ゲームオーバー画面の選択肢にロードを追加。
  ・整列機能で整列しない状態に戻す事ができる。
  ・宿帳で整列を行える。
  ・カードをレベルや価格で整列できる。
  ・バトル開始イベント中は右下に"Round 0"と表示する。

デバッグ機能について

  ・デバッグ宿と通常宿を区別せず、オプションでモードを切り替える。
  ・状態変数インスペクタをデバッガに改称し、機能を大幅に強化。
  ・デバッグ中は反転中のキャラクターでも選択可能。
  ・デバッグ中はペナルティカードの効果を受けない。
  ・デバッグ中は敵の使用カードを選択できる。ホールド切り替えも可能。

CardWirthの問題の修正や互換性について

  ・おおよそCardWirth 1.20～1.50までで互換性が失われている部分に
    対して互換モードで動く機能を追加。互換性データベースを用意し、
    互換性問題のある既知のシナリオは自動的に互換モードで動く。
  ・FPSの概念を持ち、セルアニメ等はほぼ確実にFPS 30で動く。
  ・F9でゴシップや終了印や失ったカードを含むすべてのデータが復元する。
  ・CardWirth 1.28以前の動画再生に対応。
  ・無効・無意味な効果モーションを適用させても無効化音は鳴らさない。
  ・長いカード名もカードの横幅に合わせて縮小し、表示できる。
  ・対象レベルの下限上限が同じとき、「1～1」ではなく「1」と表示。
  ・エフェクトブースターの実行中もほとんどの操作を受け付ける。
  ・CardWirthではエフェクトブースターの一時描画をF9で飛ばせるが、
    CardWirthPyではEnterの長押しでウェイトを省略できる。
    アニメーション中でもF9の機能は従来のままとなる。

CardWirthにはあるがCardWirthPyには無い機能

  ・CardWirthの宿データをそのまま読み込む機能。必ず変換が必要です。
    技術的問題が多いため、今のところ変換無しで遊べるようにする
    予定はありません(変換→逆変換によって宿データのやり取りをする
    事は可能です)。
  ・ヘルプ。まだありません。
  ・キャラクターの自動生成。現在のところ実装の予定はありません。
  ・スクリーンショットの撮影にダイアログが含まれません。
    将来のバージョンで改善されるかもしれません。
  ・デバッグ宿でのキーコード表示。0.12.2以降で、表示のみならず
    イベントを直接実行する機能の実装を考えています。
  ・その他CardWirthNextの新機能。ある程度は追随していますが、
    最新の機能はまだ乗っていないかもしれません。
    将来のバージョンで実装される事でしょう。


エラーが出たとき
--------------------------------------------------------------------------

  CardWirthPyには現在のところ未完成の機能はありませんが、
  完成度という点ではまだ道半ばです。

  不可解なエラーでプログラムが機能しなかった場合は、
  "CardWirthPy.exe.log"に記されているエラーログを添えて
  開発者までお知らせください。


互換モード
--------------------------------------------------------------------------

  シナリオを CardWirth の過去のバージョン相当の環境で
  再生する事ができます。
  例えば1.28以降ではプレイヤーカードがメニューカードより
  前に描画されますが、1.20モードで動かす事により、
  (CardWirth 1.20のように)その順序を逆にする事ができます。
  互換モードを有効にするには、次の二つの方法があります。

  ・シナリオフォルダの直下に"mode.ini"を追加する。
    "mode.ini"の内容は以下のようにしてください。
---
[Compatibility]
engine=1.28
---
    項目"engine"の値に、そのシナリオを再生すべきCardWirth
    エンジンのバージョンを記述します。
    例えば1.20相当の動作をさせたい場合は以下のようにします。
---
[Compatibility]
engine=1.20
---

  ・互換性データベースに追加する。
    作者に、互換性の問題でプレイできない過去のシナリオの
    情報を伝えてください。それについて確認できれば、
    シナリオの情報を互換性データベースに登録する事により、
    あらゆるプレイヤーがそのシナリオを妥当な互換モードで
    プレイできるようになります。


ライセンス
--------------------------------------------------------------------------

  CardWirthPyはプログラミング言語Pythonで書かれました。
  実行ファイルの作成にはpy2exeを使用しています。

    Python ver2.7.6
      License: Python Software Foundation License
      URL: http://www.python.org/

    py2exe ver0.6.9
      URL: http://www.py2exe.org/

  CardWirthPyは以下のPythonの外部モジュールを使用しています。

    wxPython ver2.9.5.0
      License: wxWindows Library License
      URL: http://www.wxpython.org/
           http://sourceforge.net/projects/wxpython/files/wxPython/2.9.5.0/

    Pygame ver1.9.1
      License: GNU Lesser General Public License
      URL: http://www.pygame.org/

    Python for Windows extensions Build 219
      License: Python Software Foundation License
      URL: http://sourceforge.net/projects/pywin32/

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

  CardWirthPyは音声再生用に以下のライブラリを同梱しています。
  これらはソフトウェアを無償配布する限りは自由に使用できますが、
  商用利用する場合は商用ライセンスを購入する必要があるのでご注意ください。

    bass.dll
    bassmidi.dll
    bass32.so
    bassmidi32.so
    bass64.so
    bassmidi64.so
      License: BASS Audioのライセンス
      URL: http://www.un4seen.com/

  CardWirthPyは"CWXEditor"のリソースの画像ファイルを一部改変して
  同梱しています。

    Resource/Image/Debug にあるすべての画像ファイル
      License: Public Domain
      URL: https://bitbucket.org/k4nagatsuki/cwxeditor/

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


貢献者
--------------------------------------------------------------------------
(順不同・敬称略)

  https://sites.google.com/site/cardwirthpy/
  CardWirthPyは logの中の人 によって作成され、ほとんどの
  主要なコードは原作者によって書かれました。

  https://bitbucket.org/k4nagatsuki/cardwirthpy-reboot
  k4nagatsuki は開発が停止していたCardWirthPyをフォークし、
  その時点で未完成だった部分のほとんどを実装しました。

  https://bitbucket.org/takuto_cw/cardwirthpy-reboot
  takuto_cw はいくつかのバグを修正し、カードダイアログの
  ボタンに使用する画像を描き起こしました。
  また、レベル調節でのカードの移動など、新機能についての
  具体的な提案を行なっています。

  https://bitbucket.org/tachi_gigas/cardwirthpy-reboot-lessor
  TachiGigas はいくつかのバグを修正し、シナリオダイアログ
  の見逃されていた未実装部分を実装しました。
  また、アプリケーション全体で使用するフォントに関して
  大きな提案を行い、試験的な実装を行いました。


謝辞
--------------------------------------------------------------------------
(順不同・敬称略)

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

