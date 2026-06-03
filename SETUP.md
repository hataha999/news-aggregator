# セットアップ手順

## 1. GitHubリポジトリ作成

1. https://github.com/new でリポジトリ作成
   - 名前例: `news-aggregator`
   - **Public** 推奨（GitHub Actions 無料枠が無制限になる）
2. このフォルダをそのままプッシュ

```bash
cd /Users/fukuzawayoshiki/Work/news-aggregator
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/news-aggregator.git
git push -u origin main
```

---

## 2. GitHub Secrets を登録

リポジトリの **Settings → Secrets and variables → Actions → New repository secret**

| Secret名 | 値 |
|----------|-----|
| `ANTHROPIC_API_KEY` | Anthropic コンソールで発行したAPIキー |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL（下記参照） |

### Discord Webhook URLの取得方法
1. Discord サーバーの投稿したいチャンネルを右クリック → **チャンネルの編集**
2. **連携サービス** → **ウェブフック** → **新しいウェブフック**
3. 名前を「NewsBot」などに設定 → **ウェブフックURLをコピー**

---

## 3. GitHub Pages を有効化

1. リポジトリの **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `docs` フォルダ を選択
4. Save

数分後に `https://YOUR_USERNAME.github.io/news-aggregator/` でポータルが見られます。

---

## 4. GitHub Actions を有効化

1. リポジトリの **Actions** タブを開く
2. 「I understand my workflows, go ahead and enable them」をクリック

これで3時間ごとに自動実行されます。

### 手動テスト実行
Actions → **News Aggregator** → **Run workflow** → **Run workflow**

---

## 5. ローカルテスト

```bash
cd /Users/fukuzawayoshiki/Work/news-aggregator
export ANTHROPIC_API_KEY="sk-ant-..."
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python3 src/main.py
```

---

## 実行スケジュール（JST換算）

| UTC cron | JST |
|----------|-----|
| 21:00 UTC | 06:00 JST |
| 00:00 UTC | 09:00 JST |
| 03:00 UTC | 12:00 JST |
| 06:00 UTC | 15:00 JST |
| 09:00 UTC | 18:00 JST |
| 12:00 UTC | 21:00 JST |
| 15:00 UTC | 00:00 JST |
| 18:00 UTC | 03:00 JST |

---

## カスタマイズ

### 分野・キーワードの追加
`config/sources.yml` を編集するだけ。

### 配信頻度の変更
`.github/workflows/fetch-news.yml` の `cron:` 行を変更。

### 1カテゴリあたりの最大記事数
`src/main.py` の `max_per_category=5` を変更。
