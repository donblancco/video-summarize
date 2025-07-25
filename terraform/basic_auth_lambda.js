'use strict';

// Basic認証のユーザー名とパスワード
const USERNAME = 'YOUR_USERNAME';
const PASSWORD = 'YOUR_PASSWORD';

// Base64エンコードされた認証情報
const authString = 'Basic ' + Buffer.from(USERNAME + ':' + PASSWORD).toString('base64');

exports.handler = (event, context, callback) => {
    // CloudFront Viewer Requestイベントからリクエストを取得
    const request = event.Records[0].cf.request;
    const headers = request.headers;
    
    // Authorizationヘッダーをチェック
    if (typeof headers.authorization !== 'undefined' && 
        headers.authorization[0].value === authString) {
        // 認証成功 - リクエストを通す
        callback(null, request);
        return;
    }
    
    // 認証失敗 - 401レスポンスを返す
    const response = {
        status: '401',
        statusDescription: 'Unauthorized',
        headers: {
            'www-authenticate': [
                {
                    key: 'WWW-Authenticate',
                    value: 'Basic realm="Restricted Area"'
                }
            ],
            'content-type': [
                {
                    key: 'Content-Type',
                    value: 'text/html; charset=UTF-8'
                }
            ]
        },
        body: `
<!DOCTYPE html>
<html>
<head>
    <title>認証が必要です</title>
    <meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; text-align: center; margin-top: 100px;">
    <h1>🔒 認証が必要です</h1>
    <p>このページにアクセスするには認証が必要です。</p>
    <p>正しいユーザー名とパスワードを入力してください。</p>
</body>
</html>
        `
    };
    
    callback(null, response);
};