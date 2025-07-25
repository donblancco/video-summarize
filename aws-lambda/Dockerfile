# AWS Lambda Python 3.11 基盤イメージ
FROM public.ecr.aws/lambda/python:3.11

# 必要なパッケージとFFmpegをインストール
RUN yum update -y && \
    yum install -y wget tar xz && \
    # FFmpeg静的バイナリをダウンロード・インストール
    wget -q https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz && \
    tar -xf ffmpeg-git-amd64-static.tar.xz && \
    find . -name "ffmpeg-git-*-amd64-static" -type d -exec cp {}/ffmpeg /usr/local/bin/ \; && \
    find . -name "ffmpeg-git-*-amd64-static" -type d -exec cp {}/ffprobe /usr/local/bin/ \; && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    # クリーンアップ
    rm -rf ffmpeg-git-* && \
    yum clean all

# Python依存関係をインストール（Container用軽量版）
COPY requirements-container.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements-container.txt

# Lambda関数コードをコピー（全てのLambda関数）
COPY extract_transcript_lambda.py ${LAMBDA_TASK_ROOT}
COPY generate_article_lambda.py ${LAMBDA_TASK_ROOT}
COPY wordpress_publish_lambda.py ${LAMBDA_TASK_ROOT}

# WordPressテンプレートファイルをコピー
COPY footer.html ${LAMBDA_TASK_ROOT}/footer.html

# デフォルトハンドラ（Terraform側で各関数ごとに CMD を上書きする）
CMD ["extract_transcript_lambda.lambda_handler"]