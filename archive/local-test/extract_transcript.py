#!/usr/bin/env python3
"""
ローカル動画ファイルから音声を抽出し、文字起こしを行うスクリプト
"""

import os
import json
import re
import subprocess
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
        base_dir / "transcripts",
        base_dir / "audio"
    ]
    
    for dir_path in directories:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return base_dir

def extract_video_id(youtube_url):
    """ユーチューブURLから動画IDを抽出"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)',
        r'youtube\.com/watch\?.*v=([\w-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    return None

def extract_audio_from_file(video_path, output_dir, video_id):
    """ローカル動画ファイルから音声を抽出"""
    print(f"🎵 ローカル動画から音声を抽出中: {video_path}")
    
    # 出力ディレクトリ作成
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 出力ファイル名
    output_file = f"{output_dir}/{video_id}.mp3"
    
    try:
        # FFmpegを使用して音声を抽出
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # ビデオを無視
            '-acodec', 'libmp3lame',
            '-ab', '192k',
            '-ar', '44100',
            '-y',  # 上書きを許可
            output_file
        ]
        
        print(f"🔧 FFmpegコマンド実行中...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # ファイルサイズを取得
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            
            # 動画情報をFFprobeで取得
            probe_cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ]
            
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            video_info = json.loads(probe_result.stdout) if probe_result.returncode == 0 else {}
            duration = float(video_info.get('format', {}).get('duration', 0))
            
            print(f"✅ 音声抽出完了: {output_file}")
            print(f"    📊 ファイルサイズ: {file_size_mb:.1f} MB")
            
            return {
                'file_path': output_file,
                'video_id': video_id,
                'duration': int(duration),
                'file_size_mb': file_size_mb
            }
        else:
            print(f"❌ FFmpegエラー: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ 音声抽出エラー: {str(e)}")
        return None

def transcribe_audio(audio_file_path, video_info):
    """音声を文字起こし"""
    print(f"📝 文字起こし中: {audio_file_path}")
    
    # OpenAIクライアントの初期化
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    try:
        with open(audio_file_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ja"
            )
            
        print(f"✅ 文字起こし完了 ({len(transcript.text)}文字)")
        
        # フォーマットされた文字起こしファイルを生成
        transcript_content = f"""動画タイトル: {video_info['title']}
URL: {video_info['url']}
投稿者: {video_info['uploader']}
投稿日: {video_info['upload_date']}
動画時間: {video_info['duration']}秒
処理日時: {datetime.now().isoformat()}

==================================================
文字起こし内容
==================================================

{transcript.text}
"""
        
        return transcript_content
        
    except Exception as e:
        print(f"❌ 文字起こしエラー: {str(e)}")
        return None

def main(video_path=None, youtube_url=None):
    """メイン実行関数"""
    print("🚀 音声抽出・文字起こし処理開始")
    print("=" * 60)
    
    # 引数の確認
    if not video_path or not youtube_url:
        print("❌ エラー: 引数が不足しています")
        print("使用方法: python extract_transcript.py <動画ファイルパス> <YouTube URL>")
        print("例: python extract_transcript.py /path/to/video.mp4 https://www.youtube.com/watch?v=VIDEO_ID")
        return
    
    print(f"📁 ローカル動画ファイル: {video_path}")
    print(f"🎬 YouTube URL: {youtube_url}")
    
    # ファイルが存在するか確認
    if not os.path.exists(video_path):
        print(f"❌ エラー: 動画ファイルが見つかりません: {video_path}")
        return
    
    # YouTube URLからvideo IDを抽出
    video_id = extract_video_id(youtube_url)
    if not video_id:
        print("❌ エラー: YouTube URLから動画IDを抽出できませんでした")
        return
    
    print(f"🆔 動画ID: {video_id}")
    
    # 出力ディレクトリ作成
    base_dir = create_output_directories()
    print(f"📁 出力ディレクトリ作成: {base_dir}")
    
    # タイムスタンプ生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 音声抽出
    print("\n" + "=" * 60)
    audio_data = extract_audio_from_file(video_path, str(base_dir / "audio"), video_id)
    if not audio_data:
        print("❌ 音声抽出に失敗しました")
        return
    
    # 動画情報を設定
    video_info = {
        'id': video_id,
        'title': f"ローカル動画 ({Path(video_path).name})",
        'uploader': '不明',
        'duration': audio_data['duration'],
        'upload_date': datetime.now().strftime('%Y%m%d'),
        'url': youtube_url
    }
    
    # 文字起こし
    print("\n" + "=" * 60)
    transcript_content = transcribe_audio(audio_data['file_path'], video_info)
    
    if not transcript_content:
        print("❌ 文字起こしに失敗しました")
        print("❌ OpenAI APIが利用できません。.envファイルにAPIKEYが設定されているか確認してください。")
        return
    
    # 文字起こしファイルを保存
    transcript_file = base_dir / "transcripts" / f"transcript_{video_id}_{timestamp}.txt"
    transcript_file.write_text(transcript_content, encoding='utf-8')
    print(f"📝 文字起こし生成完了: {transcript_file}")
    print(f"    📊 文字数: {len(transcript_content):,}文字")
    
    print("\n" + "=" * 60)
    print("✅ 音声抽出・文字起こし完了！")
    print("=" * 60)
    
    print(f"\n📁 生成されたファイル:")
    print(f"   🎵 音声ファイル: {audio_data['file_path']}")
    print(f"   📝 文字起こし: {transcript_file}")
    
    print(f"\n📈 処理結果:")
    print(f"   動画時間: {video_info['duration']}秒")
    print(f"   音声ファイルサイズ: {audio_data['file_size_mb']:.1f} MB")
    print(f"   文字起こし: {len(transcript_content):,}文字")
    
    print(f"\n💡 次のステップ:")
    print(f"   記事生成: python generate_article.py {transcript_file}")

if __name__ == "__main__":
    import sys
    
    # コマンドライン引数の処理
    if len(sys.argv) == 3:
        # ローカル動画パスとYouTube URL
        main(sys.argv[1], sys.argv[2])
    else:
        main()