#!/usr/bin/env python3
"""
文字起こしファイルからHTML記事を生成するスクリプト
"""

import os
import json
import re
import openai
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

def create_output_directories():
    """出力ディレクトリを作成"""
    base_dir = Path("final_outputs")
    directories = [
        base_dir / "articles",
        base_dir / "metadata"
    ]
    
    for dir_path in directories:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return base_dir

def parse_transcript_file(transcript_file_path):
    """文字起こしファイルを解析して情報を抽出"""
    try:
        with open(transcript_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        video_info = {}
        
        # ヘッダー情報を解析
        for line in lines[:10]:  # 最初の10行から情報を抽出
            if line.startswith('動画タイトル:'):
                video_info['title'] = line.replace('動画タイトル:', '').strip()
            elif line.startswith('URL:'):
                video_info['url'] = line.replace('URL:', '').strip()
            elif line.startswith('投稿者:'):
                video_info['uploader'] = line.replace('投稿者:', '').strip()
            elif line.startswith('投稿日:'):
                video_info['upload_date'] = line.replace('投稿日:', '').strip()
            elif line.startswith('動画時間:'):
                duration_str = line.replace('動画時間:', '').replace('秒', '').strip()
                video_info['duration'] = int(duration_str) if duration_str.isdigit() else 0
        
        # 動画IDをURLから抽出
        url = video_info.get('url', '')
        video_id_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', url)
        video_info['id'] = video_id_match.group(1) if video_id_match else 'unknown'
        
        # 文字起こし内容を抽出
        start_index = -1
        for i, line in enumerate(lines):
            if '文字起こし内容' in line:
                start_index = i + 3  # ヘッダーの後の空行をスキップ
                break
        
        if start_index > 0:
            transcript_text = '\n'.join(lines[start_index:])
        else:
            transcript_text = content
        
        return video_info, transcript_text, content
        
    except Exception as e:
        print(f"❌ 文字起こしファイル解析エラー: {str(e)}")
        return None, None, None

def generate_article(video_info, transcript_text):
    """文字起こしから記事を生成"""
    print("📄 記事生成中...")
    
    # OpenAIクライアントの初期化
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # プロンプトを短縮してコンテキスト制限を回避
    prompt = f"""
以下のYouTube動画の文字起こしから、SEO最適化されたブログ記事を作成してください。

動画タイトル: {video_info['title']}
動画URL: {video_info['url']}
投稿者: {video_info['uploader']}

文字起こし:
{transcript_text}

記事の要件:
1. タイトルは内容を的確に表現し、検索されやすいものにする
2. 見出しタグ（h2, h3）を適切に使用して構造化する
3. 重要なポイントを箇条書きや表でまとめる
4. 専門用語には簡潔な説明を加える
5. 読者が行動を起こしやすいような結論を含める
6. 最後に動画リンクを含める（「詳しい解説は動画でご確認ください」等）
7. HTML形式で出力する（<!DOCTYPE html>から</html>まで完全な形で）
8. 不要な要素（CSS、JavaScript、メタ情報等）は含めない
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "あなたは医療・健康分野に精通したプロのブログライターです。正確で分かりやすい記事を作成します。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.7
        )
        
        article = response.choices[0].message.content
        
        # Markdownのコードブロック記号を除去
        if article.startswith('```html'):
            article = article[7:]  # '```html' を除去
        elif article.startswith('```'):
            article = article[3:]   # '```' を除去
        
        if article.endswith('```'):
            article = article[:-3]  # 末尾の '```' を除去
        
        article = article.strip()  # 前後の空白を除去
        
        print(f"✅ 記事生成完了 ({len(article)}文字)")
        return article
        
    except Exception as e:
        print(f"❌ 記事生成エラー: {str(e)}")
        return None

def generate_metadata(video_info, transcript_length, article_length):
    """メタデータJSONを生成"""
    metadata = {
        "video_info": {
            "video_id": video_info['id'],
            "title": video_info['title'],
            "uploader": video_info['uploader'],
            "duration": video_info['duration'],
            "upload_date": video_info['upload_date'],
            "url": video_info['url'],
            "thumbnail": f"https://i.ytimg.com/vi/{video_info['id']}/maxresdefault.jpg"
        },
        "processing_info": {
            "processed_at": datetime.now().isoformat(),
            "status": "completed",
            "file_sizes": {
                "transcript_kb": transcript_length / 1024,
                "article_kb": article_length / 1024
            },
            "transcript_length": transcript_length,
            "article_length": article_length,
            "retry_count": 0
        },
        "system_info": {
            "python_version": "3.11",
            "openai_model_gpt": "gpt-4-turbo"
        }
    }
    
    return metadata

def main(transcript_file_path=None):
    """メイン実行関数"""
    print("🚀 HTML記事生成開始")
    print("=" * 60)
    
    # 引数の確認
    if not transcript_file_path:
        print("❌ エラー: 文字起こしファイルパスが指定されていません")
        print("使用方法: python generate_article.py <文字起こしファイルパス>")
        print("例: python generate_article.py final_outputs/transcripts/transcript_VIDEO_ID_timestamp.txt")
        return
    
    # ファイルが存在するか確認
    if not os.path.exists(transcript_file_path):
        print(f"❌ エラー: 文字起こしファイルが見つかりません: {transcript_file_path}")
        return
    
    print(f"📝 文字起こしファイル: {transcript_file_path}")
    
    # 出力ディレクトリ作成
    base_dir = create_output_directories()
    print(f"📁 出力ディレクトリ作成: {base_dir}")
    
    # 文字起こしファイルを解析
    print("\n" + "=" * 60)
    video_info, transcript_text, full_content = parse_transcript_file(transcript_file_path)
    
    if not video_info or not transcript_text:
        print("❌ 文字起こしファイルの解析に失敗しました")
        return
    
    print(f"📋 動画情報:")
    print(f"   タイトル: {video_info['title']}")
    print(f"   投稿者: {video_info['uploader']}")
    print(f"   動画ID: {video_info['id']}")
    print(f"   文字起こし長: {len(transcript_text):,}文字")
    
    # 文字起こしが長すぎる場合は警告
    if len(transcript_text) > 4000:
        print(f"⚠️ 文字起こしが長いです({len(transcript_text)}文字)。GPT-4のコンテキスト制限により、記事生成が失敗する可能性があります。")
    
    # HTML記事生成
    print("\n" + "=" * 60)
    html_content = generate_article(video_info, transcript_text)
    
    if not html_content:
        print("❌ 記事生成に失敗しました")
        return
    
    # タイムスタンプ生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # HTMLファイルを保存
    html_file = base_dir / "articles" / f"article_{video_info['id']}_{timestamp}.html"
    html_file.write_text(html_content, encoding='utf-8')
    print(f"📄 HTML記事生成完了: {html_file}")
    print(f"    📊 文字数: {len(html_content):,}文字")
    
    # メタデータファイル生成
    print("\n" + "=" * 60)
    metadata = generate_metadata(video_info, len(full_content), len(html_content))
    metadata_file = base_dir / "metadata" / f"metadata_{video_info['id']}_{timestamp}.json"
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"📊 メタデータ生成完了: {metadata_file}")
    
    print("\n" + "=" * 60)
    print("✅ HTML記事生成完了！")
    print("=" * 60)
    
    print(f"\n📁 生成されたファイル:")
    print(f"   📄 HTML記事: {html_file}")
    print(f"   📊 メタデータ: {metadata_file}")
    
    print(f"\n🌐 HTMLファイルを確認するには:")
    print(f"   以下のファイルをブラウザで開いてください:")
    print(f"   {html_file.absolute()}")
    
    print(f"\n📈 処理結果:")
    print(f"   動画時間: {video_info['duration']}秒")
    print(f"   文字起こし: {len(full_content):,}文字")
    print(f"   HTML記事: {len(html_content):,}文字")

if __name__ == "__main__":
    import sys
    
    # コマンドライン引数の処理
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        main()