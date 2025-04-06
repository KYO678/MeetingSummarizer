# MeetingSummarizer

このアプリケーションは、音声ファイルをアップロードするとAIを使って自動的に文字起こしとサマリーを生成し、Notionデータベースに保存できるWebアプリケーションです。

## 特徴

- 音声ファイル（mp4, m4a, wav）を自動文字起こし
- 会議内容の自動サマリー生成
- 長い音声ファイルの自動分割処理
- Notionデータベースへの議事録保存
- パスワード保護機能付き

## Streamlit Cloudでのデプロイ方法

1. **GitHubリポジトリの作成**:
   - このプロジェクトをGitHubリポジトリにプッシュします

2. **Streamlit Cloudでデプロイ**:
   - [Streamlit Cloud](https://streamlit.io/cloud)にアクセスし、アカウントを作成/ログイン
   - 「New app」ボタンをクリック
   - リポジトリとブランチを選択
   - メインファイルとして `minutes_webapp.py` を選択
   - 「Deploy!」ボタンをクリック

3. **シークレット設定**:
   - デプロイ後、アプリの「⋮」メニュー → 「Settings」をクリック
   - 「Secrets」セクションに以下のシークレットを追加（キーと値のペア）:
   
   ```
   OPENAI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   NOTION_API_KEY = "secret_xxxxxxxxxxxxxxxxxxxxxxxx"
   NOTION_DATABASE_ID = "xxxxxxxxxxxxxxxxxxxxxxxx"
   APP_PASSWORD = "minutestest1234"  # 任意のパスワードに変更可能
   ```

## ローカル開発での実行方法

1. **必要なライブラリのインストール**:
   ```bash
   pip install -r requirements.txt
   ```

2. **FFmpegのインストール**:
   ```bash
   # macOSの場合
   brew install ffmpeg
   
   # Ubuntuの場合
   apt-get install ffmpeg
   
   # Windowsの場合は公式サイトからダウンロード
   ```

3. **環境変数設定（オプション）**:
   ```bash
   export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
   export NOTION_API_KEY="secret_xxxxxxxxxxxxxxxxxxxxxxxx"
   export NOTION_DATABASE_ID="xxxxxxxxxxxxxxxxxxxxxxxx"
   export APP_PASSWORD="minutestest1234"
   ```

4. **アプリケーション実行**:
   ```bash
   streamlit run minutes_webapp.py
   ```

## Notion連携のセットアップ

1. **Notionインテグレーション作成**:
   - [Notion Integrations](https://www.notion.so/my-integrations) ページにアクセス
   - 「+ New integration」ボタンをクリック
   - 名前と関連するワークスペースを設定
   - 「Submit」をクリックしてAPIキーを取得

2. **Notionデータベースの作成**:
   - Notionで新しいデータベースを作成
   - 以下のプロパティを設定（必要に応じて追加可能）:
     - タイトル型プロパティ（例: 「名前」または「タイトル」）
     - 日付型プロパティ（例: 「日付」）

3. **データベースとインテグレーションの接続**:
   - データベースを開き、右上の「•••」ボタンをクリック
   - 「アクセス権限を共有」を選択
   - インテグレーションを検索し、選択
   - 「招待」ボタンをクリック

4. **データベースIDの取得**:
   - データベースのURLからデータベースIDを取得
   - 例: `https://www.notion.so/myworkspace/1cc5ba51319e8020a766e5f514988720?v=...`
   - この例では `1cc5ba51319e8020a766e5f514988720` がデータベースID

## FFmpegが利用できない環境での注意点

Streamlit Cloudや一部のホスティングサービスではFFmpegが使用できない場合があります。その場合、以下の制限が発生します：

1. 大きな音声ファイル（25MB超）を処理できない
2. ファイルのメタデータ（作成日時など）が取得できない

アップロードする音声ファイルは標準化し、なるべく25MB以下に担当者が事前に処理しておくことを推奨します。

## セキュリティに関する注意点

- OpenAIやNotionのAPIキーは機密情報です。必ずシークレットまたは環境変数で管理し、コード内にハードコードしないでください。
- パスワード保護は基本的な保護機能であり、完全なセキュリティを保証するものではありません。本番環境ではより高度な認証方法を検討してください。
- このアプリケーションは、API呼び出しごとに料金が発生するOpenAI APIを使用しています。利用制限や課金上限を設定することを検討してください。

## ライセンス

MIT License
