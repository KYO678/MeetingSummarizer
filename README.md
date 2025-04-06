# MeetingSummarizer

音声ファイルをアップロードすると、AIを使って文字起こしとサマリーを自動生成し、Notionデータベースに保存できるアプリケーションです。

## 機能

- 音声ファイル（mp4, m4a, wav）の文字起こし（OpenAI Whisper API使用）
- 文字起こしテキストの自動サマリー生成（GPT-4使用）
- 長い音声ファイルの自動分割処理
- 音声ファイルのメタデータ（ファイル名、作成日時）の取得
- Notionデータベースへの議事録保存
- パスワード保護によるアクセス制限

## 必要条件

- Python 3.9以上
- FFmpeg（音声処理とメタデータ抽出に必要）
- OpenAI API Key
- Notion API Key（オプション、Notion連携機能を使用する場合）

## インストール方法

1. リポジトリをクローン：

```bash
git clone https://github.com/yourusername/minutes.git
cd minutes
```

2. 必要なライブラリをインストール：

```bash
pip install -r requirements.txt
```

3. FFmpegをインストール：

macOSの場合：
```bash
brew install ffmpeg
```

Windowsの場合：
[FFmpegの公式サイト](https://ffmpeg.org/download.html)からダウンロードしてインストール

4. `.env.example`を`.env`にコピーして編集：

```bash
cp .env.example .env
# .envファイルを編集し、APIキーなどの情報を設定
```

## 使い方

1. アプリケーションを起動：

```bash
streamlit run minutes.py
```

2. ブラウザで表示されるアプリケーションにアクセス（デフォルトでは http://localhost:8501）

3. パスワードを入力してログイン（デフォルトパスワード: minutestest1234）

4. 音声ファイルをアップロードし、会議タイトルを入力

5. 文字起こしとサマリー生成が自動的に行われます

6. 結果を確認し、必要に応じてNotionに保存またはMarkdownとしてダウンロード

## Web公開方法

### Streamlit Cloudを使う場合

1. GitHubリポジトリにコードをプッシュ
2. [Streamlit Cloud](https://streamlit.io/cloud)にアクセス
3. リポジトリを連携して新しいアプリをデプロイ
4. 環境変数に必要なAPIキーを設定

### Herokuを使う場合

1. Procfileを作成（以下の内容）:
```
web: streamlit run minutes.py
```

2. Herokuにデプロイ:
```bash
heroku create your-app-name
git push heroku main
```

3. 環境変数を設定:
```bash
heroku config:set OPENAI_API_KEY=your_openai_api_key
heroku config:set NOTION_API_KEY=your_notion_api_key
heroku config:set NOTION_DATABASE_ID=your_notion_database_id
heroku config:set APP_PASSWORD=your_app_password
```

## 注意事項

- OpenAI APIとNotion APIの使用には料金がかかる場合があります
- 大きな音声ファイルの処理には時間がかかります
- 公開サーバーで使用する場合は、セキュリティに注意し、APIキーを安全に管理してください

## ライセンス

MIT License

## 貢献

バグ報告や機能リクエストは、GitHubのIssueでお知らせください。
プルリクエストも歓迎します。
