import streamlit as st
import tempfile
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from notion_client import Client

# サイズ制限（バイト単位）
MAX_SIZE = 25 * 1024 * 1024  # 25MB (Whisper APIの制限)

def check_password():
    """
    パスワードによるアクセス制御機能
    """
    # セッションステートを初期化
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    # すでに認証済みなら、Trueを返す
    if st.session_state["password_correct"]:
        return True
    
    # 正しいパスワード (st.secrets から読み込み)
    correct_password = st.secrets.get("APP_PASSWORD", "")
    
    # デバッグ情報を表示 - f-string内でエスケープシーケンスを避けるため変数を先に定義
    auth_status = "認証済み" if st.session_state["password_correct"] else "未認証"
    st.write(f"現在の認証状態: {auth_status}")  # デバッグ用
    
    # パスワード入力フォーム
    st.markdown("### パスワード入力")
    password = st.text_input("パスワードを入力してください", type="password", key="password_input")
    
    if st.button("ログイン", key="login_button"):
        if password == correct_password:
            st.session_state["password_correct"] = True
            # experimental_rerunをst.rerun()に変更
            st.rerun()  # セッションステートの更新を反映させるために再実行
            return True
        else:
            st.error("パスワードが正しくありません")
            return False
    
    return False

def load_config():
    """
    st.secrets から設定情報（APIキーなど）を読み込みます。
    """
    # 設定
    config = {
        "openai": {"api_key": st.secrets.get("OPENAI_API_KEY", "")},
        "notion": {
            "api_key": st.secrets.get("NOTION_API_KEY", ""),
            "database_id": st.secrets.get("NOTION_DATABASE_ID", "")
        }
    }
    
    return config

def get_file_metadata(file):
    """
    ファイルのメタデータを取得します
    :param file: アップロードされたファイルオブジェクト
    :return: ファイル名と作成日時のタプル
    """
    # 一時ファイルを作成して保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.name).suffix) as tmp_file:
        tmp_file.write(file.getvalue())
        tmp_path = tmp_file.name
    
    # ファイル名を取得（拡張子も含む）
    filename = Path(file.name).name
    
    # メタデータが取得できない場合、現在の日時を使用
    creation_date = datetime.now().strftime('%Y-%m-%d')
    
    # FFmpegがあるかどうかチェック
    ffmpeg_available = False
    try:
        subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        ffmpeg_available = True
    except (subprocess.SubprocessError, FileNotFoundError):
        # 警告メッセージを非表示にするか、より情報的なメッセージに変更
        st.info("詳細なメタデータ抽出は省略されます（FFmpeg非対応環境）")
    
    if ffmpeg_available:
        try:
            # FFmpegを使用して作成日時のメタデータを取得
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                tmp_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            metadata = json.loads(result.stdout)
            
            # 作成日時メタデータを抽出
            if 'format' in metadata and 'tags' in metadata['format']:
                tags = metadata['format']['tags']
                # 様々なメタデータタグをチェック
                for date_key in ['creation_time', 'date', 'creation_date', 'datetime']:
                    if date_key in tags:
                        creation_date = tags[date_key]
                        break
            
            if creation_date:
                # ISO 形式に変換、'T'で分割して日付部分だけを取得
                try:
                    # 様々な日付形式に対応
                    if 'T' in creation_date:
                        creation_date = creation_date.split('T')[0]  # ISO形式の場合
                    elif ' ' in creation_date:
                        creation_date = creation_date.split(' ')[0]  # 空白区切りの場合
                    
                    # YYYY:MM:DD形式をYYYY-MM-DDに変換
                    if ':' in creation_date and creation_date.count(':') >= 2:
                        parts = creation_date.split(':')
                        if len(parts[0]) == 4:  # YYYY形式の年の場合
                            creation_date = f"{parts[0]}-{parts[1]}-{parts[2]}"
                except:
                    # 日付形式の変換失敗の場合は無視
                    pass
            
            # メタデータが取得できない場合、ファイルの更新日時を使用
            if not creation_date:
                file_stat = os.stat(tmp_path)
                creation_date = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d')
        except Exception as e:
            st.warning(f"音声ファイルのメタデータ取得中にエラーが発生しました: {e}")
    
    # 一時ファイルを削除
    try:
        os.unlink(tmp_path)
    except:
        pass
    
    return filename, creation_date

def split_text_for_notion(text, max_length=2000):
    """
    長いテキストをNotionの制限に合わせて分割します
    :param text: 分割するテキスト
    :param max_length: ブロックあたりの最大文字数
    :return: 分割されたテキストのリスト
    """
    if len(text) <= max_length:
        return [text]
    
    # 文章を分割
    chunks = []
    for i in range(0, len(text), max_length):
        chunks.append(text[i:i + max_length])
    
    return chunks

def split_audio_ffmpeg(input_file, chunk_duration=300, output_dir=None):
    """
    FFmpegを使用して音声ファイルを指定された長さのチャンクに分割します（デフォルト5分）
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp()
    
    # ファイル形式を取得
    file_ext = os.path.splitext(input_file)[1].lower()
    output_format = "wav"  # 出力は常にWAV形式
    
    # FFmpegコマンドを構築
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-f", "segment",
        "-segment_time", str(chunk_duration),
        "-c:a", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",       # サンプルレート16kHz
        f"{output_dir}/chunk_%03d.{output_format}"
    ]
    
    try:
        # FFmpegを実行（出力を非表示）
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 生成されたチャンクファイルをリストアップ
        chunk_files = sorted([
            os.path.join(output_dir, f) for f in os.listdir(output_dir)
            if f.startswith("chunk_") and f.endswith(f".{output_format}")
        ])
        
        return chunk_files
    except subprocess.CalledProcessError as e:
        st.error(f"FFmpegによる音声分割中にエラーが発生しました: {e}")
        if e.stderr:
            st.error(f"FFmpeg エラーメッセージ: {e.stderr.decode()}")
        raise e

def transcribe_audio(file, api_key, model="whisper-1", language="ja"):
    """
    OpenAI Whisper APIを使用して音声を文字起こしする
    """
    try:
        # OpenAIクライアントの初期化
        client = OpenAI(api_key=api_key)
        
        # 一時ファイルを作成して保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.name).suffix) as tmp_file:
            tmp_file.write(file.getvalue())
            tmp_path = tmp_file.name
        
        file_size = os.path.getsize(tmp_path)
        
        # ファイルサイズが制限を超える場合は分割して処理
        if file_size > MAX_SIZE:
            st.info(f"ファイルサイズが大きいため（{file_size/1024/1024:.2f}MB）、分割して処理します。")
            
            # FFmpegが利用可能か確認
            ffmpeg_available = False
            try:
                subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                ffmpeg_available = True
            except (subprocess.SubprocessError, FileNotFoundError):
                st.error("音声分割にはFFmpegが必要です。Streamlit Cloudではファイルサイズが25MB以下の音声ファイルだけが対応可能です。")
                raise Exception("FFmpegが見つかりません。より小さなファイルで試してください。")
            
            if not ffmpeg_available:
                raise Exception("FFmpegが見つかりません。より小さなファイルで試してください。")
            
            # 音声ファイルを複数のチャンクに分割
            temp_dir = tempfile.mkdtemp()
            try:
                chunk_files = split_audio_ffmpeg(tmp_path, output_dir=temp_dir)
                
                full_text = ""
                all_segments = []
                
                # 各チャンクを処理
                for i, chunk_file in enumerate(chunk_files):
                    st.info(f"チャンク {i+1}/{len(chunk_files)} を処理中...")
                    
                    # ファイルサイズを確認（デバッグ用）
                    chunk_size = os.path.getsize(chunk_file)
                    st.info(f"チャンクサイズ: {chunk_size/1024/1024:.2f}MB")
                    
                    with open(chunk_file, "rb") as audio_file:
                        try:
                            transcript = client.audio.transcriptions.create(
                                model=model,
                                file=audio_file,
                                language=language,
                                response_format="verbose_json"
                            )
                            
                            # テキスト部分を結合
                            if hasattr(transcript, 'text'):
                                full_text += transcript.text + "\n"
                            
                            # セグメント情報があれば追加
                            if hasattr(transcript, 'segments'):
                                # セグメントの時間オフセットを調整
                                time_offset = (i * 300)  # 5分（300秒）ごとのオフセット
                                for segment in transcript.segments:
                                    if hasattr(segment, 'start'):
                                        segment.start += time_offset
                                    if hasattr(segment, 'end'):
                                        segment.end += time_offset
                                all_segments.extend(transcript.segments)
                        except Exception as e:
                            st.error(f"チャンク {i+1} の処理中にエラーが発生: {str(e)}")
                            continue
                    
                    # 処理済みのチャンクを削除
                    try:
                        os.remove(chunk_file)
                    except:
                        pass
                
                # 一時ディレクトリのクリーンアップ
                try:
                    os.rmdir(temp_dir)
                except:
                    pass
                
                # 元の一時ファイルも削除
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                
                return full_text, all_segments
            except Exception as e:
                st.error(f"音声分割処理中にエラーが発生しました: {str(e)}")
                raise e
        else:
            # ファイルサイズが小さい場合は直接処理
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language=language,
                    response_format="verbose_json"
                )
            
            # 一時ファイルを削除
            os.unlink(tmp_path)
            
            return transcript.text, getattr(transcript, "segments", [])
    except Exception as e:
        st.error(f"文字起こし中にエラーが発生しました: {str(e)}")
        raise e

def generate_markdown(text, segments):
    """
    文字起こし結果をMarkdown形式に整形します。
    """
    md = "# 音声文字起こし結果\n\n"
    if text:
        md += "## 全体テキスト\n\n" + text + "\n\n"
    else:
        md += "全体の文字起こしテキストがありません。\n\n"
    
    if segments:
        md += "## セグメント別文字起こし\n\n"
        for seg in segments:
            start = getattr(seg, "start", 0)
            end = getattr(seg, "end", 0)
            text = getattr(seg, "text", "").strip()
            md += f"- **[{start:.2f}秒 ～ {end:.2f}秒]**: {text}\n"
    else:
        md += "セグメント情報がありません。\n"
    return md

def generate_summary(text, api_key):
    """
    文字起こしテキストからサマリーを生成します。
    :param text: 文字起こしテキスト
    :param api_key: OpenAI APIキー
    :return: サマリー文章
    """
    prompt = f"""
以下は会議の文字起こしテキストです。このテキストから、重要なポイントをまとめた議事録を作成してください。
議事録には以下の情報を含めてください：
1. 会議の主な議題
2. 議論された重要なポイント
3. 決定事項
4. アクションアイテム（担当者と期限がわかる場合）
5. 次回のフォローアップ項目（もしあれば）

形式は以下のようにしてください：
- 簡潔かつ明確に
- 箇条書きでまとめる
- 内容は会議の実質的な情報だけを含める

文字起こしテキスト:
"""
    prompt += text

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは会議の議事録を要約する専門家です。構造的で簡潔、かつ重要なポイントが明確にわかるように情報をまとめます。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"サマリー生成中にエラーが発生しました: {str(e)}")
        raise e

def write_to_notion(api_key, database_id, title, transcription, summary, filename, file_date):
    """
    Notionデータベースに新規ページとして文字起こし結果とサマリーを書き込みます。
    :param api_key: Notion API キー
    :param database_id: 書き込み先のNotionデータベースID
    :param title: 議事録のタイトル
    :param transcription: 文字起こしテキスト
    :param summary: サマリーテキスト
    :param filename: 元の音声ファイル名
    :param file_date: 音声ファイルの作成日時
    :return: 成功メッセージまたはエラーメッセージ
    """
    try:
        notion = Client(auth=api_key)
        
        # Notionデータベースの最初のカラム（通常はタイトル型）にページタイトルを設定
        # Notionデータベースのプロパティを自動的に調べる
        try:
            db_info = notion.databases.retrieve(database_id)
            properties = {}
            
            # タイトルプロパティと日付プロパティを見つける
            title_property = None
            date_property = None
            
            for prop_name, prop_info in db_info['properties'].items():
                if prop_info['type'] == 'title' and title_property is None:
                    title_property = prop_name
                elif prop_info['type'] == 'date' and date_property is None:
                    date_property = prop_name
            
            # タイトルプロパティを設定（元のファイル名を使用）
            if title_property:
                properties[title_property] = {
                    "title": [
                        {
                            "text": {
                                "content": filename
                            }
                        }
                    ]
                }
            else:
                st.warning("データベースにタイトル型プロパティが見つかりませんでした。")
            
            # 日付プロパティがあれば設定（ファイルの作成日時を使用）
            if date_property and file_date:
                properties[date_property] = {
                    "date": {
                        "start": file_date
                    }
                }
            
            # ページの子ブロックを作成
            children = [
                {
                    "object": "block",
                    "type": "heading_2", 
                    "heading_2": {
                        "rich_text": [{
                            "type": "text", 
                            "text": {"content": "会議要約"}
                        }]
                    }
                }
            ]
            
            # サマリーテキストをブロックに追加
            summary_chunks = split_text_for_notion(summary)
            for chunk in summary_chunks:
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text", 
                            "text": {"content": chunk}
                        }]
                    }
                })
            
            # 文字起こし見出しを追加
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{
                        "type": "text", 
                        "text": {"content": "文字起こし全文"}
                    }]
                }
            })
            
            # 文字起こしテキストをチャンクに分割して追加
            transcription_chunks = split_text_for_notion(transcription)
            for chunk in transcription_chunks:
                children.append({
                    "object": "block", 
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text", 
                            "text": {"content": chunk}
                        }]
                    }
                })
            
            # 新しいページを作成
            new_page = notion.pages.create(
                parent={"database_id": database_id},
                properties=properties,
                children=children
            )
            
            return f"Notionデータベースに新規ページとして議事録を作成しました。文字起こしテキストは{len(transcription_chunks)}個のブロックに分割されました。"
            
        except Exception as e:
            return f"Notionデータベースのプロパティ取得中にエラーが発生しました: {str(e)}"
            
    except Exception as e:
        return f"Notionへの書き込み中にエラーが発生しました: {str(e)}"

def main():
    st.set_page_config(page_title="会議録作成アプリ", page_icon="📝", layout="wide")
    st.title("会議録作成アプリ")
    
    # パスワード認証を確認
    if not check_password():
        st.stop()  # 認証が通らなければここで処理を中断
    
    try:
        config = load_config()
        api_key = config.get("openai", {}).get("api_key")
        notion_api_key = config.get("notion", {}).get("api_key")
        notion_database_id = config.get("notion", {}).get("database_id")
        
        if not api_key:
            st.error("Streamlit Secretsから OpenAI APIキーが見つかりません。")
            return
        
        # Notion設定の確認
        notion_configured = notion_api_key and notion_database_id
    except Exception as e:
        st.error(f"設定の読み込みエラー: {e}")
        return

    uploaded_file = st.file_uploader("音声ファイルをドラッグ＆ドロップしてください (mp4, m4a, wav)", type=["mp4", "m4a", "wav"])
    meeting_title = st.text_input("会議タイトル", "議事録")
    
    if uploaded_file is not None:
        st.info("ファイルをアップロードしました。文字起こしを開始します...")
        
        # ファイルのメタデータを取得
        filename, file_date = get_file_metadata(uploaded_file)
        st.info(f"ファイル名: {filename}, 作成日時: {file_date}")
        
        with st.spinner("文字起こし中..."):
            try:
                # 直接Whisper APIを使用して文字起こし
                transcription_text, segments = transcribe_audio(uploaded_file, api_key=api_key)
                
                # サマリー生成
                with st.spinner("会議内容のサマリーを生成中..."):
                    summary_text = generate_summary(transcription_text, api_key=api_key)
                
                # 結果の表示
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 会議サマリー")
                    st.markdown(summary_text)
                    
                with col2:
                    st.markdown("### 文字起こし結果")
                    st.markdown(transcription_text[:1000] + "..." if len(transcription_text) > 1000 else transcription_text)
                    if len(transcription_text) > 1000:
                        with st.expander("全文を表示"):
                            st.markdown(transcription_text)
                
                # Markdownテキストをダウンロードできるボタン
                full_markdown = f"# {meeting_title}\n\n## 会議サマリー\n\n{summary_text}\n\n## 文字起こし全文\n\n{transcription_text}"
                st.download_button(
                    label="Markdownファイルとしてダウンロード",
                    data=full_markdown,
                    file_name=f"{meeting_title}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )
                
                # Notionへの書き込みオプション
                if notion_configured:
                    if st.button("Notionに議事録を保存"):
                        with st.spinner("Notionに保存中..."):
                            result = write_to_notion(
                                notion_api_key, 
                                notion_database_id, 
                                meeting_title, 
                                transcription_text, 
                                summary_text,
                                filename,
                                file_date
                            )
                            st.success(result)
                else:
                    st.warning("Notionへの保存機能を使用するには、Streamlit Secretsに Notionの設定情報を入力してください。")
                    
            except Exception as e:
                st.error(f"処理中にエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()
